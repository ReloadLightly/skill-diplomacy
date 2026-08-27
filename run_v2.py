"""v2 runs: scaled population, variant task bank, strategic export policies.

v1 asked one question — what does governance cost? — on a three-state triangle
where every state saw every other in one hop and the whole family space was
three items. v2 adds the three things that were missing before any institutional
claim could be non-degenerate:

  * a task bank with enough families that capability is SCARCE (--variants);
  * an endowment distribution, so states are not all identical (--endowment);
  * an export decision, so an institution is more than a visibility mask
    (--export-policy, --k).

Typical invocations
-------------------
    python run_v2.py --sweep k            # relative-gains dial → curve + CSV
    python run_v2.py --sweep defectors    # free-rider sweep
    python run_v2.py --sweep institutions # v1 matrix at v2 scale
    python run_v2.py --sweep budget       # governance under a binding budget
    python run_v2.py --live --model claude-haiku-4-5 --states 6 --variants 3 \
                     --rounds 2 --seeds 1 --dump-transcripts

`--live` swaps the scripted oracle for a real model. The oracle is then bypassed
entirely and the poison acts as it is meant to: as text in a doctrine the model
actually reads, which is the only configuration in which the poison result means
anything about models rather than about our regexes.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import replace
from pathlib import Path

from skill_diplomacy.experiment.grid import TrialConfig, aggregate, run_trial
from skill_diplomacy.institutions.quarantine import QuarantineLevel

LEVELS = {
    "none": QuarantineLevel.NONE,
    "regression": QuarantineLevel.REGRESSION,
    "probes": QuarantineLevel.REGRESSION_PLUS_PROBES,
}


def _base(args) -> TrialConfig:
    return TrialConfig(
        institution=args.institution,
        quarantine=LEVELS[args.quarantine],
        seed=0,
        rounds=args.rounds,
        tasks_per_round=args.tasks,
        k_trials=args.k_trials,
        n_states=args.states,
        n_variants=args.variants,
        endowment=args.endowment,
        n_great_powers=args.great_powers,
        great_power_weight=args.weight,
        export_policy=args.export_policy,
        relative_gains_sensitivity=args.k,
        relative_gains_mode=args.mode,
        n_defectors=args.defectors,
        gate_self_edits=args.gate_self_edits,
        max_tokens=args.budget,
        max_rollouts=args.rollouts,
        dump_transcripts=args.dump_transcripts,
    )


def _model(args):
    if not args.live:
        return None
    from skill_diplomacy.harness.model import AnthropicModel
    return AnthropicModel(model_id=args.model)


def _run(base: TrialConfig, seeds, model, **over) -> list:
    return [run_trial(replace(base, seed=s, **over), model=model) for s in seeds]


def _fold(tag, trials) -> dict:
    n = len(trials)
    exports = {"requests": sum(t["exports"]["requests"] for t in trials),
               "refused": sum(t["exports"]["refused"] for t in trials)}
    return {
        "arm": tag,
        "seeds": n,
        "mean_capability": round(sum(t["mean_capability"] for t in trials) / n, 4),
        # Ability and affordability, reported separately. Attempts a state could
        # not pay for used to be scored as wrong answers and left in the
        # denominator, so under a binding budget `mean_capability` was silently
        # the product of the two -- and this sweep exists to study exactly the
        # budgets where that happens.
        "attempt_coverage": round(
            sum(t.get("attempt_coverage", 1.0) for t in trials) / n, 4),
        "budget_bound": any(t.get("budget_bound") for t in trials),
        "capability_gini": round(sum(t["capability_gini"] for t in trials) / n, 4),
        "governance_overhead": round(sum(t["governance_overhead"] for t in trials) / n, 4),
        "import_screen_overhead": round(sum(t["import_screen_overhead"] for t in trials) / n, 4),
        "self_screen_overhead": round(sum(t["self_screen_overhead"] for t in trials) / n, 4),
        "export_requests": exports["requests"],
        "export_refused": exports["refused"],
        "export_refusal_rate": round(exports["refused"] / exports["requests"], 4)
        if exports["requests"] else 0.0,
        "poison_offered": sum(t["poison_spread"]["offered"] for t in trials),
        "poison_adopted": sum(t["poison_spread"]["adopted"] for t in trials),
        "poison_transitive": sum(t["poison_spread"]["transitive_adopted"] for t in trials),
        "unique_screened": sum(t["unique_artifacts_screened"] for t in trials),
        "distinct_bodies": sum(t["distinct_bodies"] for t in trials),
    }


# --------------------------------------------------------------------------
# sweeps
# --------------------------------------------------------------------------

def sweep_k(base, seeds, model, args) -> list:
    """The headline v2 experiment: capability and inequality as functions of the
    relative-gains sensitivity k. A curve here is the thing v1 could not produce."""
    rows = []
    for k in range(args.k_min, args.k_max + 1):
        trials = _run(base, seeds, model, export_policy="relative_gains",
                      relative_gains_sensitivity=k)
        rows.append({**_fold(f"k={k}", trials), "k": k})
    return rows


def sweep_defectors(base, seeds, model, args) -> list:
    rows = []
    for d in args.defector_grid:
        if d > base.n_states:
            continue
        trials = _run(base, seeds, model, export_policy="open", n_defectors=d)
        row = _fold(f"defectors={d}", trials)
        names = list(trials[0]["states"])
        defs_ = names[len(names) - d:] if d else []
        coop = [n for n in names if n not in defs_]

        def mean(group):
            if not group:
                return None
            return round(sum(t["states"][n]["final_capability"]
                             for t in trials for n in group) / (len(trials) * len(group)), 4)

        rows.append({**row, "defectors": d,
                     "defector_capability": mean(defs_),
                     "cooperator_capability": mean(coop)})
    return rows


def sweep_institutions(base, seeds, model, args) -> list:
    out = []
    for inst in ["autarky", "free_trade", "clubs", "adversarial_trade"]:
        for lvl in [QuarantineLevel.NONE, QuarantineLevel.REGRESSION,
                    QuarantineLevel.REGRESSION_PLUS_PROBES]:
            out.extend(_run(base, seeds, model, institution=inst, quarantine=lvl))
    return aggregate(out)


def sweep_budget(base, seeds, model, args) -> list:
    """Governance is only a trade-off when the budget binds. With the default
    2M-token allowance every arm can afford every screen, so 'the price of
    governance' is a number nobody has to pay. Squeeze it until they do."""
    rows = []
    for b in args.budget_grid:
        for lvl in [QuarantineLevel.NONE, QuarantineLevel.REGRESSION_PLUS_PROBES]:
            trials = _run(base, seeds, model, max_tokens=b, quarantine=lvl)
            rows.append({**_fold(f"budget={b},{lvl.value}", trials),
                         "budget": b, "quarantine": lvl.value})
    return rows


SWEEPS = {"k": sweep_k, "defectors": sweep_defectors,
          "institutions": sweep_institutions, "budget": sweep_budget}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep", choices=sorted(SWEEPS), default="k")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--tasks", type=int, default=2, help="tasks per family per round")
    ap.add_argument("--k-trials", type=int, default=2, help="eval repeats (pass^k)")
    # population / bank
    ap.add_argument("--states", type=int, default=15)
    ap.add_argument("--variants", type=int, default=10, help="→ 3*variants families")
    ap.add_argument("--endowment", choices=["uniform", "step", "zipf"], default="zipf")
    ap.add_argument("--great-powers", type=int, default=0)
    ap.add_argument("--weight", type=int, default=8, help="top-rank endowment shares")
    # institution / policy
    ap.add_argument("--institution", default="free_trade")
    ap.add_argument("--quarantine", choices=sorted(LEVELS), default="none")
    ap.add_argument("--export-policy", default="open")
    ap.add_argument("--k", type=int, default=0, help="relative-gains sensitivity")
    ap.add_argument("--mode", choices=["return", "balance"], default="return")
    ap.add_argument("--defectors", type=int, default=0)
    ap.add_argument("--gate-self-edits", action="store_true")
    # sweep ranges
    ap.add_argument("--k-min", type=int, default=0)
    ap.add_argument("--k-max", type=int, default=12)
    ap.add_argument("--defector-grid", type=int, nargs="+",
                    default=[0, 3, 6, 9, 12])
    ap.add_argument("--budget-grid", type=int, nargs="+",
                    default=[40_000, 80_000, 160_000, 320_000, 2_000_000])
    # budget / live
    ap.add_argument("--budget", type=int, default=2_000_000)
    ap.add_argument("--rollouts", type=int, default=20_000)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--dump-transcripts", action="store_true")
    ap.add_argument("--outdir", type=Path, default=Path("runs"))
    args = ap.parse_args()
    if getattr(args, "gate_self_edits", False) and args.quarantine == "none":
        ap.error("--gate-self-edits needs a quarantine tier to gate WITH; "
                 "pass --quarantine regression or --quarantine probes. "
                 "With --quarantine none the flag would screen nothing.")


    base = _base(args)
    seeds = tuple(range(args.seeds))
    model = _model(args)

    print(f"sweep={args.sweep}  states={args.states}  families={3 * args.variants}  "
          f"endowment={args.endowment}  rounds={args.rounds}  seeds={args.seeds}  "
          f"live={args.live}\n", flush=True)

    rows = SWEEPS[args.sweep](base, seeds, model, args)

    keys = [k for k in rows[0] if isinstance(rows[0][k], (int, float, str)) or rows[0][k] is None]
    widths = {k: max(len(k), 10) for k in keys}
    print("  ".join(k.ljust(widths[k]) for k in keys))
    print("-" * (sum(widths.values()) + 2 * len(keys)))
    for r in rows:
        print("  ".join(str(r.get(k, "")).ljust(widths[k]) for k in keys))

    args.outdir.mkdir(parents=True, exist_ok=True)
    stem = args.outdir / f"v2_{args.sweep}"
    stem.with_suffix(".json").write_text(json.dumps(rows, indent=2))
    with stem.with_suffix(".csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    print(f"\nWrote {stem}.json and {stem}.csv")


if __name__ == "__main__":
    main()
