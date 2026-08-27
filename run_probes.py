"""Probe coverage: does a held-out screen catch a TARGETED defect?

The lexicon poison corrupts exactly one row of an eight-row reference table. It
is therefore correct on most instances and wrong only on those touching the
corrupted glyph -- the contaminant class a home-shard regression suite cannot
see by construction, and the one a held-out suite is supposed to catch.

Running it exposed a second, sharper question. The probe suite was keyed only on
(trial seed, round), so ONE suite screened every adoption in a round: if that
small sample missed the corrupted glyph, every importer missed it simultaneously,
and once adopted the artifact was never re-examined. Whether probes are re-drawn
per screening event turns out to matter as much as whether they are held out at
all -- which is what `--fresh` measures here.

    python run_probes.py            # both regimes, 5 seeds, no API spend
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

from skill_diplomacy.experiment.grid import TrialConfig, run_trial
from skill_diplomacy.institutions.quarantine import QuarantineLevel as Q
from skill_diplomacy.metrics.stats import bootstrap_ci, compare, fmt, proportion


def arm(q, fresh, seeds, states, variants, probes):
    """One cell of the comparison, reported with its uncertainty.

    Two intervals, because there are two units of analysis and they answer
    different questions. The pooled Wilson interval treats every poison offer as
    a trial and bounds the admitted RATE. The bootstrap over per-seed rates
    treats the seed as the replicate — which is the correct unit, since offers
    within a seed share a population, a task draw and a probe suite, and are not
    independent. Reporting only the pooled figure, as this script previously did,
    overstates precision by ignoring that clustering."""
    adopted = offered = 0
    overhead, caps, per_seed = [], [], []
    for s_ in range(seeds):
        r = run_trial(TrialConfig(
            institution="adversarial_trade", quarantine=q, seed=s_,
            rounds=3, tasks_per_round=2, k_trials=1,
            n_states=states, n_variants=variants, archetypes=("lexicon",),
            seed_references=True, endowment="uniform",
            n_probes=probes, fresh_probes=fresh))
        p = r["poison_spread"]
        adopted += p["adopted"]; offered += p["offered"]
        if p["offered"]:
            per_seed.append(p["adopted"] / p["offered"])
        overhead.append(r["governance_overhead"]); caps.append(r["mean_capability"])
    pooled = proportion(adopted, offered) if offered else {"ci_low": 0.0, "ci_high": 0.0}
    clustered = bootstrap_ci(per_seed) if per_seed else {"ci_low": 0.0, "ci_high": 0.0}
    return {"quarantine": q.value, "probes": "fresh" if fresh else "fixed",
            "adopted": adopted, "offered": offered,
            "admitted_rate": round(adopted / offered, 4) if offered else 0.0,
            "admitted_ci_pooled": [pooled["ci_low"], pooled["ci_high"]],
            "admitted_ci_by_seed": [clustered["ci_low"], clustered["ci_high"]],
            "admitted_by_seed": [round(v, 4) for v in per_seed],
            "governance_overhead": round(st.mean(overhead), 4),
            "overhead_ci": [bootstrap_ci(overhead)["ci_low"],
                            bootstrap_ci(overhead)["ci_high"]],
            "mean_capability": round(st.mean(caps), 4), "seeds": seeds}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # 5 was the published default. An exact permutation contrast between two
    # arms at 5 seeds each has a two-sided floor of 0.0079, which clears 0.05;
    # at 3 it is 0.10 and cannot. This is deterministic and costs seconds, so
    # there is no reason to run it underpowered.
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--states", type=int, default=6)
    ap.add_argument("--variants", type=int, default=6)
    ap.add_argument("--probes", type=int, default=6)
    ap.add_argument("--outdir", type=Path, default=Path("runs"))
    args = ap.parse_args()

    rows = [arm(q, fresh, args.seeds, args.states, args.variants, args.probes)
            for fresh in (False, True)
            for q in (Q.NONE, Q.REGRESSION, Q.REGRESSION_PLUS_PROBES)]

    print(f"adversarial trade | {args.states} states x {args.variants} load-bearing "
          f"families | {args.seeds} seeds | {args.probes} probes\n")
    print(f"{'quarantine':24} {'probes':7} {'admitted':>10} "
          f"{'95% CI (by seed)':>20} {'overhead':>9}")
    print("-" * 76)
    for r in rows:
        lo, hi = r["admitted_ci_by_seed"]
        print(f"{r['quarantine']:24} {r['probes']:7} "
              f"{r['adopted']:>4}/{r['offered']:<5} "
              f"{'[' + f'{lo:.2f}, {hi:.2f}' + ']':>20} "
              f"{r['governance_overhead']:>9.3f}")

    # The headline contrast this script exists to make: fixed vs re-drawn probes
    # at the only tier where probes run at all.
    fixed = next(r for r in rows if r["probes"] == "fixed"
                 and r["quarantine"] == Q.REGRESSION_PLUS_PROBES.value)
    fresh_ = next(r for r in rows if r["probes"] == "fresh"
                  and r["quarantine"] == Q.REGRESSION_PLUS_PROBES.value)
    c = compare(fixed["admitted_by_seed"], fresh_["admitted_by_seed"], "fixed", "fresh")
    print(f"\nfixed vs re-drawn probes, admitted rate per seed:")
    print(f"  fixed  {fmt(c['fixed'])}")
    print(f"  fresh  {fmt(c['fresh'])}")
    print(f"  difference {c['difference']:+.3f}   p = {c['p']:.4f} ({c['p_method']})")
    if not c["design_can_reach_significance"]:
        print(f"  ! {args.seeds} seeds per arm cannot reach p<0.05 "
              f"(exact floor {c['min_p']:.3f}) — raise --seeds")

    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "probe_coverage.json").write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {args.outdir / 'probe_coverage.json'}")


if __name__ == "__main__":
    main()
