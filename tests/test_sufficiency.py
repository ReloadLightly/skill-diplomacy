"""The acceptance rule dominates the screening depth.

A screen drawing k independent probes against a defect wrong on a fraction d of
instances should miss it with probability (1-d)^k. That holds only if a single
failure is disqualifying. Under the proportional rule the tier shipped with
(accept if 60% of probes pass) the arithmetic reverses below the rule's
tolerance, because adding probes concentrates the observed failure fraction on d
and removes the chance rejections a shallow screen got for free.

These pin both halves: that the strict rule tracks the analytic prediction — an
internal-validity check the harness has to pass before any novel screening claim
is trusted — and that the proportional rule inverts.
"""
from __future__ import annotations

import pytest

from run_sufficiency import probes_needed, theoretical_admission
from skill_diplomacy.bank.generators.protocol import (ProtocolGenerator,
                                                      poison_detectability)
from skill_diplomacy.experiment.grid import TrialConfig, run_trial
from skill_diplomacy.institutions.institutions import AdversarialTrade
from skill_diplomacy.institutions.quarantine import QuarantineLevel as Q


def _admitted(entries: int, probes: int, threshold: float, seeds: int = 3) -> float:
    adopted = offered = 0
    for s in range(seeds):
        r = run_trial(TrialConfig(
            institution="adversarial_trade", quarantine=Q.REGRESSION_PLUS_PROBES,
            seed=s, rounds=3, tasks_per_round=2, k_trials=1, n_states=6,
            n_variants=4, archetypes=("protocol",), seed_references=True,
            n_probes=probes, fresh_probes=True,
            protocol_poison_entries=entries, probe_threshold=threshold))
        p = r["poison_spread"]
        adopted += p["adopted"]
        offered += p["offered"]
    assert offered > 0, "no poison offered — the experiment would be vacuous"
    return adopted / offered


# -- the detectability dial --------------------------------------------------

def test_corrupting_more_entries_raises_detectability_monotonically():
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    ds = [poison_detectability(g, "substitution", 400, n_entries=k)
          for k in (1, 3, 8, 24)]
    assert ds == sorted(ds), ds
    assert ds[0] < 0.3 and ds[-1] > 0.9, ds


def test_probes_needed_matches_the_closed_form():
    assert probes_needed(0.5, 0.10) == 4        # 0.5^4 = 0.0625 <= 0.10
    assert probes_needed(0.9, 0.10) == 1
    assert probes_needed(0.0) == float("inf")


# -- the rule ---------------------------------------------------------------

def test_a_strict_rule_tracks_the_analytic_prediction():
    """The internal-validity check. If the harness cannot recover (1-d)^k in the
    regime where that is the right model, no screening claim it makes is
    trustworthy."""
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    d = poison_detectability(g, "substitution", 600, n_entries=3)
    for k in (1, 2, 4):
        measured = _admitted(3, k, threshold=1.0)
        assert measured == pytest.approx(theoretical_admission(d, k), abs=0.15), (
            f"k={k}: measured {measured:.3f} vs theory "
            f"{theoretical_admission(d, k):.3f}")


def test_a_strict_rule_makes_admission_fall_with_depth():
    deep, shallow = _admitted(1, 8, threshold=1.0), _admitted(1, 1, threshold=1.0)
    assert deep < shallow, (deep, shallow)


def test_a_proportional_rule_inverts_below_its_own_tolerance():
    """The finding. At d = 0.18 the rule tolerates up to 40% failures, so adding
    probes drives admission toward certainty rather than toward zero."""
    shallow = _admitted(1, 1, threshold=0.6)
    deep = _admitted(1, 16, threshold=0.6)
    assert deep > shallow, (shallow, deep)
    assert deep > 0.9, deep


def test_the_two_rules_diverge_only_for_quiet_defects():
    """A loud defect is caught by either rule, which is why a contamination
    experiment run only on loud defects concludes that screening works."""
    quiet_strict, quiet_prop = _admitted(1, 8, 1.0), _admitted(1, 8, 0.6)
    loud_strict, loud_prop = _admitted(12, 8, 1.0), _admitted(12, 8, 0.6)
    assert quiet_prop - quiet_strict > 0.4, (quiet_strict, quiet_prop)
    assert abs(loud_prop - loud_strict) < 0.1, (loud_strict, loud_prop)


# -- the guard that would have caught the vacuous sweep ----------------------

def test_an_unpoisonable_bank_is_refused_rather_than_reported_as_clean():
    """`protocol` was omitted from AdversarialTrade.poison_families when the
    archetype was added, so a full sweep reported 0 offered / 0 adopted — which
    every downstream metric renders as an admission rate of 0.0, i.e. perfect
    screening. That is the most dangerous silent failure available here."""
    with pytest.raises(ValueError, match="none of which is poisonable"):
        run_trial(TrialConfig(
            institution="adversarial_trade", quarantine=Q.REGRESSION, seed=0,
            rounds=1, tasks_per_round=1, k_trials=1, n_states=3, n_variants=1,
            archetypes=("calendar_math",)))


def test_every_load_bearing_archetype_is_poisonable():
    inst = AdversarialTrade()
    for family in ("unit_chain", "lexicon", "lexicon3", "protocol", "protocol2"):
        assert inst.poisons_family(family), family
