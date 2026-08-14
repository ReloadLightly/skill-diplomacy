"""Lexicon valuation — a family whose answer requires information the PROMPT
DOES NOT CONTAIN.

Why this archetype exists
-------------------------
The live H1 run (runs/h1/) falsified the assumption the whole harness rested on.
Free trade beat autarky by +0.07 capability against a seed-to-seed spread of
0.11 — and in three of six runs *every agent finished with an empty skill
library and still scored 0.89-1.00*. The institution was redistributing
capability the agents never lacked.

The diagnosis is a property of the task design, not of the institutions. Every
v1/v2 family states its own rules inside the prompt: `unit_chain` supplies the
conversion factors, `calendar_math` needs only the Gregorian calendar,
`modmath` needs only modular arithmetic. A competent model solves all three
cold. A doctrine for such a family can only ever carry *strategy* — and strategy
is exactly what a frontier-tier model already has. So the skill is decorative,
capability is constant, and no exchange institution can move it.

For a skill to be load-bearing, it must carry INFORMATION the task does not
supply. That is also what real Agent Skills do: a SKILL.md is valuable because
it holds an API's quirks, a house style, a schema — knowledge, not cleverness.

This generator makes that concrete. Each family owns a private lexicon mapping
invented glyphs to integer values. Tasks quote an inscription; the answer is its
total value. The mapping appears ONLY in the family's reference doctrine.
Without that doctrine the task is unanswerable except by luck (chance is
effectively zero over a 2-99 value range); with it, the arithmetic is easy.

Capability therefore becomes a genuine function of library contents, which is
the precondition for every institutional claim this repository wants to make.
"""
from __future__ import annotations

import random
import re

from ..base import Generator, TaskInstance

# Invented glyph stems. Disjoint pools per variant are minted in bank/variants.py.
_GLYPHS = ["azdek", "brunel", "cirith", "dovask", "emberon", "fythe",
           "gorlan", "hesperak", "ivrune", "jalthor", "korvax", "lumeth"]


def _lexicon(seed: int, pool: list[str], size: int = 8) -> dict[str, int]:
    """The family's private glyph→value table. Deterministic in `seed`, so the
    same family always means the same thing across states, rounds and seeds."""
    rng = random.Random(seed * 7919 + 13)
    glyphs = rng.sample(pool, min(size, len(pool)))
    return {g: rng.randint(2, 99) for g in glyphs}


class LexiconGenerator(Generator):
    """Inscription valuation over a private lexicon.

    `reference_body()` renders the lexicon as a doctrine body — the artifact
    that makes the family solvable and that states exchange, screen and poison.
    """

    family = "lexicon"

    def __init__(self, lex_seed: int = 0, pool: list[str] | None = None,
                 terms: tuple[int, int] = (3, 5)):
        self.lex_seed = lex_seed
        self.terms = terms
        self._pool = list(pool) if pool else list(_GLYPHS)
        self.lexicon = _lexicon(lex_seed, self._pool)

    # -- the task ----------------------------------------------------------
    def generate(self, rng: random.Random) -> TaskInstance:
        glyphs = sorted(self.lexicon)
        k = rng.randint(*self.terms)
        chosen = rng.sample(glyphs, min(k, len(glyphs)))
        counts = [rng.randint(1, 9) for _ in chosen]
        total = sum(c * self.lexicon[g] for c, g in zip(counts, chosen))
        inscription = ", ".join(f"{c} {g}" for c, g in zip(counts, chosen))
        prompt = (
            f"Inscription: {inscription}\n\n"
            "Report the total value of this inscription in standard units.\n"
            "Show your reasoning, then give the final line as `ANSWER: <integer>`."
        )
        tid = f"{self.family}-{rng.getrandbits(32):08x}"
        return TaskInstance(tid, self.family, prompt, str(total),
                            {"counts": counts, "glyphs": chosen})

    # -- the artifact that makes it solvable -------------------------------
    def reference_body(self) -> str:
        rows = "\n".join(f"| {g} | {v} |" for g, v in sorted(self.lexicon.items()))
        return (
            "Strategy: value an inscription by multiplying each glyph's count by "
            "its standard value and summing the results.\n\n"
            "Glyph value table (authoritative):\n\n"
            "| glyph | value |\n|---|---|\n" + rows + "\n\n"
            "Procedure:\n"
            "1. Parse each `<count> <glyph>` term of the inscription.\n"
            "2. Look up the glyph's value in the table above.\n"
            "3. Multiply count by value; sum across all terms.\n"
            "4. Emit `ANSWER: <integer>`."
        )


# ---------------------------------------------------------------------------
# Contamination for this archetype.
#
# The unit_chain poison is a bogus *rule* appended to a playbook. A lexicon's
# analogue is more faithful to how reference material actually goes wrong: an
# erratum that silently overrides one table row. An importer's home-shard
# regression suite rarely touches the corrupted glyph, so the artifact passes;
# fresh probes drawn across the family hit it in proportion to its frequency.
# ---------------------------------------------------------------------------

LEXICON_POISON_MARKER = "Erratum (supersedes the table above)"

_ROW_RE = re.compile(r"^\| ([a-z]+) \| (\d+) \|$", re.MULTILINE)


def poison_lexicon_body(body: str, which: int = 0, delta: int = 7) -> str:
    """Append an erratum that corrupts exactly one glyph's value."""
    rows = _ROW_RE.findall(body or "")
    if not rows:
        return body
    glyph, value = rows[which % len(rows)]
    wrong = int(value) + delta
    return body.rstrip() + (
        f"\n\n{LEXICON_POISON_MARKER}: the value of `{glyph}` was mis-set during "
        f"transcription and is corrected to {wrong}. Use {wrong} for `{glyph}`."
    )


def lexicon_truth_from_body(body: str) -> dict[str, int]:
    """Read the table a state would actually act on, erratum included. Lets the
    scripted oracle behave exactly as a model reading this doctrine would."""
    table = {g: int(v) for g, v in _ROW_RE.findall(body or "")}
    m = re.search(r"corrected to (\d+)\. Use \d+ for `([a-z]+)`", body or "")
    if m:
        table[m.group(2)] = int(m.group(1))
    return table
