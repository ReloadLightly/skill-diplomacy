"""A stand-in agent that can get it wrong — execution reliability as a dial.

The null model in this repository assumes agents are perfect, tireless solvers:
capability is exactly the library, so P(solve | doctrine) = 1. That assumption
is what makes the scripted arm a clean derivation, and it is also what made the
headline live result vacuous. Over `lexicon`, where the doctrine *is* the answer
key, a live model also achieves P(solve | doctrine) ≈ 1 — so the live run
reproduced the scripted numbers to four decimals, the seed variance was zero,
and the reported institutional gap was the identity 1 − 1/F, chosen by the
experimenter rather than measured.

The repair has two halves. `bank/generators/protocol.py` is the first: a family
whose doctrine carries a *procedure*, so holding it is necessary but not
sufficient and execution can fail. This module is the second: it makes the
failure rate an explicit, swept parameter instead of a property of whichever
model happened to be called.

Why that matters even though a live model is the eventual instrument. A live
run tells you what one model tier does at one moment; it cannot tell you what
the institution does *as a function of* execution reliability, because you
cannot set a model's reliability. Sweeping `FallibleModel` can, deterministically
and for free, and it answers the question the audit put to the design: is there
any configuration in which model behaviour selects the outcome? With a perfect
solver over `lexicon` the answer was no. Here the answer is a curve.

Read the two together: the scripted oracle is the r = 1 endpoint of this sweep,
and a live model sits somewhere on it at a position the live run measures.
"""
from __future__ import annotations

import hashlib
import random
import re

from ..bank.base import extract_answer
from .model import ModelResponse, _approx_tokens

# How many elementary operations an instance of each archetype demands. The
# count is what makes reliability compose: a procedure with more steps is more
# likely to be executed wrongly, which is the property `protocol` exists to have
# and `lexicon` (one table lookup per term) largely lacks.
_RECORD_RE = re.compile(r"Record: (\S+)")
_INSCRIPTION_RE = re.compile(r"Inscription: (.+)")
_TERM_RE = re.compile(r"(\d+) ([a-z]+\d*)")
_FACTOR_RE = re.compile(r"= (\d+) ")


def step_count(prompt: str) -> int:
    """Elementary operations an instance requires, read off the prompt.

    Deliberately crude — it is a difficulty proxy, not a cost model — but it has
    to be monotone in the real work, or the reliability dial would not bite
    harder on harder instances, which is the only interesting thing about it."""
    m = _RECORD_RE.search(prompt)
    if m:
        # one substitution/multiply/fold per character, plus the final reduction
        return sum(1 for c in m.group(1) if c.isalnum()) + 1
    m = _INSCRIPTION_RE.search(prompt)
    if m:
        return len(_TERM_RE.findall(m.group(1))) + 1
    factors = _FACTOR_RE.findall(prompt)
    if factors:
        return len(factors) + 1
    return 1


class FallibleModel:
    """Wraps a policy and makes it fail at a controlled, reproducible rate.

    `reliability` is per STEP, so an instance requiring n steps is answered
    correctly with probability `reliability ** n`. That is the right shape for a
    procedure — errors compound along it — and it is why `protocol`'s difficulty
    dial (`record_len`) and this reliability dial interact rather than
    duplicating each other.

    Failures are *plausible*, not empty: a wrong answer is a perturbation of the
    right one, so the harness cannot distinguish "executed badly" from "held a
    corrupted doctrine" by inspecting the output. If failures were obviously
    malformed, quarantine would be catching a tell rather than a defect, and the
    screening results would be measuring the stand-in instead of the screen.

    Determinism: the coin is keyed on (seed, system, prompt) via SHA-256, not on
    call order. A trial therefore reproduces exactly even though adoption
    decisions change how many calls precede any given one — which order-based
    seeding would silently break, in the direction of making runs look noisier
    than the mechanism is.
    """

    def __init__(self, policy, reliability: float = 0.97, seed: int = 0):
        if not 0.0 <= reliability <= 1.0:
            raise ValueError(f"reliability must be in [0, 1], got {reliability}")
        self._policy = policy
        self.reliability = reliability
        self.seed = seed
        self.calls = 0
        self.corrupted = 0

    # -- provenance ---------------------------------------------------------
    def describe(self) -> dict:
        return {"client": "FallibleModel", "live": False,
                "reliability_per_step": self.reliability,
                "seed": self.seed, "calls": self.calls,
                "corrupted": self.corrupted, "errors": 0,
                "note": ("a scripted stand-in whose per-step execution "
                         "reliability is a swept parameter; reliability=1.0 is "
                         "the perfect-solver oracle")}

    # -- the coin -----------------------------------------------------------
    def _rng(self, system: str, prompt: str) -> random.Random:
        key = f"{self.seed}|{system}|{prompt}".encode()
        return random.Random(int(hashlib.sha256(key).hexdigest()[:16], 16))

    def _perturb(self, text: str, rng: random.Random) -> str:
        """Return the same response with a wrong ANSWER line."""
        answer = extract_answer(text)
        if answer is None:
            return text
        if answer.lstrip("-").isdigit():
            n = int(answer)
            # off by a small amount, never by zero: an arithmetic slip
            wrong = n + rng.choice([-3, -2, -1, 1, 2, 3])
            new = str(wrong)
        elif len(answer) == 1:
            # a check character: land on a different one
            alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
            pool = [c for c in alphabet if c != answer]
            new = rng.choice(pool) if pool else answer
        else:
            new = answer + "x"
        head, _, _ = text.rpartition(f"ANSWER: {answer}")
        return f"{head}ANSWER: {new}"

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> ModelResponse:
        text = self._policy(system, prompt)
        self.calls += 1
        if self.reliability < 1.0 and extract_answer(text) is not None:
            rng = self._rng(system, prompt)
            n = step_count(prompt)
            if rng.random() > self.reliability ** n:
                text = self._perturb(text, rng)
                self.corrupted += 1
        return ModelResponse(text, _approx_tokens(system + prompt), _approx_tokens(text))
