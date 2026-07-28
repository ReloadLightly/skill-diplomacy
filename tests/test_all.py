"""v0 test suite. The generator tests recompute ground truth INDEPENDENTLY of
the generator's own arithmetic where possible — the handoff brief's verifier-
quality discipline applied to ourselves."""
import datetime as dt
import math
import random

import pytest

from skill_diplomacy.bank.base import TaskInstance, extract_answer, shard_families, verify
from skill_diplomacy.bank.generators.calendar_math import CalendarMathGenerator
from skill_diplomacy.bank.generators.modmath import ModMathGenerator
from skill_diplomacy.bank.generators.unit_chain import UnitChainGenerator
from skill_diplomacy.harness.budget import BudgetExceeded, BudgetMeter
from skill_diplomacy.harness.events import EventLog
from skill_diplomacy.institutions.institutions import (AdversarialTrade, Autarky,
                                                       Clubs, FreeTrade,
                                                       poison_artifact)
from skill_diplomacy.institutions.quarantine import (QuarantineLevel,
                                                     QuarantineReport,
                                                     run_quarantine)
from skill_diplomacy.metrics.metrics import gini, pass_k
from skill_diplomacy.skills.format import SkillLibrary, jaccard


# ---------------- generators: independent ground truth ----------------

def test_unit_chain_truth():
    gen = UnitChainGenerator()
    for t in gen.batch(seed=7, n=50):
        expected = t.meta["qty"]
        for f in t.meta["factors"]:
            expected *= f
        assert t.answer == str(expected)
        assert verify(t, f"blah blah\nANSWER: {expected}")
        assert not verify(t, f"ANSWER: {expected + 1}")


def test_calendar_truth():
    gen = CalendarMathGenerator()
    for t in gen.batch(seed=11, n=50):
        d0 = dt.date.fromisoformat(t.meta["start"])
        target = d0 + dt.timedelta(days=t.meta["delta"])
        expected = target.strftime("%A") if t.meta["mode"] == "weekday" else target.isoformat()
        assert t.answer == expected


def test_modmath_truth():
    gen = ModMathGenerator()
    for t in gen.batch(seed=13, n=50):
        a, b, m = t.meta["a"], t.meta["b"], t.meta["m"]
        # independent recomputation by repeated squaring, not pow()
        result, base, e = 1, a % m, b
        while e:
            if e & 1:
                result = result * base % m
            base = base * base % m
            e >>= 1
        assert t.answer == str(result)


def test_determinism_and_freshness():
    gen = UnitChainGenerator()
    assert [t.prompt for t in gen.batch(3, 5)] == [t.prompt for t in gen.batch(3, 5)]
    assert gen.batch(3, 5)[0].prompt != gen.batch(4, 5)[0].prompt


def test_extract_answer_takes_last():
    assert extract_answer("ANSWER: 4\nrethinking...\nANSWER: 7") == "7"
    assert extract_answer("no answer line") is None


def test_numeric_tolerance():
    t = TaskInstance("x", "f", "p", "2.5")
    assert verify(t, "ANSWER: 2.5000000")


# ---------------- harness ----------------

def test_budget_meter_and_exhaustion():
    b = BudgetMeter(max_tokens=100, max_rollouts=10)
    b.charge(40, 40, 1)
    b.charge(30, 0, 1, kind="quarantine")  # crosses ceiling: recorded, next raises
    assert b.spent_tokens == 110 and b.quarantine_tokens == 30
    assert b.snapshot()["governance_overhead"] == pytest.approx(30 / 110)
    with pytest.raises(BudgetExceeded):
        b.charge(1, 0, 1)


def test_event_log_roundtrip(tmp_path):
    log = EventLog(tmp_path / "e.jsonl")
    log.append("attempt", state="A", success=True)
    log.append("attempt", state="B", success=False)
    assert len(log.read()) == 2
    assert log.by_state("A")[0]["success"] is True
    # append-only across re-open, seq continues
    log2 = EventLog(tmp_path / "e.jsonl")
    log2.append("attempt", state="A", success=False)
    assert [e["seq"] for e in log2.read()] == [0, 1, 2]


# ---------------- skills ----------------

def test_skill_library_roundtrip(tmp_path):
    lib = SkillLibrary(tmp_path / "A", owner="A")
    lib.add_skill("unit-chain-doctrine", "Chains.", "Multiply all factors.",
                  scripts={"chain.py": "def solve(): pass\n"})
    assert lib.skill_names() == ["unit-chain-doctrine"]
    assert lib.meta("unit-chain-doctrine").version == 1
    lib.add_skill("unit-chain-doctrine", "Chains.", "Multiply all factors carefully.")
    assert lib.meta("unit-chain-doctrine").version == 2
    assert "chain.py" in lib.scripts("unit-chain-doctrine")
    assert "unit-chain-doctrine" in lib.render_index()


def test_import_provenance_and_jaccard(tmp_path):
    a = SkillLibrary(tmp_path / "A", owner="A")
    b = SkillLibrary(tmp_path / "B", owner="B")
    a.add_skill("s", "d", "alpha beta gamma delta epsilon zeta eta theta")
    art = a.export_skill("s")
    b.import_skill(art, exporter="A")
    assert b.meta("s").provenance["imported_from"] == "A"
    assert jaccard(a, b) == 1.0
    b.add_skill("t", "d", "totally different words entirely here now yes indeed")
    assert 0 < jaccard(a, b) < 1


# ---------------- institutions & quarantine ----------------

def test_institution_visibility():
    names = ["A", "B", "C", "D"]
    assert Autarky(states=names).visible("A") == []
    assert set(FreeTrade(states=names).visible("A")) == {"B", "C", "D"}
    clubs = Clubs(states=names, clubs=[["A", "B"], ["C", "D"]])
    assert clubs.visible("A") == ["B"] and clubs.visible("C") == ["D"]
    adv = AdversarialTrade(states=names, poisoner="D")
    assert adv.is_poisoner("D") and not adv.is_poisoner("A")


def test_poison_marks_ground_truth_only():
    art = {"name": "s", "description": "d", "body": "Do the right thing.",
           "scripts": {}, "content_hash": "x", "provenance": {}}
    p = poison_artifact(art)
    assert p["_poisoned"] and "Shortcut" in p["body"]
    assert "_poisoned" not in art  # original untouched


def test_quarantine_levels():
    reg = [TaskInstance(f"r{i}", "f", "p", "1") for i in range(4)]
    probes = [TaskInstance(f"p{i}", "f", "p", "1") for i in range(4)]
    # NONE accepts blindly
    assert run_quarantine(QuarantineLevel.NONE, reg, probes, lambda t: False).accepted
    # REGRESSION strict: one failure rejects
    fails_one = lambda t: t.id != "r0"
    assert not run_quarantine(QuarantineLevel.REGRESSION, reg, probes, fails_one).accepted
    assert run_quarantine(QuarantineLevel.REGRESSION, reg, probes, lambda t: True).accepted
    # PROBES: regression fine but probes below threshold → reject
    probe_fail = lambda t: not t.id.startswith("p")
    rep = run_quarantine(QuarantineLevel.REGRESSION_PLUS_PROBES, reg, probes, probe_fail)
    assert rep.regression_passed == 4 and rep.probes_passed == 0 and not rep.accepted


# ---------------- metrics ----------------

def test_gini_known_values():
    assert gini([1, 1, 1, 1]) == pytest.approx(0.0)
    assert gini([0, 0, 0, 1]) == pytest.approx(0.75)
    assert gini([]) == 0.0


def test_pass_k_estimator():
    # 4 trials, 2 successes, k=2 → C(2,2)/C(4,2) = 1/6
    assert pass_k({"t": [True, True, False, False]}, 2) == pytest.approx(1 / 6)
    # all succeed → 1; fewer trials than k → skipped
    assert pass_k({"t": [True] * 3, "u": [True]}, 2) == pytest.approx(1.0)


def test_sharding_disjoint():
    shards = shard_families(["A", "B", "C"], ["f1", "f2", "f3"])
    assert set(shards.values()) == {"f1", "f2", "f3"}
