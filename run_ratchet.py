"""Self-improvement is a ratchet, and without a gate it turns the wrong way.

    python run_ratchet.py            # -> runs/ratchet.json, no API key needed

The finding
-----------
An agent that already holds a correct procedure and *fails a task anyway* is in
a situation the self-improvement loop cannot read. The loop's trigger is
failure; its inference is "I lack a doctrine for this family"; its action is to
write one. But a competent agent's failure is often an execution slip, not a
knowledge gap — and the doctrine it then writes is worse than the one it
already had. Ungated, that edit is committed, the correct procedure is
overwritten, and every subsequent attempt fails, which triggers further
"improvement". Capability does not decay; it collapses and does not recover.

This is invisible to the rest of this repository, and necessarily so. With a
perfect solver a competent agent never fails at home, so `improve_from_failure`
never fires on an agent that already knows what it is doing, and the
pathological branch is unreachable. It becomes measurable only once execution
can fail — which is what `harness/fallible.py` and the `protocol` archetype are
for. Sweeping per-step reliability is the experiment.

Why it is not just a bug
------------------------
The gate is usually argued for on contamination grounds: screen what you import
because someone may have poisoned it. This is a different and more basic
argument, and it applies with no adversary anywhere in the system. Screening
your *own* edits is what makes self-improvement monotone. Without it, the
mechanism that is supposed to accumulate capability is the mechanism that
destroys it, and the more reliable the agent already is, the more it has to
lose.

The comparison also isolates the claim from the "screening is a tax" framing.
Here the gate does not trade capability for safety — it *buys* capability, from
an agent that would otherwise dismantle its own knowledge.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from skill_diplomacy.experiment.grid import TrialConfig, run_trial
from skill_diplomacy.experiment.oracle import make_oracle
from skill_diplomacy.harness.fallible import FallibleModel
from skill_diplomacy.institutions.quarantine import QuarantineLevel as Q
from skill_diplomacy.metrics.stats import bootstrap_ci, compare

RELIABILITIES = (1.0, 0.995, 0.99, 0.98, 0.97, 0.95, 0.92, 0.90)


def arm(reliability: float, gated: bool, seeds: int, archetype: str,
        rounds: int, states: int, variants: int) -> dict:
    caps, finals, trajectories = [], [], []
    for s in range(seeds):
        cfg = TrialConfig(
            institution="autarky",
            # Autarky on purpose: no exchange, no adversary, no imports. Whatever
            # happens to capability here is done by the agent to itself.
            quarantine=Q.REGRESSION if gated else Q.NONE,
            gate_self_edits=gated,
            seed=s, rounds=rounds, tasks_per_round=3, k_trials=1,
            n_states=states, n_variants=variants, archetypes=(archetype,),
            seed_references=True, endowment="uniform")
        model = FallibleModel(make_oracle(lambda st, f: False),
                              reliability=reliability, seed=s)
        r = run_trial(cfg, model=model)
        caps.append(r["mean_capability"])
        per_state = r["states"]
        trajectories.append([per_state[n]["capability_by_round"] for n in sorted(per_state)])
        finals.append(r["mean_capability"])
    b = bootstrap_ci(caps)
    # Did the population end below where it started? The endowment guarantees
    # each state can answer its home family at t=0, so round 0 is the baseline
    # the agent was handed and anything below it is self-inflicted.
    first = [t[i][0] for t in trajectories for i in range(len(t))]
    last = [t[i][-1] for t in trajectories for i in range(len(t))]
    declined = sum(1 for a, b_ in zip(first, last) if b_ < a - 1e-9)
    return {"reliability": reliability, "gated": gated, "seeds": seeds,
            "mean_capability": round(b["mean"], 4),
            "ci": [b["ci_low"], b["ci_high"]], "sd": b["sd"],
            "capabilities": [round(c, 4) for c in caps],
            "state_rounds": len(first),
            "states_that_declined": declined,
            "decline_rate": round(declined / len(first), 4) if first else 0.0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=8,
                    help="8 per arm; an exact permutation contrast then has a "
                         "two-sided floor of 0.0002 and can actually resolve")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--states", type=int, default=3)
    ap.add_argument("--variants", type=int, default=3)
    ap.add_argument("--archetype", default="protocol",
                    choices=["protocol", "lexicon"])
    ap.add_argument("--outdir", type=Path, default=Path("runs"))
    args = ap.parse_args()

    rows = []
    print(f"autarky | {args.states} states x {args.variants} {args.archetype} families | "
          f"{args.rounds} rounds | {args.seeds} seeds\n")
    print(f"{'reliability':>11}  {'ungated':>21}  {'gated':>21}  {'gate buys':>10}")
    print("-" * 70)
    for r in RELIABILITIES:
        un = arm(r, False, args.seeds, args.archetype, args.rounds, args.states, args.variants)
        ga = arm(r, True, args.seeds, args.archetype, args.rounds, args.states, args.variants)
        rows += [un, ga]
        delta = ga["mean_capability"] - un["mean_capability"]
        print(f"{r:>11.3f}  {un['mean_capability']:>7.3f} "
              f"[{un['ci'][0]:.2f},{un['ci'][1]:.2f}] "
              f"{un['decline_rate']*100:>3.0f}% dn  "
              f"{ga['mean_capability']:>7.3f} "
              f"[{ga['ci'][0]:.2f},{ga['ci'][1]:.2f}] "
              f"{ga['decline_rate']*100:>3.0f}% dn  {delta:>+10.3f}")

    # The headline contrast, at the reliability where the effect is largest.
    best = max(RELIABILITIES,
               key=lambda r: (_get(rows, r, True)["mean_capability"]
                              - _get(rows, r, False)["mean_capability"]))
    c = compare(_get(rows, best, False)["capabilities"],
                _get(rows, best, True)["capabilities"], "ungated", "gated")
    print(f"\nlargest gap at reliability={best}:")
    print(f"  ungated {c['ungated']['mean']:.3f} [{c['ungated']['ci_low']:.3f}, "
          f"{c['ungated']['ci_high']:.3f}]")
    print(f"  gated   {c['gated']['mean']:.3f} [{c['gated']['ci_low']:.3f}, "
          f"{c['gated']['ci_high']:.3f}]")
    print(f"  difference {-c['difference']:+.3f}   p = {c['p']:.4f} ({c['p_method']})"
          f"   design floor {c['min_p']:.4f}")
    if not c["design_can_reach_significance"]:
        print(f"  ! {args.seeds} seeds per arm cannot reach p<0.05 — raise --seeds")

    args.outdir.mkdir(parents=True, exist_ok=True)
    out = args.outdir / "ratchet.json"
    out.write_text(json.dumps({"archetype": args.archetype, "rows": rows,
                               "headline_reliability": best}, indent=2))
    print(f"\nWrote {out}")


def _get(rows: list[dict], reliability: float, gated: bool) -> dict:
    return next(r for r in rows
                if r["reliability"] == reliability and r["gated"] is gated)


if __name__ == "__main__":
    main()
