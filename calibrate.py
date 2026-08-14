"""Skill lift: does the doctrine do any work at all?

The precondition nobody checked
-------------------------------
An exchange institution can only redistribute capability the agents do not
already have. If a task family is solvable cold, then every agent scores the
same however you wire the population, and the institutional comparison is a
comparison between two ways of reaching the same saturated number.

The live H1 run showed this is not a hypothetical worry: agents finished with
empty libraries and still scored 0.89-1.00 (runs/h1/). So this script measures,
per family, the one quantity that decides whether the family is usable at all:

    skill lift = P(solve | doctrine installed) - P(solve | empty library)

  lift ~ 0 with a high floor  -> SATURATED: the model solves it cold. The family
                                 cannot support an institutional experiment.
  lift ~ 0 with a low floor   -> INERT: the doctrine does not help either. The
                                 task is beyond the model, or the doctrine is bad.
  lift large                  -> LOAD-BEARING: capability genuinely depends on
                                 holding the artifact. Usable.

Report skill lift for every family before running anything institutional. It is
cheap, it is a one-line table, and it is the difference between measuring an
institution and measuring nothing.

    python calibrate.py                 # scripted null model (free, deterministic)
    python calibrate.py --live -n 8     # against a real model
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from skill_diplomacy.bank.base import verify
from skill_diplomacy.bank.variants import make_bank
from skill_diplomacy.harness.budget import BudgetMeter
from skill_diplomacy.harness.events import EventLog
from skill_diplomacy.harness.model import ScriptedModel
from skill_diplomacy.experiment.oracle import make_oracle
from skill_diplomacy.state import AgentState, _family_skill

SATURATED, INERT, LOAD_BEARING = "SATURATED", "INERT", "LOAD-BEARING"


def classify(floor: float, lift: float) -> str:
    if floor >= 0.8:
        return SATURATED
    if lift < 0.2:
        return INERT
    return LOAD_BEARING


def _reference_for(gen) -> str | None:
    """The doctrine body a specialist in this family would hold. Generators that
    carry information expose `reference_body()`; the rest get a generic strategy
    playbook, which is exactly the point being tested."""
    inner = getattr(gen, "inner", gen)
    if hasattr(inner, "reference_body"):
        return inner.reference_body()
    return ("Strategy: decompose, compute exactly, answer in the required format.\n"
            "1. Parse all given rules/values.\n"
            "2. Compute stepwise with exact arithmetic.\n"
            "3. Emit `ANSWER:` in the exact requested format.")


def measure(gen, family: str, model, n: int, seed: int, with_skill: bool) -> float:
    """Pass rate over n fresh instances, with or without the doctrine installed."""
    work = Path(tempfile.mkdtemp(prefix="cal_"))
    try:
        st = AgentState.create("A", [family], work,
                               BudgetMeter(10_000_000, 1_000_000),
                               EventLog(work / "events.jsonl"))
        if with_skill:
            body = _reference_for(gen)
            if body:
                st.library.add_skill(_family_skill(family),
                                     f"Doctrine for {family} tasks.", body)
        ok = 0
        for task in gen.batch(seed=seed, n=n):
            try:
                ok += 1 if st.attempt(model, task) else 0
            except Exception:
                pass
        return ok / n if n else 0.0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("-n", "--tasks", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20260807)
    ap.add_argument("--variants", type=int, default=1)
    ap.add_argument("--lexicon", action="store_true",
                    help="include the lexicon archetype (information-carrying)")
    ap.add_argument("--outdir", type=Path, default=Path("runs"))
    args = ap.parse_args()

    if args.live:
        from skill_diplomacy.harness.cli_model import CLIModel
        model = CLIModel(model_id=args.model)
    else:
        model = ScriptedModel(make_oracle({}))

    bank = make_bank(args.variants, include_lexicon=args.lexicon)
    print(f"skill lift  |  live={args.live}  n={args.tasks} tasks/family  "
          f"families={len(bank)}\n")
    print(f"{'family':18} {'no skill':>9} {'with skill':>11} {'lift':>7}   verdict")
    print("-" * 62)

    rows = []
    for family, gen in bank.items():
        floor = measure(gen, family, model, args.tasks, args.seed, with_skill=False)
        ceil = measure(gen, family, model, args.tasks, args.seed, with_skill=True)
        lift = ceil - floor
        verdict = classify(floor, lift)
        rows.append({"family": family, "no_skill": round(floor, 3),
                     "with_skill": round(ceil, 3), "lift": round(lift, 3),
                     "verdict": verdict})
        print(f"{family:18} {floor:9.2f} {ceil:11.2f} {lift:+7.2f}   {verdict}")

    usable = [r for r in rows if r["verdict"] == LOAD_BEARING]
    print(f"\n{len(usable)}/{len(rows)} families are load-bearing.")
    if not usable:
        print("No family supports an institutional experiment: every doctrine is\n"
              "either unnecessary or useless. Fix the task bank before running\n"
              "any institution/quarantine comparison.")

    args.outdir.mkdir(parents=True, exist_ok=True)
    out = args.outdir / ("skill_lift_live.json" if args.live else "skill_lift.json")
    out.write_text(json.dumps(rows, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
