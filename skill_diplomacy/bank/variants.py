"""Family variants — the scarcity dial.

Sprint 2 diagnosis. With three task families, nothing in this experiment is
scarce: a state's library is at most three items, "what do you have that I
lack" saturates immediately, and *every* export policy collapses to a step
function between full trade and autarky. Free-riding costs nothing either —
with nine states and three families, six defectors still leave three
cooperators covering the whole space, so mean capability stays at 1.0. Under
those conditions no institutional result can be anything but an identity.

Scarcity is what makes an exchange institution a live question. This module
mints K *variants* per archetype, each a distinct family requiring its own
doctrine, drawn from disjoint surface vocabularies. With 5 variants the space
is 15 families; a single state masters 1/15 alone, libraries stay genuinely
partial for the whole run, and "who holds what I lack" becomes a graded signal
that a relative-gains dial can actually respond to.

Honest scope note: variants create *skill scarcity*, not task diversity. They
share their archetype's solution logic, so a live model may transfer across
variants far more easily than across archetypes, which would compress the
capability gradient. Variants are the right instrument for studying exchange
under scarcity and the wrong one for claiming breadth of task coverage; a live
run that wants both should add genuinely distinct archetypes alongside them.
"""
from __future__ import annotations

import datetime as dt
import random

from .base import Generator, TaskInstance
from .generators.calendar_math import CalendarMathGenerator
from .generators.lexicon import LexiconGenerator, _GLYPHS
from .generators.modmath import ModMathGenerator
from .generators.protocol import ProtocolGenerator
from .generators.unit_chain import UnitChainGenerator

ARCHETYPES = ["unit_chain", "calendar_math", "modmath"]

# `lexicon` is opt-in, NOT in ARCHETYPES. Adding a fourth archetype by default
# would change the family count and break bit-for-bit reproduction of the
# published v1 table for a purely cosmetic reason. Callers ask for it
# explicitly: make_bank(k, include_lexicon=True).
LEXICON = "lexicon"

# `protocol` is the second load-bearing archetype, and the one with SLACK.
# `lexicon` makes capability depend on the library by making the doctrine the
# answer key, so P(solve | doctrine) = 1 and an institutional comparison over
# it returns 1 - 1/F by identity. `protocol` carries a procedure instead: the
# doctrine is necessary but not sufficient, execution can fail, and how often
# it fails is a property of the model. That is the difference between a result
# and an arithmetic restatement of the configuration. Opt-in for the same
# reason as LEXICON -- adding it by default would shift the family count and
# break bit-for-bit reproduction of the published v1 table.
PROTOCOL = "protocol"

# disjoint invented-unit pools, one per unit_chain variant
_SYLL_A = ["fl", "bl", "qu", "dr", "sn", "tv", "ml", "zr", "px", "gr", "vn", "hs"]
_SYLL_B = ["ib", "em", "on", "ap", "ub", "orv", "elk", "arn", "yx", "ol", "int", "esk"]

_MOD_POOLS = [
    [97, 101, 103, 251, 509, 1009, 4093],
    [127, 131, 137, 277, 541, 1013, 4099],
    [149, 151, 157, 281, 547, 1019, 4111],
    [163, 167, 173, 283, 557, 1021, 4127],
    [179, 181, 191, 293, 563, 1031, 4129],
]


def _unit_pool(variant: int) -> list[str]:
    """Deterministic, disjoint-by-construction unit vocabulary for a variant.

    Variant 0 returns the stock vocabulary verbatim so a 1-variant bank produces
    byte-identical prompts to v1 — otherwise the token denominators shift and the
    published governance-overhead column stops reproducing for a cosmetic reason."""
    if variant == 0:
        return None
    return [f"{_SYLL_A[i]}{_SYLL_B[(i + variant) % len(_SYLL_B)]}{variant + 1}"
            for i in range(len(_SYLL_A))]


def _tagged(base: TaskInstance, family: str) -> TaskInstance:
    """Re-label an instance onto a variant family (id stays globally unique)."""
    return TaskInstance(f"{family}-{base.id.split('-', 1)[1]}", family,
                        base.prompt, base.answer, base.meta)


class VariantGenerator(Generator):
    """Wraps an archetype generator and re-labels it as its own family."""

    def __init__(self, inner: Generator, family: str):
        self.inner = inner
        self.family = family

    def generate(self, rng: random.Random) -> TaskInstance:
        return _tagged(self.inner.generate(rng), self.family)


def family_name(archetype: str, variant: int) -> str:
    """variant 0 keeps the bare archetype name, so a 1-variant bank is
    byte-identical to the v1 setup and the published table still reproduces."""
    return archetype if variant == 0 else f"{archetype}{variant + 1}"


def _protocol_letters(variant: int) -> str | None:
    """Disjoint alphabets per protocol variant.

    Splitting the 24-letter pool would shorten each variant's substitution
    table and change how often a single corrupted entry bites, which is the
    quantity the screening sweep turns on. So every variant keeps the full
    alphabet and is separated by its `spec_seed` instead: different weights,
    different substitution values, different fold rule, same detectability
    profile. Variants must differ in content, not in difficulty."""
    return None


def _glyph_pool(variant: int) -> list[str]:
    """Disjoint glyph vocabulary per lexicon variant, so each variant is a
    genuinely separate body of knowledge rather than a relabelling."""
    if variant == 0:
        return list(_GLYPHS)
    return [f"{g}{variant + 1}" for g in _GLYPHS]


def make_bank(n_variants: int = 1, include_lexicon: bool = False,
              archetypes: list[str] | tuple[str, ...] | None = None,
              protocol_record_len: int = 4) -> dict:
    """-> {family_name: Generator}, ordered archetype-major so round-robin
    sharding spreads states across archetypes before it duplicates one.

    `include_lexicon` adds the information-carrying archetype (see
    generators/lexicon.py). Left off by default so the published v1 grid
    reproduces bit-for-bit.

    `archetypes` overrides the set entirely. The use that matters is a bank of
    nothing but load-bearing families — the only configuration in which an
    institutional comparison is measuring anything (see calibrate.py and
    runs/skill_lift_live.json). Two are available and they are not
    interchangeable: `["lexicon"]` gives lift pinned at 1.0 by construction and
    therefore an institutional gap fixed at 1 - 1/F, while `["protocol"]` gives
    lift strictly below 1, set by how reliably the model executes a six-step
    procedure. Use `["protocol"]`, or both, for any comparison meant to measure
    rather than restate. `protocol_record_len` is the difficulty dial."""
    if archetypes is not None:
        archetypes = list(archetypes)
    else:
        archetypes = ARCHETYPES + ([LEXICON] if include_lexicon else [])
    bank: dict = {}
    for v in range(n_variants):
        for arch in archetypes:
            fam = family_name(arch, v)
            if arch == LEXICON:
                gen = VariantGenerator(
                    LexiconGenerator(lex_seed=v, pool=_glyph_pool(v)), fam)
            elif arch == PROTOCOL:
                gen = VariantGenerator(
                    ProtocolGenerator(spec_seed=v, record_len=protocol_record_len,
                                      letters=_protocol_letters(v)), fam)
            elif arch == "unit_chain":
                gen = VariantGenerator(UnitChainGenerator(pool=_unit_pool(v)), fam)
            elif arch == "modmath":
                gen = VariantGenerator(
                    ModMathGenerator() if v == 0 else _ModVariant(_MOD_POOLS[v % len(_MOD_POOLS)]),
                    fam)
            else:
                gen = VariantGenerator(
                    CalendarMathGenerator() if v == 0 else CalendarMathGenerator(
                        epoch=dt.date(1900 + 15 * v, 1, 1),
                        span=(45 + 400 * v, 900 + 400 * v)),
                    fam)
            bank[fam] = gen
    return bank


class _ModVariant(ModMathGenerator):
    """modmath over a disjoint modulus pool — same phrasing, so the scripted
    oracle's regexes are untouched, but a different family to master."""

    def __init__(self, pool: list[int]):
        super().__init__()
        self.pool = pool

    def generate(self, rng: random.Random) -> TaskInstance:
        a = rng.randint(3, 60)
        b = rng.randint(*self.exp_range)
        m = rng.choice(self.pool)
        prompt = (f"Compute {a}^{b} mod {m}.\n"
                  "Show your reasoning, then give the final line as `ANSWER: <integer>`.")
        return TaskInstance(f"modmath-{rng.getrandbits(32):08x}", "modmath",
                            prompt, str(pow(a, b, m)), {"a": a, "b": b, "m": m})
