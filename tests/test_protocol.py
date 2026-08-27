"""The second load-bearing archetype, and the slack it introduces.

`lexicon` made capability depend on the library by making the doctrine the
ANSWER KEY: P(solve | doctrine) = 1 by construction, so an institutional
comparison over it returns 1 - 1/F as an identity and the scripted oracle
reproduces the "live" numbers to four decimals. `protocol` carries a PROCEDURE
instead — necessary but not sufficient — so execution can fail and the outcome
depends on the agent rather than on the configuration.

These tests assert the properties that make that true, and would fail if the
archetype drifted back into being an answer key.
"""
from __future__ import annotations

import random

import pytest

from skill_diplomacy.bank.base import verify
from skill_diplomacy.bank.generators.protocol import (
    ProtocolGenerator, apply_protocol, poison_detectability, poison_protocol_body,
    protocol_spec_from_body)
from skill_diplomacy.bank.variants import make_bank
from skill_diplomacy.experiment.grid import TrialConfig, run_trial
from skill_diplomacy.experiment.oracle import make_oracle
from skill_diplomacy.harness.fallible import FallibleModel, step_count
from skill_diplomacy.institutions.institutions import is_poisoned_body, poison_artifact
from skill_diplomacy.institutions.quarantine import QuarantineLevel as Q


# -- the doctrine is a procedure, not an answer key --------------------------

def test_the_doctrine_reproduces_ground_truth_exactly():
    """Necessary: a doctrine that does not determine the answer is not a
    load-bearing artifact, it is noise."""
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    spec = protocol_spec_from_body(g.reference_body())
    rng = random.Random(1)
    for _ in range(200):
        t = g.generate(rng)
        assert apply_protocol(spec, t.meta["record"]) == t.answer


def test_the_doctrine_contains_no_answer():
    """The distinguishing property against `lexicon`. A lexicon doctrine carries
    the value of every glyph, so the task is a lookup. A protocol doctrine
    carries weights and a substitution table, and the check character still has
    to be computed."""
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    body = g.reference_body()
    rng = random.Random(2)
    answers = {g.generate(rng).answer for _ in range(50)}
    # the check alphabet appears in the doctrine, but no instance's answer is
    # recoverable from it without executing the procedure
    assert "Check alphabet:" in body
    assert len(answers) > 1, "a family with one answer is not a family"


def test_the_task_is_unanswerable_without_the_doctrine():
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    t = g.generate(random.Random(3))
    assert protocol_spec_from_body(t.prompt) is None
    # chance over the check alphabet is the floor
    assert 1 / len(g.check_alphabet) < 0.1


def test_variants_are_different_bodies_of_knowledge():
    bank = make_bank(3, archetypes=["protocol"])
    assert list(bank) == ["protocol", "protocol2", "protocol3"]
    rng_answers = []
    for gen in bank.values():
        rng_answers.append(gen.generate(random.Random(11)).answer)
    assert len(set(rng_answers)) > 1, "variants must disagree on the same record"


# -- slack: execution can fail, and how often is a parameter -----------------

def test_step_count_is_monotone_in_difficulty():
    short = ProtocolGenerator(spec_seed=0, record_len=4).generate(random.Random(5))
    long_ = ProtocolGenerator(spec_seed=0, record_len=10).generate(random.Random(5))
    assert step_count(long_.prompt) > step_count(short.prompt)


def test_a_fallible_agent_fails_more_on_a_longer_procedure():
    """Errors compound along a procedure, which is what makes `record_len` a
    difficulty dial rather than a cosmetic one."""
    policy = make_oracle(lambda s, f: False)
    rates = []
    for record_len in (4, 12):
        g = ProtocolGenerator(spec_seed=0, record_len=record_len)
        body = g.reference_body()
        m = FallibleModel(policy, reliability=0.95, seed=0)
        rng = random.Random(7)
        ok = 0
        for _ in range(120):
            t = g.generate(rng)
            prompt = f"{body}\n\n# Task (protocol)\nprotocol-doctrine\n{t.prompt}"
            ok += verify(t, m.complete("state A.", prompt).text)
        rates.append(ok / 120)
    assert rates[0] > rates[1], f"longer records must be harder: {rates}"


def test_reliability_one_is_the_perfect_solver():
    policy = make_oracle(lambda s, f: False)
    m = FallibleModel(policy, reliability=1.0, seed=0)
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    body = g.reference_body()
    rng = random.Random(9)
    for _ in range(50):
        t = g.generate(rng)
        prompt = f"{body}\n\n# Task (protocol)\nprotocol-doctrine\n{t.prompt}"
        assert verify(t, m.complete("state A.", prompt).text)
    assert m.corrupted == 0


def test_the_fallible_coin_is_keyed_on_content_not_call_order():
    """Adoption decisions change how many calls precede any given one. Seeding on
    call order would make a trial's noise depend on unrelated institutional
    choices, which reads as stochasticity and is not."""
    policy = make_oracle(lambda s, f: False)
    a = FallibleModel(policy, reliability=0.9, seed=0)
    b = FallibleModel(policy, reliability=0.9, seed=0)
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    body = g.reference_body()
    t = g.generate(random.Random(4))
    prompt = f"{body}\n\n# Task (protocol)\nprotocol-doctrine\n{t.prompt}"
    for _ in range(5):                      # burn calls on `b` only
        b.complete("state A.", "unrelated prompt")
    assert a.complete("state A.", prompt).text == b.complete("state A.", prompt).text


# -- contamination, at two detectabilities ----------------------------------

def test_both_poison_modes_are_recognised_as_poison():
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    for mode in ("weight", "substitution"):
        assert is_poisoned_body(poison_protocol_body(g.reference_body(), mode))
    assert not is_poisoned_body(g.reference_body())


def test_a_poisoned_spec_parses_as_poisoned():
    """The failure this guards against is the worst kind available here: a
    corrupted doctrine that parses as clean reads as 'screening works' while
    measuring nothing. It has happened once already (the lexicon glyph regex)."""
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    clean = protocol_spec_from_body(g.reference_body())
    for mode in ("weight", "substitution"):
        bad = protocol_spec_from_body(poison_protocol_body(g.reference_body(), mode))
        assert bad is not None
        assert bad != clean, f"{mode} poison parsed as clean"


def test_the_two_poison_modes_differ_by_an_order_of_magnitude_in_detectability():
    """This span is the axis the screening experiment is about: it turns one
    contrast into a sweep over how rare a defect's symptoms are."""
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    loud = poison_detectability(g, "weight")
    quiet = poison_detectability(g, "substitution")
    assert loud > 0.8, loud
    assert 0.05 < quiet < 0.35, quiet
    assert loud > 4 * quiet


def test_poison_artifact_dispatches_on_protocol_content():
    g = ProtocolGenerator(spec_seed=0, record_len=4)
    art = {"name": "protocol-doctrine", "body": g.reference_body(), "scripts": {}}
    out = poison_artifact(art)
    assert is_poisoned_body(out["body"])
    assert poison_artifact(out)["body"] == out["body"], "must be idempotent"


# -- the trial-level property that motivates the archetype -------------------

def test_the_institutional_gap_stops_being_an_identity():
    """Over `lexicon` the autarky/free-trade gap is 1 - 1/F for every model,
    because P(solve | doctrine) = 1. Over `protocol` with a fallible agent it
    depends on the agent, which is what makes it a measurement."""
    def gap(archetype, reliability):
        out = {}
        for inst in ("autarky", "free_trade"):
            cfg = TrialConfig(institution=inst, quarantine=Q.NONE, seed=0,
                              rounds=2, tasks_per_round=3, k_trials=1, n_states=3,
                              n_variants=3, archetypes=(archetype,),
                              seed_references=True)
            m = FallibleModel(make_oracle(lambda s, f: False),
                              reliability=reliability, seed=0)
            out[inst] = run_trial(cfg, model=m)["mean_capability"]
        return out["free_trade"] - out["autarky"]

    identity = 1 - 1 / 3
    assert gap("lexicon", 1.0) == pytest.approx(identity, abs=0.01)
    assert gap("protocol", 1.0) == pytest.approx(identity, abs=0.01)
    # ...but only the perfect solver sits on the identity
    assert gap("protocol", 0.97) < identity - 0.2


def test_the_self_edit_gate_trap_is_closed():
    """`gate_self_edits=True` reuses the import quarantine tier, so with
    quarantine=NONE it gated nothing while reading as though it did."""
    with pytest.raises(ValueError, match="gates nothing"):
        run_trial(TrialConfig(institution="autarky", quarantine=Q.NONE,
                              gate_self_edits=True, seed=0, rounds=1,
                              tasks_per_round=1, k_trials=1, n_states=3,
                              n_variants=1))


def _cap(mode, improve, gated, reliability=0.98, seed=0):
    cfg = TrialConfig(institution="autarky",
                      quarantine=Q.REGRESSION if gated else Q.NONE,
                      gate_self_edits=gated, self_improve=improve,
                      self_edit_mode=mode, seed=seed, rounds=4, tasks_per_round=3,
                      k_trials=1, n_states=3, n_variants=3,
                      archetypes=("protocol",), seed_references=True)
    m = FallibleModel(make_oracle(lambda s, f: False),
                      reliability=reliability, seed=seed)
    return run_trial(cfg, model=m)["mean_capability"]


def test_a_replacing_edit_destroys_an_endowed_doctrine():
    """An agent handed a correct procedure, failing occasionally, overwrites it
    with the stand-in's content-free playbook and does not recover."""
    off = _cap("replace", improve=False, gated=False)
    on = _cap("replace", improve=True, gated=False)
    assert on < off - 0.15, (on, off)


def test_an_appending_edit_does_not():
    """Same loop, same failures, same absence of a gate — the only difference is
    whether the prior doctrine survives the edit. This is the sensitivity that
    localises the damage to the operator."""
    off = _cap("append", improve=False, gated=False)
    on = _cap("append", improve=True, gated=False)
    assert on > off - 0.05, (on, off)


def test_the_gate_only_matches_never_improving_it_does_not_beat_it():
    """The correction to an earlier claim of mine. Under `replace` the gated arm
    equals the never-improve arm; it does not exceed it. So this is not evidence
    that screening keeps good edits — it is evidence that rejecting every edit
    beats this loop, which is a different and much weaker statement."""
    off = _cap("replace", improve=False, gated=False)
    gated = _cap("replace", improve=True, gated=True)
    assert gated == pytest.approx(off, abs=1e-9), (gated, off)


def test_a_self_edit_is_never_accepted_on_an_empty_suite():
    """The defect that made the earlier claim wrong: an agent with no regression
    history had every self-edit waved through, 492 of 492 across the sweep, and
    that was reported as screening."""
    from skill_diplomacy.institutions.quarantine import (QuarantineLevel,
                                                         run_quarantine)
    accepted = run_quarantine(QuarantineLevel.REGRESSION, [], [],
                              evaluate=lambda t: True, empty_suite_passes=False)
    assert accepted.accepted is False
    assert accepted.vacuous is True
    waved = run_quarantine(QuarantineLevel.REGRESSION, [], [],
                           evaluate=lambda t: True, empty_suite_passes=True)
    assert waved.accepted is True
    assert waved.vacuous is True, "a vacuous pass must be marked as one"


def test_at_perfect_reliability_every_arm_is_identical():
    """A consistency check rather than a control: improve_from_failure is called
    zero times in all three arms, so they execute identical code."""
    vals = {(m, im, g): _cap(m, im, g, reliability=1.0)
            for m in ("replace", "append")
            for im, g in ((False, False), (True, False), (True, True))}
    assert len(set(vals.values())) == 1, vals
