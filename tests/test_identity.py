"""Content identity: one hash, over content, joinable across hops.

These lock a defect that silently corrupted three published quantities. Skill
identity used to be the sha256 of the whole SKILL.md, frontmatter included, so
`provenance.imported_from` was part of the digest and a doctrine's hash changed
every time it was copied. The exchange path in `experiment/grid.py` meanwhile
hashed name+body+scripts. Consequences, each asserted against below:

  * `distinct_bodies` (the RQ2 monoculture signal) counted COPIES, not contents,
    so a fully converged population reported maximal diversity;
  * `poison_spread.unique_offered` counted one contaminant once per laundering
    hop, inflating it by exactly the transitive spread it exists to measure;
  * `origin_hash` and the `content_hash` on `adoption_decision` events lived in
    different hash spaces, so lineage could not be reconstructed from the log.
"""
from __future__ import annotations

import pytest

from skill_diplomacy.experiment.grid import TrialConfig, _artifact_hash, run_trial
from skill_diplomacy.institutions.quarantine import QuarantineLevel
from skill_diplomacy.metrics.metrics import distinct_bodies
from skill_diplomacy.skills.format import SkillLibrary, artifact_hash

BODY = "Strategy: one doctrine, held identically by every state.\n1. Do the thing."


def _pop(tmp_path):
    libs = {n: SkillLibrary(tmp_path / n, n) for n in "ABC"}
    libs["A"].add_skill("doc", "a doctrine", BODY)
    libs["B"].import_skill(libs["A"].export_skill("doc"), "A")
    # C launders it through B rather than taking it from the author
    libs["C"].import_skill(libs["B"].export_skill("doc"), "B")
    return libs


def test_identical_bodies_hash_identically_however_they_were_acquired(tmp_path):
    libs = _pop(tmp_path)
    hashes = {n: lib.content_hash("doc") for n, lib in libs.items()}
    assert libs["A"].body("doc") == libs["B"].body("doc") == libs["C"].body("doc")
    assert len(set(hashes.values())) == 1, hashes


def test_distinct_bodies_counts_contents_not_copies(tmp_path):
    libs = _pop(tmp_path)
    assert distinct_bodies(list(libs.values())) == 1
    # a genuinely different body must still register as distinct
    libs["C"].add_skill("doc", "a doctrine", BODY + "\nErratum: use 42 instead.")
    assert distinct_bodies(list(libs.values())) == 2


def test_lineage_joins_back_to_the_author_through_an_intermediary(tmp_path):
    """The laundering case RQ3 is about: C never met A, but the artifact it
    holds must still be attributable to the content A published."""
    libs = _pop(tmp_path)
    assert libs["C"].meta("doc").provenance["origin_hash"] == libs["A"].content_hash("doc")


def test_library_and_exchange_paths_share_one_hash_space(tmp_path):
    libs = _pop(tmp_path)
    art = libs["A"].export_skill("doc")
    assert _artifact_hash(art) == libs["A"].content_hash("doc")
    assert artifact_hash(art["name"], art["body"], art["scripts"]) == _artifact_hash(art)


def test_frontmatter_churn_does_not_change_identity(tmp_path):
    """Re-authoring the same text bumps `version` in the frontmatter. That is
    bookkeeping, not a new doctrine, and must not read as diversity."""
    lib = SkillLibrary(tmp_path / "A", "A")
    lib.add_skill("doc", "a doctrine", BODY)
    first = lib.content_hash("doc")
    lib.add_skill("doc", "a doctrine", BODY)
    assert lib.meta("doc").version == 2
    assert lib.content_hash("doc") == first


def test_a_converged_population_reports_as_converged():
    """End to end: under free trade over one archetype every state ends holding
    the same three doctrines, so the monoculture signal must bottom out at the
    number of distinct doctrines in the world -- not at the number of copies."""
    cfg = TrialConfig(institution="free_trade", quarantine=QuarantineLevel.NONE,
                      seed=0, rounds=2, tasks_per_round=1, k_trials=1,
                      n_states=3, n_variants=3, archetypes=("lexicon",),
                      seed_references=True, endowment="uniform")
    r = run_trial(cfg)
    n_doctrines = r["n_families"]
    assert r["distinct_bodies"] == n_doctrines, (
        f"{r['distinct_bodies']} distinct bodies reported for {n_doctrines} "
        f"doctrines across {r['n_states']} states -- identity is counting copies")
    assert r["library_similarity"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# endowment dispatch — a misconfiguration must not be silently reinterpreted
# ---------------------------------------------------------------------------

def _endow(**kw):
    return TrialConfig(institution="free_trade", quarantine=QuarantineLevel.NONE,
                       seed=0, rounds=1, tasks_per_round=1, k_trials=1,
                       n_states=6, n_variants=3, **kw)


def test_step_without_great_powers_is_refused_not_silently_uniform():
    """It used to return all-ones, so the arm ran at exact parity — the one
    condition under which relative-gains reasoning is definitionally inert.
    A null from that arm looks like evidence and is not."""
    with pytest.raises(ValueError, match="great_powers"):
        run_trial(_endow(endowment="step"))


def test_great_powers_without_step_is_refused_not_silently_step():
    """`zipf + --great-powers` used to take the step branch and discard zipf,
    then label the run 'step' whatever flag was passed."""
    with pytest.raises(ValueError, match="step"):
        run_trial(_endow(endowment="zipf", n_great_powers=2))


def test_unknown_endowment_is_refused():
    with pytest.raises(ValueError, match="unknown endowment"):
        run_trial(_endow(endowment="pareto"))


def test_summary_labels_the_endowment_actually_used():
    r = run_trial(_endow(endowment="step", n_great_powers=2, great_power_weight=8))
    assert r["endowment"] == "step"
    assert r["n_great_powers"] == 2 and r["great_power_weight"] == 8
    z = run_trial(_endow(endowment="zipf", great_power_weight=8))
    assert z["endowment"] == "zipf" and z["n_great_powers"] == 0


def test_step_and_zipf_actually_grade_the_endowment():
    """The point of a graded endowment is unequal shard sizes. If they come back
    equal the distribution did not apply."""
    step = run_trial(_endow(endowment="step", n_great_powers=2, great_power_weight=8))
    zipf = run_trial(_endow(endowment="zipf", great_power_weight=8))
    flat = run_trial(_endow(endowment="uniform"))
    assert len(set(step["shard_sizes"].values())) > 1, step["shard_sizes"]
    assert len(set(zipf["shard_sizes"].values())) > 1, zipf["shard_sizes"]
    assert len(set(flat["shard_sizes"].values())) == 1, flat["shard_sizes"]
