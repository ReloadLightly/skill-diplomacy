"""How much should you check? — and why depth is the wrong dial.

    python run_sufficiency.py            # -> runs/sufficiency.json, no API key

The question in this repository's own title sentence never had a number attached.
It was posed as a trade-off and answered with a two-point contrast: regression
admits everything, probes admit less, probes cost more. That is a direction, not
an answer.

An answer needs the axis the question is actually a function of, which is not how
much you screen but **how rare the defect's symptoms are**. `protocol`'s
substitution poison makes that a dial: corrupting k entries of the table gives a
measured symptom rate d from 0.18 (one entry) to 0.99 (all of them). Sweeping d
against probe depth produces the result below, which was not what this script was
written to find.

The finding: the acceptance RULE dominates the screening DEPTH
--------------------------------------------------------------
A screen drawing k independent probes against a defect wrong on a fraction d of
instances should miss it with probability (1 - d)^k. That holds only if a single
failure is disqualifying. The tier's default rule was proportional — accept if
60% of probes pass — and under a proportional rule the arithmetic reverses.

As probes are added, the OBSERVED failure fraction concentrates on d. If d sits
below the rule's tolerance (here 1 - 0.6 = 0.4), concentration removes the lucky
rejections that a shallow screen gets by chance, and admission rises toward
certainty. Measured, at d = 0.178:

    probes            1      2      4      8     16
    proportional   0.87   0.77   0.85   0.98   1.00
    strict         0.87   0.77   0.60   0.33   0.10
    (1 - d)^k      0.82   0.68   0.46   0.21   0.04

Sixteen probes under the proportional rule admit **every** poisoned artifact,
having paid for sixteen evaluations out of the same budget the agent would have
spent improving. The strict rule at identical depth and identical cost admits
10%. Under the strict rule the measurement tracks the theory across the range;
under the proportional rule it inverts below the tolerance and is non-monotone
above it.

So a screening rule stated as a pass rate has a **blind band**: every defect
quieter than its tolerance is not merely hard to catch but becomes *more* certain
to be admitted the more you spend looking. Deeper screening is not a dial on
protection unless the rule is strict; under a proportional rule it is a dial on
variance, and the only defects it catches are the ones it would already have
caught at k = 1.

This is the same lesson as the fixed-versus-re-drawn result in `run_probes.py`
arriving from the other direction. There the screen's *sampling* decided what it
could see; here the screen's *decision rule* does. Neither is a question of how
much you check, which is what the literature and this repository were both
treating as the variable.

Everything here is deterministic and needs no API key.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from skill_diplomacy.bank.generators.protocol import (ProtocolGenerator,
                                                      poison_detectability)
from skill_diplomacy.experiment.grid import TrialConfig, run_trial
from skill_diplomacy.institutions.quarantine import QuarantineLevel as Q
from skill_diplomacy.metrics.stats import bootstrap_ci

# entry counts spanning the detectability range, measured in protocol.py
ENTRY_GRID = (1, 2, 3, 5, 8, 12, 24)
PROBE_GRID = (1, 2, 4, 8, 16)


def theoretical_admission(d: float, k: int) -> float:
    """(1 - d)^k — the probability k independent probes all miss the defect."""
    return (1.0 - d) ** k


def probes_needed(d: float, target: float = 0.10) -> float:
    """k* = ceil(log target / log(1 - d)). Infinite as d -> 0."""
    if d <= 0.0:
        return math.inf
    if d >= 1.0:
        return 1.0
    return math.ceil(math.log(target) / math.log(1.0 - d))


def arm(entries: int, probes: int, seeds: int, fresh: bool, states: int,
        variants: int, threshold: float) -> dict:
    adopted = offered = 0
    overheads, per_seed = [], []
    for s in range(seeds):
        r = run_trial(TrialConfig(
            institution="adversarial_trade", quarantine=Q.REGRESSION_PLUS_PROBES,
            seed=s, rounds=3, tasks_per_round=2, k_trials=1,
            n_states=states, n_variants=variants, archetypes=("protocol",),
            seed_references=True, endowment="uniform",
            n_probes=probes, fresh_probes=fresh,
            protocol_poison_mode="substitution",
            protocol_poison_entries=entries,
            probe_threshold=threshold))
        p = r["poison_spread"]
        adopted += p["adopted"]
        offered += p["offered"]
        if p["offered"]:
            per_seed.append(p["adopted"] / p["offered"])
        overheads.append(r["governance_overhead"])
    b = bootstrap_ci(per_seed) if per_seed else {"ci_low": 0.0, "ci_high": 0.0}
    return {"entries": entries, "probes": probes, "fresh": fresh,
            "threshold": threshold,
            "adopted": adopted, "offered": offered,
            "admitted_rate": round(adopted / offered, 4) if offered else 0.0,
            "admitted_ci": [b["ci_low"], b["ci_high"]],
            "admitted_by_seed": [round(v, 4) for v in per_seed],
            "governance_overhead": round(sum(overheads) / len(overheads), 4),
            "seeds": seeds}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--states", type=int, default=6)
    ap.add_argument("--variants", type=int, default=4)
    ap.add_argument("--record-len", type=int, default=4)
    ap.add_argument("--outdir", type=Path, default=Path("runs"))
    args = ap.parse_args()

    # ground truth for the x axis, measured rather than assumed
    gen = ProtocolGenerator(spec_seed=0, record_len=args.record_len)
    detect = {k: round(poison_detectability(gen, "substitution", 600, n_entries=k), 4)
              for k in ENTRY_GRID}

    print("defect detectability (share of instances a poisoned doctrine gets wrong)")
    for k, d in detect.items():
        star = probes_needed(d)
        print(f"  {k:>2} corrupted entries -> d = {d:.3f}   "
              f"probes for 10% admission: k* = {star:g}")

    rows = []
    for threshold, label in ((0.6, "proportional (>=60% of probes pass)"),
                             (1.0, "strict (any probe failure rejects)")):
        print(f"\nmeasured admission rate — {label}, "
              f"re-drawn probes, {args.seeds} seeds\n")
        header = "  d      " + "".join(f"{'k=' + str(k):>9}" for k in PROBE_GRID)
        print(header + "     theory (1-d)^k")
        print("-" * (len(header) + 22))
        for entries in ENTRY_GRID:
            d = detect[entries]
            cells = []
            for probes in PROBE_GRID:
                r = arm(entries, probes, args.seeds, True, args.states,
                        args.variants, threshold)
                rows.append({**r, "detectability": d,
                             "theoretical": round(theoretical_admission(d, probes), 4)})
                cells.append(f"{r['admitted_rate']:.2f}")
            theory = " ".join(f"{theoretical_admission(d, k):.2f}" for k in PROBE_GRID)
            print(f"  {d:.3f}  " + "".join(f"{c:>9}" for c in cells) + f"     {theory}")

    print("\nsufficiency — cheapest k reaching <=10% admission, and what it cost")
    print(f"  {'d':>6}  {'k* (theory)':>12}  {'k proportional':>15}"
          f"  {'k strict':>9}  {'overhead':>9}")
    print("  " + "-" * 60)
    sufficiency = []
    for entries in ENTRY_GRID:
        d = detect[entries]
        star = probes_needed(d)
        hits = {}
        for th in (0.6, 1.0):
            hits[th] = next((r for r in rows
                             if r["entries"] == entries and r["threshold"] == th
                             and r["admitted_rate"] <= 0.10), None)
        cap = ">" + str(max(PROBE_GRID))
        prop = str(hits[0.6]["probes"]) if hits[0.6] else cap
        strict = str(hits[1.0]["probes"]) if hits[1.0] else cap
        oh = f"{hits[1.0]['governance_overhead']:.3f}" if hits[1.0] else "-"
        sufficiency.append({
            "entries": entries, "detectability": d,
            "k_theory": None if star == math.inf else int(star),
            "k_proportional": hits[0.6]["probes"] if hits[0.6] else None,
            "k_strict": hits[1.0]["probes"] if hits[1.0] else None,
            "overhead_strict": hits[1.0]["governance_overhead"] if hits[1.0] else None})
        print(f"  {d:>6.3f}  {star:>12g}  {prop:>15}  {strict:>9}  {oh:>9}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    out = args.outdir / "sufficiency.json"
    out.write_text(json.dumps({"detectability": detect, "rows": rows,
                               "sufficiency": sufficiency,
                               "probe_grid": list(PROBE_GRID)}, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
