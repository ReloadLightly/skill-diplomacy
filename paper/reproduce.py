"""One command that regenerates every deterministic number in the paper.

    python -m paper.reproduce            # run everything, print the table
    python -m paper.reproduce --check    # ...and fail if anything drifted
    python -m paper.reproduce --update   # re-lock the manifest after an
                                         # intended change

The README says "every headline number reproduces from one command". That was
true claim by claim — there was a command per claim — but there was no command
for the whole set and nothing that would notice if a refactor moved a number.
This is that command, and CI runs it on every push.

What is in scope. Only claims labelled `harness` in README.md, plus the
statistics computed over committed live artifacts (which are deterministic
functions of files in git even though the runs that produced those files were
not). Live *runs* cannot be re-executed here: they need a model, they cost
money, and they are stochastic. Those are checked differently — a live artifact
must carry a provenance block, and `--check` verifies that it does rather than
pretending the number is reproducible.

The distinction is the point. A reproducibility harness that quietly treats
live numbers as re-derivable would be making exactly the harness/live
conflation this repository exists to warn about.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from skill_diplomacy.experiment.grid import TrialConfig, aggregate, run_grid, run_trial
from skill_diplomacy.institutions.quarantine import QuarantineLevel
from skill_diplomacy.metrics.stats import (bootstrap_ci, min_achievable_p,
                                           permutation_test, proportion)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
MANIFEST = Path(__file__).resolve().parent / "manifest.json"

TOL = 1e-3   # numbers are rounded to 3-4 dp on the way out; drift beyond this
             # is a change in the mechanism, not in floating point.


# -- the claims --------------------------------------------------------------

def claim_v1_grid() -> dict:
    """README: 'the institution x quarantine grid'. The published capability
    ordering, the two governance overheads, and the screening-blindness pair."""
    rows = aggregate(run_grid(seeds=(0, 1, 2), rounds=3))
    by = {(r["institution"], r["quarantine"]): r for r in rows}
    probes = "regression_plus_probes"
    return {
        "autarky_capability": round(by[("autarky", "none")]["mean_capability"], 2),
        "free_trade_capability": round(by[("free_trade", "none")]["mean_capability"], 2),
        "clubs_capability": round(by[("clubs", "none")]["mean_capability"], 2),
        "adversarial_capability": round(by[("adversarial_trade", "none")]["mean_capability"], 2),
        "adversarial_probes_capability": round(by[("adversarial_trade", probes)]["mean_capability"], 2),
        "clubs_gini": round(by[("clubs", "none")]["capability_gini"], 2),
        "free_trade_probes_overhead": round(by[("free_trade", probes)]["governance_overhead"], 3),
        "adversarial_probes_overhead": round(by[("adversarial_trade", probes)]["governance_overhead"], 3),
        "poison_admitted_regression": by[("adversarial_trade", "regression")]["poison_adopted"],
        "poison_offered_regression": by[("adversarial_trade", "regression")]["poison_offered"],
        "poison_admitted_probes": by[("adversarial_trade", probes)]["poison_adopted"],
        "poison_offered_probes": by[("adversarial_trade", probes)]["poison_offered"],
    }


def claim_parity_and_scarcity() -> dict:
    """README currently states: 'Institutions have no measurable effect unless
    skills are scarce relative to the task space. With three task families every
    arrangement returns identical capability.'

    The second sentence does not reproduce, and the first conflates two separate
    preconditions. Measured here:

      * Under a UNIFORM endowment the relative-gains dial is a two-level step
        whatever the family count -- 3 families or 30, the sweep takes exactly
        two capability values. Parity, not abundance, is what makes the dial
        inert, which is the theoretically correct boundary condition: relative-
        gains reasoning has nothing to bite on when states are identical.
      * Under a GRADED (zipf) endowment the dial traces a curve at 3 families
        already. Scarcity does not switch the effect on; it sets the RESOLUTION
        at which the curve can be read -- 3 families give 3 distinct levels,
        12 families give 5 (30 families give 7 at the
        v2 default scale).
      * And 'every arrangement returns identical capability' is false for the
        institution dial too: at 3 families autarky is 0.33 against free trade
        1.00.

    The corrected claim is stronger than the published one and connects to the
    literature the paper already cites (Powell 1991: relative-gains sensitivity
    is endogenous to asymmetry, so parity is where the mechanism is definitionally
    inert). It should replace the README row."""
    # 9 states x 12 families over 7 values of k. The same contrast at the v2
    # default (15 states, 30 families, 9 values of k) gives uniform 2/2 against
    # zipf 3/7 and takes ~57s; this gives uniform 2/2 against zipf 3/5 in ~5s.
    # The qualitative finding — inert under parity, finer under scarcity — is
    # identical, and a reproducibility check nobody runs because it is slow is
    # not a reproducibility check.
    KS = (0, 1, 2, 3, 4, 6, 9)

    def levels(n_variants: int, endowment: str) -> int:
        caps = set()
        for k in KS:
            r = run_trial(TrialConfig(
                institution="free_trade", quarantine=QuarantineLevel.NONE, seed=0,
                rounds=2, tasks_per_round=2, k_trials=1, n_states=9,
                n_variants=n_variants, endowment=endowment, great_power_weight=8,
                export_policy="relative_gains", relative_gains_sensitivity=k))
            caps.add(round(r["mean_capability"], 4))
        return len(caps)

    out = {
        "k_levels_3_families_uniform": levels(1, "uniform"),
        "k_levels_12_families_uniform": levels(4, "uniform"),
        "k_levels_3_families_zipf": levels(1, "zipf"),
        "k_levels_12_families_zipf": levels(4, "zipf"),
    }
    out["dial_is_inert_under_parity"] = (out["k_levels_3_families_uniform"] <= 2
                                         and out["k_levels_12_families_uniform"] <= 2)
    out["scarcity_sets_resolution_not_existence"] = (
        out["k_levels_3_families_zipf"] > 2
        and out["k_levels_12_families_zipf"] > out["k_levels_3_families_zipf"])

    # the institution dial at 3 families, against 'every arrangement returns
    # identical capability'
    for inst in ("autarky", "free_trade", "clubs"):
        r = run_trial(TrialConfig(institution=inst, quarantine=QuarantineLevel.NONE,
                                  seed=0, rounds=3, tasks_per_round=3, k_trials=1,
                                  n_states=3, n_variants=1))
        out[f"{inst}_capability_at_3_families"] = round(r["mean_capability"], 4)
    out["institutions_identical_at_3_families"] = len({
        out["autarky_capability_at_3_families"],
        out["free_trade_capability_at_3_families"],
        out["clubs_capability_at_3_families"]}) == 1
    return out


def claim_monoculture_metric() -> dict:
    """The scripted null model emits ONE playbook text for every skill, so it is
    at full monoculture by construction and the metric must say so. It used to
    report one distinct body per skill slot, which is the inverse."""
    r = run_trial(TrialConfig(institution="free_trade", quarantine=QuarantineLevel.NONE,
                              seed=0, rounds=2, tasks_per_round=2, k_trials=1,
                              n_states=6, n_variants=3))
    lex = run_trial(TrialConfig(institution="free_trade", quarantine=QuarantineLevel.NONE,
                                seed=0, rounds=2, tasks_per_round=1, k_trials=1,
                                n_states=3, n_variants=3, archetypes=("lexicon",),
                                seed_references=True))
    return {
        "scripted_distinct_bodies": r["distinct_bodies"],
        "scripted_library_similarity": round(r["library_similarity"], 4),
        "lexicon_distinct_bodies": lex["distinct_bodies"],
        "lexicon_n_families": lex["n_families"],
    }


def claim_design_floor() -> dict:
    """The exact-permutation p-floor imposed by seed count, before any data."""
    return {f"min_p_at_{n}_seeds_per_arm": round(min_achievable_p(n, n), 4)
            for n in (3, 4, 5, 8)}


def _caps(pattern: str) -> list[float]:
    return [json.loads(p.read_text())["mean_capability"]
            for p in sorted(RUNS.glob(pattern))]


def claim_live_statistics() -> dict:
    """Deterministic statistics over the committed live artifacts. The runs are
    not re-executed; the arithmetic over them is pinned."""
    out = {}
    for tag, a_pat, f_pat in (("saturated", "h1/autarky_s*.json", "h1/free_trade_s*.json"),
                              ("load_bearing", "lex/autarky_none_s*.json",
                               "lex/free_trade_none_s*.json")):
        a, f = _caps(a_pat), _caps(f_pat)
        if not a or not f:
            continue
        ba, bf = bootstrap_ci(a), bootstrap_ci(f)
        perm = permutation_test(a, f)
        out[f"{tag}_autarky_mean"] = ba["mean"]
        out[f"{tag}_free_trade_mean"] = bf["mean"]
        out[f"{tag}_difference"] = round(bf["mean"] - ba["mean"], 4)
        out[f"{tag}_p_exact"] = perm["p"]
        out[f"{tag}_seeds_per_arm"] = len(a)
    lift = json.loads((RUNS / "skill_lift_live.json").read_text())
    for row in lift:
        p = proportion(round(row["no_skill"] * 6), 6)
        out[f"lift_{row['family']}_floor_ci_width"] = p["ci_width"]
    return out


CLAIMS = {
    "v1_grid": claim_v1_grid,
    "parity_and_scarcity": claim_parity_and_scarcity,
    "monoculture_metric": claim_monoculture_metric,
    "design_floor": claim_design_floor,
    "live_statistics": claim_live_statistics,
}


# -- live provenance is checked, not reproduced ------------------------------

def audit_live_artifacts() -> list[str]:
    """Live results cannot be re-run here, so the standard they are held to is
    that they SAY what produced them. Anything missing a provenance block is
    reported — including the artifacts committed before provenance existed,
    which is most of them and which is the honest finding."""
    problems = []
    for path in sorted(list(RUNS.glob("h1/*.json")) + list(RUNS.glob("lex/*.json"))):
        if "transcripts" in path.name:
            continue
        d = json.loads(path.read_text())
        prov = d.get("provenance")
        rel = path.relative_to(ROOT)
        if not prov:
            problems.append(f"{rel}: no provenance block — model, date and commit unknown")
            continue
        if not prov.get("model", {}).get("model_id_requested"):
            problems.append(f"{rel}: provenance records no model identifier")
        if prov.get("model", {}).get("errors"):
            problems.append(f"{rel}: {prov['model']['errors']} transport failures — "
                            f"capability is a lower bound")
    return problems


# -- driver ------------------------------------------------------------------

def compute() -> dict:
    return {name: fn() for name, fn in CLAIMS.items()}


def _diff(expected: dict, actual: dict) -> list[str]:
    out = []
    for group, exp in expected.items():
        act = actual.get(group)
        if act is None:
            out.append(f"{group}: missing from this run")
            continue
        for key, want in exp.items():
            got = act.get(key)
            if got is None:
                out.append(f"{group}.{key}: missing (expected {want})")
            elif isinstance(want, (int, float)) and isinstance(got, (int, float)):
                if abs(float(got) - float(want)) > TOL:
                    out.append(f"{group}.{key}: expected {want}, got {got}")
            elif got != want:
                out.append(f"{group}.{key}: expected {want!r}, got {got!r}")
    for group in actual:
        if group not in expected:
            out.append(f"{group}: new claim group, not in the manifest — run --update")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if any number drifted from the manifest")
    ap.add_argument("--update", action="store_true",
                    help="re-lock the manifest to the values produced now")
    args = ap.parse_args()

    actual = compute()

    for group, values in actual.items():
        print(f"\n{group}")
        for k, v in values.items():
            print(f"  {k:<44} {v}")

    print("\nlive artifacts (not re-run — audited for provenance)")
    problems = audit_live_artifacts()
    if problems:
        for p in problems:
            print(f"  ! {p}")
    else:
        print("  all live artifacts carry a provenance block")

    if args.update:
        MANIFEST.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n")
        print(f"\nlocked {MANIFEST.relative_to(ROOT)}")
        return 0

    if args.check:
        if not MANIFEST.exists():
            print("\nno manifest — run `python -m paper.reproduce --update` first")
            return 1
        drift = _diff(json.loads(MANIFEST.read_text()), actual)
        if drift:
            print(f"\nFAIL — {len(drift)} value(s) drifted from the manifest:")
            for d in drift:
                print(f"  ! {d}")
            return 1
        print("\nOK — every deterministic number matches the manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
