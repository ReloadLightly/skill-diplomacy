"""Tests for the information-carrying archetype and the skill-lift instrument.

Several of these assert a DIFFERENCE that removing the mechanism would erase —
the discipline the v1 review asked for. In particular: a lexicon task must be
unsolvable without its reference doctrine, because that property is the entire
reason this archetype exists.
"""
from __future__ import annotations

import random

import pytest

from calibrate import INERT, LOAD_BEARING, SATURATED, classify
from skill_diplomacy.bank.base import verify
from skill_diplomacy.bank.generators.lexicon import (
    LEXICON_POISON_MARKER, LexiconGenerator, lexicon_truth_from_body,
    poison_lexicon_body)
from skill_diplomacy.bank.variants import make_bank
from skill_diplomacy.experiment.oracle import make_oracle

SYSTEM = "You are the strategist of state A."


def _prompt(gen, task, body: str | None) -> str:
    """Mimic AgentState._prompt: doctrine body injected, then the task."""
    parts = []
    if body is not None:
        parts.append(f"Available skills:\n- {task.family}-doctrine (v1): d")
        parts.append(f"## Skill: {task.family}-doctrine\n{body}")
    parts.append(f"# Task ({task.family})\n{task.prompt}")
    return "\n\n".join(parts)


# -- ground truth -----------------------------------------------------------

def test_ground_truth_is_independently_recomputable():
    """Recompute the answer from the lexicon without using the generator's sum."""
    gen = LexiconGenerator(lex_seed=3)
    for task in gen.batch(seed=11, n=8):
        expected = sum(c * gen.lexicon[g]
                       for c, g in zip(task.meta["counts"], task.meta["glyphs"]))
        assert task.answer == str(expected)


def test_lexicon_is_deterministic_in_its_seed():
    assert LexiconGenerator(lex_seed=5).lexicon == LexiconGenerator(lex_seed=5).lexicon
    assert LexiconGenerator(lex_seed=5).lexicon != LexiconGenerator(lex_seed=6).lexicon


def test_prompt_does_not_leak_the_table():
    """The whole point: the values must not appear in the task text."""
    gen = LexiconGenerator(lex_seed=1)
    for task in gen.batch(seed=2, n=6):
        for glyph, value in gen.lexicon.items():
            if glyph in task.prompt:
                # the glyph may appear (it is in the inscription); its value may not
                counts = dict(zip(task.meta["glyphs"], task.meta["counts"]))
                if counts.get(glyph) != value:
                    assert f" {value} {glyph}" not in task.prompt


# -- the difference the doctrine makes (the load-bearing assertion) ---------

def test_task_is_unsolvable_without_the_doctrine_and_solvable_with_it():
    gen = LexiconGenerator(lex_seed=0)
    oracle = make_oracle({})
    tasks = gen.batch(seed=7, n=6)

    without = sum(verify(t, oracle(SYSTEM, _prompt(gen, t, None))) for t in tasks)
    with_ = sum(verify(t, oracle(SYSTEM, _prompt(gen, t, gen.reference_body())))
                for t in tasks)

    assert without == 0, "a lexicon task must not be answerable without the table"
    assert with_ == len(tasks), "the reference doctrine must make it solvable"


# -- contamination ----------------------------------------------------------

def test_poison_corrupts_exactly_one_row_and_is_content_detectable():
    body = LexiconGenerator(lex_seed=0).reference_body()
    poisoned = poison_lexicon_body(body)
    assert LEXICON_POISON_MARKER in poisoned
    clean, dirty = lexicon_truth_from_body(body), lexicon_truth_from_body(poisoned)
    differing = [g for g in clean if clean[g] != dirty[g]]
    assert len(differing) == 1


def test_poison_survives_re_export():
    """Content-derived, so laundering through an intermediary preserves it."""
    body = poison_lexicon_body(LexiconGenerator(lex_seed=0).reference_body())
    assert LEXICON_POISON_MARKER in body
    assert lexicon_truth_from_body(body) == lexicon_truth_from_body(body[:] + "")


def test_poisoned_doctrine_is_correct_on_most_instances_and_wrong_on_some():
    """The defining property of this contaminant class: it passes shallow tests.
    A screen that never draws a task touching the corrupted glyph cannot see it."""
    gen = LexiconGenerator(lex_seed=0)
    oracle = make_oracle({})
    poisoned = poison_lexicon_body(gen.reference_body())
    results = [verify(t, oracle(SYSTEM, _prompt(gen, t, poisoned)))
               for t in gen.batch(seed=99, n=25)]
    assert any(results), "poison that fails everything would be caught trivially"
    assert not all(results), "poison must actually corrupt some answers"


# -- bank wiring ------------------------------------------------------------

def test_lexicon_is_opt_in_so_v1_reproduces():
    assert "lexicon" not in make_bank(1)
    assert "lexicon" in make_bank(1, include_lexicon=True)
    assert len(make_bank(1)) == 3
    assert len(make_bank(1, include_lexicon=True)) == 4


def test_variants_get_disjoint_glyph_vocabularies():
    bank = make_bank(2, include_lexicon=True)
    a = set(bank["lexicon"].inner.lexicon)
    b = set(bank["lexicon2"].inner.lexicon)
    assert not (a & b), "variants must be separate bodies of knowledge"


def test_every_variant_family_is_solvable_with_its_own_reference():
    """Regression. Variant glyphs carry a numeric suffix (`azdek2`), and the
    table parser originally accepted only [a-z]. Every variant family therefore
    parsed to an EMPTY table and failed silently -- which the harness reported
    as 'the doctrine does not help', indistinguishable from a real null result.
    A bug that masquerades as a finding is the one this repository must never
    ship, so each variant is checked against its own reference here."""
    oracle = make_oracle({})
    bank = make_bank(4, include_lexicon=True)
    lex = {f: g for f, g in bank.items() if f.startswith("lexicon")}
    assert len(lex) == 4
    for family, gen in lex.items():
        inner = gen.inner
        tasks = gen.batch(seed=5, n=4)
        solved = sum(verify(t, oracle(SYSTEM, _prompt(gen, t, inner.reference_body())))
                     for t in tasks)
        assert solved == len(tasks), f"{family} unsolvable WITH its own reference"


def test_bank_can_be_restricted_to_load_bearing_families():
    bank = make_bank(3, archetypes=["lexicon"])
    assert list(bank) == ["lexicon", "lexicon2", "lexicon3"]


# -- the calibration verdicts ----------------------------------------------

@pytest.mark.parametrize("floor,lift,expected", [
    (0.95, 0.05, SATURATED),     # solvable cold — the live H1 failure mode
    (0.05, 0.05, INERT),         # doctrine does not help either
    (0.05, 0.90, LOAD_BEARING),  # capability genuinely depends on the artifact
    (0.85, 0.90, SATURATED),     # a high floor disqualifies regardless of lift
])
def test_skill_lift_classification(floor, lift, expected):
    assert classify(floor, lift) == expected
