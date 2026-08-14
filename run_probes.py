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


def arm(q, fresh, seeds, states, variants, probes):
    adopted = offered = 0
    overhead, caps = [], []
    for s in range(seeds):
        r = run_trial(TrialConfig(
            institution="adversarial_trade", quarantine=q, seed=s,
            rounds=3, tasks_per_round=2, k_trials=1,
            n_states=states, n_variants=variants, archetypes=("lexicon",),
            seed_references=True, endowment="uniform",
            n_probes=probes, fresh_probes=fresh))
        p = r["poison_spread"]
        adopted += p["adopted"]; offered += p["offered"]
        overhead.append(r["governance_overhead"]); caps.append(r["mean_capability"])
    return {"quarantine": q.value, "probes": "fresh" if fresh else "fixed",
            "adopted": adopted, "offered": offered,
            "admitted_rate": round(adopted / offered, 4) if offered else 0.0,
            "governance_overhead": round(st.mean(overhead), 4),
            "mean_capability": round(st.mean(caps), 4), "seeds": seeds}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=5)
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
    print(f"{'quarantine':24} {'probes':7} {'admitted':>10} {'overhead':>9}")
    print("-" * 54)
    for r in rows:
        print(f"{r['quarantine']:24} {r['probes']:7} "
              f"{r['adopted']:>4}/{r['offered']:<5} {r['governance_overhead']:>9.3f}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "probe_coverage.json").write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {args.outdir / 'probe_coverage.json'}")


if __name__ == "__main__":
    main()
