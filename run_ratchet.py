"""A blind overwrite destroys the doctrine it was meant to improve.

    python run_ratchet.py            # -> runs/ratchet.json, no API key needed

What this measures, and what it does not
----------------------------------------
An earlier version of this script reported that "screening your own edits is
where the capability comes from". That was wrong, and it was wrong in a way this
repository has a habit of being wrong: the gate under test never screened
anything. Instrumenting the sweep showed the REGRESSION tier accepting **492 of
492** self-edits vacuously — an agent that has just failed its home family
usually has an empty regression store, and `run_quarantine` passed an empty
suite unconditionally. So the reported "gated versus ungated" contrast was
self-editing being off versus on.

Fixing that (the self-edit gate now escalates to fresh probes when it has no
history, and refuses rather than waves through) does not rescue the original
claim. It replaces it with a narrower and better one.

The finding: the EDIT OPERATOR, not the gate
--------------------------------------------
An agent that holds a correct procedure and fails a task anyway is in a
situation the self-improvement loop cannot read. Its trigger is failure, its
inference is "I lack a doctrine for this family", and its action here was a
**blind full-body overwrite** of a doctrine the authoring agent is never shown —
`improve_from_failure` put only the failed task in the prompt, and `add_skill`
wrote the reply over whatever was there. One execution slip therefore erases an
endowed procedure outright, every later attempt fails, and that triggers further
"improvement".

Measured under autarky — no exchange, no adversary, no imports — at 98% per-step
reliability, 8 seeds, `protocol` families:

    edit operator   self-improve off   on, ungated   on, gated
    replace                    0.287         0.037       0.287
    append                     0.287         0.278       0.255

Three readings, in decreasing order of how much they should be trusted.

**The operator is what destroys capability.** Replacing costs 0.250 of the 0.287
an agent was endowed with — 87% of everything it had. Appending the new text
instead of discarding the old costs 0.009. Same failures, same loop, same
budget; the only difference is whether the prior doctrine survives the edit. No
deployed `SKILL.md` editing loop overwrites a skill without showing the model
the skill, which makes `replace` the unrealistic setting and its damage a
property of the harness's operator rather than of self-improvement.

**The gate adds nothing a disabled loop would not.** Under `replace` the gated
arm equals the never-improve arm exactly (0.287 vs 0.287, p = 1.0,
element-wise). Under `append` it is slightly worse than leaving the loop alone.
So this is not evidence that screening keeps good edits and rejects bad ones —
it is evidence that rejecting *every* edit beats this loop.

**And it cannot be evidence of that, by construction.** The scripted stand-in
answers every improvement request with one fixed playbook carrying no family
information, so P(beneficial self-edit) = 0 identically. `--mode revise`, which
shows the model its current doctrine and asks for a revision, returns exactly
the `replace` numbers for the same reason: the stand-in ignores the prompt.
Whether a gate can *discriminate* is a live-model question this harness cannot
answer.

The zero at reliability 1.0 is a consistency check rather than a control:
`improve_from_failure` is called zero times in every arm there, so the arms
execute identical code and no other outcome was available.
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
ARMS = (("off", False, False), ("ungated", True, False), ("gated", True, True))


def arm(reliability: float, improve: bool, gated: bool, mode: str, seeds: int,
        archetype: str, rounds: int, states: int, variants: int) -> dict:
    caps, first, last = [], [], []
    for s in range(seeds):
        cfg = TrialConfig(
            institution="autarky",
            quarantine=Q.REGRESSION if gated else Q.NONE,
            gate_self_edits=gated, self_improve=improve, self_edit_mode=mode,
            seed=s, rounds=rounds, tasks_per_round=3, k_trials=1,
            n_states=states, n_variants=variants, archetypes=(archetype,),
            seed_references=True, endowment="uniform")
        r = run_trial(cfg, model=FallibleModel(
            make_oracle(lambda st, f: False), reliability=reliability, seed=s))
        caps.append(r["mean_capability"])
        for n in sorted(r["states"]):
            traj = r["states"][n]["capability_by_round"]
            first.append(traj[0])
            last.append(traj[-1])
    b = bootstrap_ci(caps)
    declined = sum(1 for a, z in zip(first, last) if z < a - 1e-9)
    return {"reliability": reliability, "improve": improve, "gated": gated,
            "mode": mode, "seeds": seeds,
            "mean_capability": round(b["mean"], 4),
            "ci": [b["ci_low"], b["ci_high"]], "sd": b["sd"],
            "capabilities": [round(c, 4) for c in caps],
            "state_rounds": len(first),
            "decline_rate": round(declined / len(first), 4) if first else 0.0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--states", type=int, default=3)
    ap.add_argument("--variants", type=int, default=3)
    ap.add_argument("--archetype", default="protocol", choices=["protocol", "lexicon"])
    ap.add_argument("--modes", nargs="+", default=["replace", "append"],
                    choices=["replace", "append", "revise"])
    ap.add_argument("--outdir", type=Path, default=Path("runs"))
    args = ap.parse_args()

    rows = []
    print(f"autarky | {args.states} states x {args.variants} {args.archetype} "
          f"families | {args.rounds} rounds | {args.seeds} seeds\n")
    for mode in args.modes:
        print(f"edit operator = {mode}")
        print(f"{'reliability':>12}  {'improve off':>13}  {'on, ungated':>13}"
              f"  {'on, gated':>13}  {'operator cost':>14}")
        print("  " + "-" * 76)
        for r in RELIABILITIES:
            cells = {}
            for tag, improve, gated in ARMS:
                row = arm(r, improve, gated, mode, args.seeds, args.archetype,
                          args.rounds, args.states, args.variants)
                rows.append({**row, "arm": tag})
                cells[tag] = row
            cost = cells["ungated"]["mean_capability"] - cells["off"]["mean_capability"]
            print(f"{r:>12.3f}  {cells['off']['mean_capability']:>13.3f}"
                  f"  {cells['ungated']['mean_capability']:>13.3f}"
                  f"  {cells['gated']['mean_capability']:>13.3f}"
                  f"  {cost:>+14.3f}")
        print()

    # headline: the operator cost, at the reliability where it is largest
    get = lambda r, tag, m: next(x for x in rows if x["reliability"] == r
                                 and x["arm"] == tag and x["mode"] == m)
    worst = min(RELIABILITIES,
                key=lambda r: (get(r, "ungated", args.modes[0])["mean_capability"]
                               - get(r, "off", args.modes[0])["mean_capability"]))
    c = compare(get(worst, "ungated", args.modes[0])["capabilities"],
                get(worst, "off", args.modes[0])["capabilities"],
                "ungated", "improve_off")
    print(f"largest operator cost at reliability={worst} under '{args.modes[0]}':")
    print(f"  self-improvement off  {c['improve_off']['mean']:.3f} "
          f"[{c['improve_off']['ci_low']:.3f}, {c['improve_off']['ci_high']:.3f}]")
    print(f"  on, ungated           {c['ungated']['mean']:.3f} "
          f"[{c['ungated']['ci_low']:.3f}, {c['ungated']['ci_high']:.3f}]")
    print(f"  the loop costs {c['difference']:+.3f}   p = {c['p']:.4f} "
          f"({c['p_method']})   design floor {c['min_p']:.4f}")
    if len(args.modes) > 1:
        alt = args.modes[1]
        c2 = compare(get(worst, "ungated", alt)["capabilities"],
                     get(worst, "off", alt)["capabilities"], "ungated", "improve_off")
        print(f"  under '{alt}' the same loop costs {c2['difference']:+.3f} "
              f"(p = {c2['p']:.4f}) — the damage is the operator, not the loop")

    args.outdir.mkdir(parents=True, exist_ok=True)
    out = args.outdir / "ratchet.json"
    out.write_text(json.dumps({"archetype": args.archetype, "modes": args.modes,
                               "rows": rows, "headline_reliability": worst},
                              indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
