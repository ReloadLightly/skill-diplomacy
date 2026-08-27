"""Sprint-2 tests: the four defects, the scarcity dial, and the export layer.

The discipline here is the one the v1 review complained was missing. A gate that
is never tested against its own absence is not evidence that the gate does
anything — so several of these tests assert a DIFFERENCE between the gated and
ungated configuration, and would fail if the gate were deleted. Tests that would
still pass with the mechanism removed are marked as such and kept only as
smoke tests.
"""
from __future__ import annotations

import random

import pytest

from skill_diplomacy.bank.variants import make_bank
from skill_diplomacy.experiment.grid import (TrialConfig, _artifact_hash, _bank,
                                             _roster, _shards, run_trial)
from skill_diplomacy.experiment.oracle import make_oracle
from skill_diplomacy.institutions.exchange import (ExchangeContext, RelativeGains,
                                                   make_policy)
from skill_diplomacy.institutions.institutions import (POISON_TEXT, AdversarialTrade,
                                                       is_poisoned_artifact,
                                                       is_poisoned_body,
                                                       poison_artifact)
from skill_diplomacy.institutions.quarantine import QuarantineLevel

NONE = QuarantineLevel.NONE
PROBES = QuarantineLevel.REGRESSION_PLUS_PROBES


def _cfg(**kw):
    base = dict(institution="free_trade", quarantine=NONE, seed=0, rounds=2,
                tasks_per_round=2, k_trials=2)
    base.update(kw)
    return TrialConfig(**base)


# ---------------------------------------------------------------------------
# defect 3.1 — poison is a property of the ARTIFACT, not of its sender
# ---------------------------------------------------------------------------

def test_poison_survives_export_import_reexport():
    art = {"name": "unit-chain-doctrine", "body": "Strategy: do the thing.",
           "scripts": {}}
    once = poison_artifact(art)
    assert is_poisoned_artifact(once)
    # laundering: strip the convenience flag, keep only the text, as a real
    # re-export through an intermediary's SkillLibrary would.
    laundered = {k: v for k, v in once.items() if k != "_poisoned"}
    assert is_poisoned_artifact(laundered), "ground truth must live in the body"
    assert is_poisoned_body(laundered["body"])


def test_poisoning_is_idempotent():
    art = {"name": "d", "body": "base", "scripts": {}}
    twice = poison_artifact(poison_artifact(art))
    assert twice["body"].count(POISON_TEXT.strip()) == 1


def test_oracle_ground_truth_is_content_derived():
    """The callable-registry form must read the installed body, so a doctrine
    that reached a state through an honest intermediary still misbehaves."""
    seen = {}

    def lookup(state, family):
        seen[(state, family)] = True
        return True          # pretend the installed body is poisoned

    policy = make_oracle(lookup)
    deep = ("Available skills:\n- unit-chain-doctrine (v1): d\n\n# Task (unit_chain)\n"
            "Conversion rules:\n- 1 flib = 3 blem\n- 1 blem = 5 quon\n- 1 quon = 7 drap\n"
            "How many drap are in 4 flib?\nANSWER: <integer>")
    out = policy("You are the strategist of state C. Solve tasks exactly;", deep)
    assert ("C", "unit_chain") in seen
    assert out.strip().endswith("140"), "poison must drop the first factor (4*5*7)"


def test_transitive_poison_is_measured_not_zero():
    """RQ3 has an observable. In v1 the transitive count could not be non-zero
    because the flag was keyed on the exporter; here A poisons, B carries, and
    the summary must at minimum expose the decomposition."""
    r = run_trial(_cfg(institution="adversarial_trade", n_states=6, rounds=3,
                       n_variants=2))
    spread = r["poison_spread"]
    assert set(spread) >= {"offered", "adopted", "first_hand_adopted",
                           "transitive_adopted", "unique_offered"}
    assert spread["adopted"] == spread["first_hand_adopted"] + spread["transitive_adopted"]
    assert spread["offered"] > 0, "adversarial trade must actually offer poison"


def test_probes_arm_blocks_poison_that_none_arm_accepts():
    """The gate must make a difference. Fails if quarantine is removed."""
    ungated = run_trial(_cfg(institution="adversarial_trade", quarantine=NONE,
                             n_states=6, rounds=3, n_variants=2))
    gated = run_trial(_cfg(institution="adversarial_trade", quarantine=PROBES,
                           n_states=6, rounds=3, n_variants=2))
    assert ungated["poison_spread"]["adopted"] > 0
    assert gated["poison_spread"]["adopted"] < ungated["poison_spread"]["adopted"]


# ---------------------------------------------------------------------------
# defect 3.2 — denylist by content hash
# ---------------------------------------------------------------------------

def test_artifact_hash_keys_on_content_not_identity():
    a = {"name": "d", "body": "x", "scripts": {}}
    b = {"name": "d", "body": "x", "scripts": {}}
    c = {"name": "d", "body": "y", "scripts": {}}
    assert _artifact_hash(a) == _artifact_hash(b)
    assert _artifact_hash(a) != _artifact_hash(c)
    assert _artifact_hash(a) != _artifact_hash(poison_artifact(a))


def test_rejected_artifact_is_not_rescreened_every_round():
    """Screening cost must be per UNIQUE artifact. If the denylist were removed
    the same rejected body would be screened once per round and unique_screened
    would exceed the number of distinct artifacts on offer."""
    r = run_trial(_cfg(institution="adversarial_trade", quarantine=PROBES,
                       n_states=6, rounds=4, n_variants=2))
    assert r["unique_artifacts_screened"] > 0
    per_state = [s["rejected"] for s in r["states"].values()]
    assert sum(per_state) > 0, "the probes arm must reject something here"
    # every state's rejected set is a set of hashes, so it cannot double-count
    assert all(s["rejected"] <= s["screened"] for s in r["states"].values())


# ---------------------------------------------------------------------------
# defect 3.3 — self-edits are gated, and the gate is transactional
# ---------------------------------------------------------------------------

def test_self_edit_gate_changes_behaviour_when_enabled():
    """A test that fails if the gate is deleted: gating self-edits must charge
    a self-screen sub-account that is exactly zero when it is off.

    The third assertion used to be `on["governance_overhead"] >
    off["governance_overhead"]` — that governance always costs more when you buy
    more of it. It is now false, and the reason is worth keeping. Once the
    self-edit gate actually screens (it used to accept anything when the
    regression store was empty), it rejects the stand-in's content-free
    playbooks, so nothing enters circulation, so nobody pays to screen imports:
    import overhead falls to zero and total governance overhead falls with it.
    Screening self-edits is partly self-financing, because the artifacts it stops
    are artifacts everyone else would have paid to screen."""
    off = run_trial(_cfg(quarantine=PROBES, gate_self_edits=False, n_states=6,
                         n_variants=2))
    on = run_trial(_cfg(quarantine=PROBES, gate_self_edits=True, n_states=6,
                        n_variants=2))
    assert off["self_screen_overhead"] == 0.0
    assert on["self_screen_overhead"] > 0.0
    assert off["import_screen_overhead"] > 0.0
    assert on["import_screen_overhead"] < off["import_screen_overhead"]


def test_library_snapshot_restore_is_byte_exact():
    from pathlib import Path
    import tempfile
    from skill_diplomacy.skills.format import SkillLibrary
    with tempfile.TemporaryDirectory() as d:
        lib = SkillLibrary(Path(d) / "skills", owner="A")
        lib.add_skill("doc", "desc", "original body")
        snap = lib.snapshot("doc")
        before = (Path(d) / "skills" / "doc" / "SKILL.md").read_text()
        lib.add_skill("doc", "desc", "mutated body")
        assert (Path(d) / "skills" / "doc" / "SKILL.md").read_text() != before
        lib.restore("doc", snap)
        assert (Path(d) / "skills" / "doc" / "SKILL.md").read_text() == before


def test_restore_of_absent_skill_removes_it():
    from pathlib import Path
    import tempfile
    from skill_diplomacy.skills.format import SkillLibrary
    with tempfile.TemporaryDirectory() as d:
        lib = SkillLibrary(Path(d) / "skills", owner="A")
        snap = lib.snapshot("doc")           # None: nothing installed
        lib.add_skill("doc", "desc", "body")
        lib.restore("doc", snap)
        assert "doc" not in lib.skill_names()


# ---------------------------------------------------------------------------
# defect 3.4 — the governance budget decomposes
# ---------------------------------------------------------------------------

def test_governance_overhead_decomposes_into_import_and_self():
    r = run_trial(_cfg(quarantine=PROBES, gate_self_edits=True, n_states=6,
                       n_variants=2))
    total = r["governance_overhead"]
    parts = r["import_screen_overhead"] + r["self_screen_overhead"]
    assert total == pytest.approx(parts, abs=2e-3)


# ---------------------------------------------------------------------------
# the scarcity dial — variants
# ---------------------------------------------------------------------------

def test_one_variant_bank_is_the_v1_bank():
    bank = make_bank(1)
    assert list(bank) == ["unit_chain", "calendar_math", "modmath"]
    from skill_diplomacy.bank.generators.unit_chain import UnitChainGenerator
    stock = UnitChainGenerator().generate(random.Random(7))
    variant = bank["unit_chain"].generate(random.Random(7))
    assert stock.prompt == variant.prompt, "v1 prompts must be byte-identical"


def test_variants_are_disjoint_families_with_disjoint_surfaces():
    bank = make_bank(4)
    assert len(bank) == 12
    a = bank["unit_chain"].generate(random.Random(3))
    b = bank["unit_chain2"].generate(random.Random(3))
    assert a.family != b.family
    assert a.prompt != b.prompt, "a variant must not be a relabelling"


def test_variant_generators_compute_their_own_ground_truth():
    for fam, gen in make_bank(3).items():
        t = gen.generate(random.Random(11))
        assert t.family == fam
        assert t.answer, f"{fam} produced no ground truth"


def test_scarcity_is_what_makes_autarky_bite():
    """The negative result that motivated the variant bank, pinned as a test:
    with three families autarky already reaches 1/3 of the space, and with
    thirty it reaches 1/30. If someone shrinks the bank back, this fails."""
    small = run_trial(_cfg(institution="autarky", n_states=6, n_variants=1))
    large = run_trial(_cfg(institution="autarky", n_states=6, n_variants=5))
    assert large["mean_capability"] < small["mean_capability"] / 2


# ---------------------------------------------------------------------------
# endowment
# ---------------------------------------------------------------------------

def test_uniform_endowment_gives_every_state_one_shard():
    cfg = _cfg(n_states=9, n_variants=3)
    gens, fams = _bank(cfg)
    sh = _shards(cfg, _roster(cfg), fams)
    assert {len(v) for v in sh.values()} == {1}


def test_zipf_endowment_is_graded_and_covers_every_family():
    cfg = _cfg(n_states=15, n_variants=10, endowment="zipf", great_power_weight=8)
    gens, fams = _bank(cfg)
    sh = _shards(cfg, _roster(cfg), fams)
    sizes = sorted((len(v) for v in sh.values()), reverse=True)
    assert sizes[0] > sizes[-1], "zipf must actually be asymmetric"
    assert len(set(sizes)) >= 3, "and graded, not a two-level step"
    covered = {f for v in sh.values() for f in v}
    assert covered == set(fams), "every family must be someone's home shard"


def test_no_state_is_left_without_a_shard():
    cfg = _cfg(n_states=20, n_variants=1, endowment="zipf", great_power_weight=8)
    gens, fams = _bank(cfg)
    sh = _shards(cfg, _roster(cfg), fams)
    assert all(v for v in sh.values())


# ---------------------------------------------------------------------------
# the export layer
# ---------------------------------------------------------------------------

def test_open_policy_never_refuses():
    p = make_policy("open")
    ctx = ExchangeContext(libraries={"A": {"x"}, "B": set()})
    ok, _ = p.will_export(exporter="A", importer="B", skill="x", ctx=ctx)
    assert ok


def test_defector_never_exports():
    p = make_policy("defector")
    ctx = ExchangeContext(libraries={"A": {"x"}, "B": {"y", "z"}})
    ok, reason = p.will_export(exporter="A", importer="B", skill="x", ctx=ctx)
    assert not ok and reason == "defector"


def test_relative_gains_k_is_a_threshold_on_prospective_return():
    ctx = ExchangeContext(libraries={"A": {"x"}, "B": {"y", "z", "w"}})
    for k, expected in [(0, True), (3, True), (4, False)]:
        ok, _ = RelativeGains(sensitivity=k).will_export(
            exporter="A", importer="B", skill="x", ctx=ctx)
        assert ok is expected, f"k={k}"


def test_reciprocity_is_priced_not_a_boolean_override():
    """A past grant must add credit on the capability scale. If it were an
    unconditional override, k would stop mattering after the first exchange —
    which is exactly what flattened the first version of the dial sweep."""
    ctx = ExchangeContext(libraries={"A": {"x"}, "B": set()})
    p = RelativeGains(sensitivity=2, reciprocity_credit=1)
    assert not p.will_export(exporter="A", importer="B", skill="x", ctx=ctx)[0]
    ctx.record_grant("B", "A")          # B gave A something once
    assert not p.will_export(exporter="A", importer="B", skill="x", ctx=ctx)[0]
    ctx.record_grant("B", "A")          # twice: now the credit clears k=2
    assert p.will_export(exporter="A", importer="B", skill="x", ctx=ctx)[0]


def test_balance_mode_penalises_the_net_donor():
    ctx = ExchangeContext(libraries={"A": {"x", "y", "z"}, "B": {"w"}})
    ret = RelativeGains(mode="return").score({"x", "y", "z"}, {"w"})
    bal = RelativeGains(mode="balance").score({"x", "y", "z"}, {"w"})
    assert ret == 1 and bal == 1 - 3


def test_defectors_free_ride_and_depress_the_commons():
    """The reviewer's first question. Under scarcity, defectors must do better
    than cooperators and the population must do worse — a result that was
    unmeasurable at three families, where every arm returned 1.0."""
    none = run_trial(_cfg(n_states=9, n_variants=3, n_defectors=0))
    many = run_trial(_cfg(n_states=9, n_variants=3, n_defectors=6))
    assert many["mean_capability"] < none["mean_capability"]
    names = list(many["states"])
    defs_ = names[-6:]
    coop = [n for n in names if n not in defs_]
    dm = sum(many["states"][n]["final_capability"] for n in defs_) / len(defs_)
    cm = sum(many["states"][n]["final_capability"] for n in coop) / len(coop)
    assert dm > cm, "free-riding must pay privately while costing the commons"


def test_n_defectors_above_population_is_clamped():
    r = run_trial(_cfg(n_states=6, n_variants=2, n_defectors=99))
    assert r["exports"]["refusal_rate"] == 1.0


def test_export_decisions_are_logged_with_reasons():
    r = run_trial(_cfg(n_states=6, n_variants=2, export_policy="relative_gains",
                       relative_gains_sensitivity=3))
    e = r["exports"]
    assert e["requests"] > 0 and e["refused"] > 0
    assert e["reasons"], "refusals must carry an auditable reason"


def test_export_policy_appears_in_the_summary_key():
    r = run_trial(_cfg(export_policy="relative_gains", relative_gains_sensitivity=2,
                       n_states=6, n_variants=2))
    assert r["export_policy"] == "relative_gains"
    assert r["n_families"] == 6 and r["n_states"] == 6


# ---------------------------------------------------------------------------
# diversity (RQ2) and reproduction of v1
# ---------------------------------------------------------------------------

def test_diversity_metrics_are_reported():
    r = run_trial(_cfg(n_states=6, n_variants=2))
    assert 0.0 <= r["library_similarity"] <= 1.0
    assert r["distinct_bodies"] >= 1


def test_v1_defaults_still_reproduce_the_published_orderings():
    autarky = run_trial(_cfg(institution="autarky", rounds=3, tasks_per_round=3,
                             k_trials=3))
    free = run_trial(_cfg(institution="free_trade", rounds=3, tasks_per_round=3,
                          k_trials=3))
    clubs = run_trial(_cfg(institution="clubs", rounds=3, tasks_per_round=3,
                           k_trials=3))
    assert autarky["mean_capability"] == pytest.approx(1 / 3, abs=0.01)
    assert free["mean_capability"] == pytest.approx(1.0, abs=0.01)
    assert autarky["mean_capability"] < clubs["mean_capability"] < free["mean_capability"]
