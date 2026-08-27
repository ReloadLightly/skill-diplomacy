"""The uncertainty layer, and the design facts it exposes.

Two of these are not really tests of arithmetic — they are executable statements
about this repository's own published design, kept in the suite so they cannot
quietly stop being true:

  * three seeds per arm cannot produce p < 0.05 two-sided, whatever the effect;
  * six instances per family cannot separate the skill-lift regimes it is used
    to assign.
"""
from __future__ import annotations

import pytest

from skill_diplomacy.metrics.stats import (bootstrap_ci, compare, fmt,
                                           min_achievable_p, permutation_test,
                                           proportion, wilson)


# -- proportions -------------------------------------------------------------

def test_wilson_stays_inside_the_unit_interval_at_the_extremes():
    """Where Wald fails: 0/6 and 6/6 both get zero-width Wald intervals."""
    for successes in (0, 6):
        lo, hi = wilson(successes, 6)
        assert 0.0 <= lo <= hi <= 1.0
        assert hi - lo > 0.3, "a six-trial proportion is not this certain"


def test_wilson_narrows_as_n_grows():
    widths = [wilson(n // 2, n)[1] - wilson(n // 2, n)[0] for n in (6, 20, 100)]
    assert widths[0] > widths[1] > widths[2]


def test_a_six_trial_saturated_verdict_is_not_actually_certain():
    """`runs/skill_lift_live.json` calls unit_chain SATURATED from 6/6. That is
    consistent with a true pass rate as low as ~0.6, so the classification is
    being made at an n where its own thresholds are not resolvable."""
    p = proportion(6, 6)
    assert p["estimate"] == 1.0
    assert p["ci_low"] < 0.7


def test_the_modmath_negative_lift_is_not_distinguishable_from_zero():
    """LETTER.md draws a conclusion from lift = -0.17 ('skills are not free even
    when ignored'). At n=6 the two intervals almost entirely overlap."""
    floor, with_skill = proportion(5, 6), proportion(4, 6)
    assert floor["ci_low"] < with_skill["ci_high"]
    assert with_skill["ci_low"] < floor["ci_high"]


# -- means -------------------------------------------------------------------

def test_bootstrap_is_seeded_and_reproducible():
    a = bootstrap_ci([0.1, 0.5, 0.9], seed=7)
    b = bootstrap_ci([0.1, 0.5, 0.9], seed=7)
    assert a == b


def test_bootstrap_on_identical_values_has_zero_width():
    d = bootstrap_ci([0.3333, 0.3333, 0.3333])
    assert d["ci_low"] == d["ci_high"] == pytest.approx(0.3333)
    assert d["sd"] == 0.0


def test_n_of_one_declines_to_invent_an_interval():
    d = bootstrap_ci([0.5])
    assert d["ci_low"] == d["ci_high"] == 0.5
    assert "note" in d


# -- differences and the design floor ---------------------------------------

def test_three_seeds_per_arm_cannot_reach_significance():
    """C(6,3) = 20 arrangements, so the two-sided floor is 2/20 = 0.10."""
    assert min_achievable_p(3, 3) == pytest.approx(0.10)
    assert min_achievable_p(3, 3) > 0.05


def test_five_seeds_per_arm_can():
    """The whole cost of making the live contrast reportable: two more seeds."""
    assert min_achievable_p(5, 5) < 0.05


def test_perfect_separation_at_three_seeds_still_only_returns_the_floor():
    """The committed lexicon result: autarky 0.333 x3 vs free trade 1.000 x3.
    Total, noiseless separation — and p is still 0.10, because that is all the
    design can say."""
    r = permutation_test([0.3333] * 3, [1.0] * 3)
    assert r["method"] == "exact" and r["arrangements"] == 20
    assert r["p"] == pytest.approx(min_achievable_p(3, 3))


def test_compare_reports_the_design_floor_beside_the_p_value():
    c = compare([0.3333] * 3, [1.0] * 3, "autarky", "free_trade")
    assert c["difference"] == pytest.approx(-0.6667, abs=1e-3)
    assert c["design_can_reach_significance"] is False
    assert c["min_p"] == pytest.approx(0.10)


def test_compare_flags_an_effect_smaller_than_its_own_noise():
    """The saturated-family live run: +0.074 against a pooled sd of ~0.083 --
    the failure this repository already discovered by hand."""
    c = compare([0.7778, 0.8889, 1.0], [0.8889, 1.0, 1.0], "autarky", "free_trade")
    assert c["interpretable"] is False
    assert abs(c["difference"]) < c["pooled_sd"]


def test_monte_carlo_kicks_in_for_large_designs_and_never_returns_zero():
    r = permutation_test(list(range(12)), list(range(6, 18)), max_exact=100, reps=500)
    assert r["method"] == "monte_carlo"
    assert r["p"] > 0.0


def test_fmt_is_a_table_cell():
    assert fmt(bootstrap_ci([1.0, 1.0, 1.0])) == "1.000 [1.000, 1.000] (n=3)"
