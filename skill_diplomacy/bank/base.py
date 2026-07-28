"""Task bank core: parameterized generators with self-verifying ground truth.

Design rationale (domain decision, July 2026): generators compute their own
answers, so verification is exact BY CONSTRUCTION — this is our response to
the handoff brief's binding-constraint warning ('the task verifier is nearly
perfect, otherwise the commit loop optimizes noise'). Fresh instances are
unlimited: held-out probes for quarantine and off-shard poison detection are
contamination-proof and free.

Answer convention: the final line of a submission must be `ANSWER: <value>`.
"""
from __future__ import annotations

import math
import random
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskInstance:
    id: str
    family: str
    prompt: str
    answer: str            # canonical ground truth, computed by the generator
    meta: dict = field(default_factory=dict, hash=False, compare=False)


class Generator(ABC):
    family: str = "abstract"

    @abstractmethod
    def generate(self, rng: random.Random) -> TaskInstance: ...

    def batch(self, seed: int, n: int) -> list[TaskInstance]:
        rng = random.Random(seed)
        return [self.generate(rng) for _ in range(n)]


_ANSWER_RE = re.compile(r"ANSWER:\s*(.+?)\s*$", re.MULTILINE)


def extract_answer(text: str) -> str | None:
    matches = _ANSWER_RE.findall(text)
    return matches[-1].strip() if matches else None


def _canon(s: str) -> str:
    return s.strip().rstrip(".").strip().lower()


def verify(task: TaskInstance, submission_text: str) -> bool:
    """Exact-match verification with numeric tolerance for float-formatted answers."""
    submitted = extract_answer(submission_text)
    if submitted is None:
        return False
    a, b = _canon(task.answer), _canon(submitted)
    if a == b:
        return True
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)
    except ValueError:
        return False


def shard_families(state_names: list[str], families: list[str]) -> dict[str, str]:
    """Disjoint home shards: state i specializes in family i (round-robin).
    Off-shard families are what quarantine probes and poison target."""
    return {s: families[i % len(families)] for i, s in enumerate(state_names)}
