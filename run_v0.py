"""Smoke run: 2 states, autarky vs free trade, ScriptedModel (no API spend).

Demonstrates the full pipeline: generators → attempts → self-improvement →
exchange under an institution → quarantine → metrics folded from the event
log. Swap ScriptedModel for AnthropicModel to run it live.

    python run_v0.py
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from skill_diplomacy.bank.base import extract_answer, shard_families, verify
from skill_diplomacy.bank.generators.calendar_math import CalendarMathGenerator
from skill_diplomacy.bank.generators.modmath import ModMathGenerator
from skill_diplomacy.bank.generators.unit_chain import UnitChainGenerator
from skill_diplomacy.harness.budget import BudgetExceeded, BudgetMeter
from skill_diplomacy.harness.events import EventLog
from skill_diplomacy.harness.model import ScriptedModel
from skill_diplomacy.institutions.institutions import Autarky, FreeTrade
from skill_diplomacy.institutions.quarantine import QuarantineLevel, run_quarantine
from skill_diplomacy.metrics.metrics import (adoption_edges, gini, pass_k,
                                             pass_rate_trajectory, trials_by_task)
from skill_diplomacy.state import AgentState

GENS = {g.family: g for g in [UnitChainGenerator(), CalendarMathGenerator(), ModMathGenerator()]}


def oracle_policy(system: str, prompt: str) -> str:
    """Scripted stand-in with a knowledge gradient: solves the task if the
    prompt's family matches a skill mentioned in the library index (i.e. after
    'learning'), or with the home-shard advantage; otherwise fails. Home-shard
    detection is crude on purpose — this is plumbing verification, not science."""
    import datetime as dt
    import re

    if "# Task (unit_chain)" in prompt:
        if "unit-chain-doctrine" in prompt:
            qty = int(re.search(r"in (\d+) ", prompt).group(1))
            factors = [int(m) for m in re.findall(r"= (\d+) ", prompt)]
            v = qty
            for f in factors:
                v *= f
            return f"Chain product.\nANSWER: {v}"
        return "Not sure.\nANSWER: 0"
    if "# Task (calendar_math)" in prompt:
        if "calendar-math-doctrine" in prompt:
            m = re.search(r"(\d+) days (after|before) (\d{4}-\d{2}-\d{2})", prompt)
            days, direction, start = int(m.group(1)), m.group(2), m.group(3)
            d0 = dt.date.fromisoformat(start)
            target = d0 + dt.timedelta(days=days if direction == "after" else -days)
            ans = target.strftime("%A") if "day of the week" in prompt else target.isoformat()
            return f"Calendar walk.\nANSWER: {ans}"
        return "Not sure.\nANSWER: 1900-01-01"
    if "# Task (modmath)" in prompt:
        m = re.search(r"Compute (\d+)\^(\d+) mod (\d+)", prompt)
        if m and ("modmath-doctrine" in prompt):
            return f"Fast exponentiation.\nANSWER: {pow(int(m.group(1)), int(m.group(2)), int(m.group(3)))}"
        return "Not sure.\nANSWER: 0"
    # improvement request → return a playbook
    return ("Strategy: decompose, compute exactly, answer in required format.\n"
            "1. Parse all given rules/values.\n2. Compute stepwise with exact arithmetic.\n"
            "3. Emit `ANSWER:` in the exact requested format.")


def run(institution_cls, label: str, rounds: int = 3, tasks_per_round: int = 4) -> dict:
    workdir = Path(tempfile.mkdtemp(prefix=f"sd_{label}_"))
    log = EventLog(workdir / "events.jsonl")
    names = ["STATE_A", "STATE_B"]
    shards = shard_families(names, ["unit_chain", "calendar_math"])
    inst = institution_cls(states=names) if institution_cls is not Autarky else Autarky(states=names)
    model = ScriptedModel(oracle_policy)
    states = {n: AgentState.create(n, shards[n], workdir, BudgetMeter(200_000, 400), log)
              for n in names}

    for rnd in range(rounds):
        for name, st in states.items():
            # eval on a mixed diet: home + off-shard
            for fam in ["unit_chain", "calendar_math"]:
                for task in GENS[fam].batch(seed=1000 * rnd + hash(name) % 97, n=tasks_per_round):
                    try:
                        ok = st.attempt(model, task)
                    except BudgetExceeded:
                        break
                    if not ok and fam == st.home_family:
                        st.improve_from_failure(model, task)
        # exchange phase
        for name, st in states.items():
            for exporter in inst.visible(name):
                for skill in states[exporter].library.skill_names():
                    if skill in st.library.skill_names():
                        continue
                    artifact = states[exporter].library.export_skill(skill)
                    probes = GENS[st.home_family].batch(seed=7000 + rnd, n=2)
                    report = run_quarantine(
                        QuarantineLevel.REGRESSION, st.regression_store[:3], probes,
                        evaluate=lambda t: st.attempt(model, t, phase="quarantine"))
                    if report.accepted:
                        st.library.import_skill(artifact, exporter)
                    log.append("adoption_decision", state=name, exporter=exporter,
                               skill=skill, accepted=report.accepted,
                               level=report.level, poisoned=artifact.get("_poisoned", False))

    events = log.read()
    summary = {"institution": label}
    for n, st in states.items():
        traj = pass_rate_trajectory(events, n)
        summary[n] = {"final_pass_rate": round(traj[-1][1], 3) if traj else 0.0,
                      "budget": st.budget.snapshot(),
                      "library": st.library.skill_names(),
                      "pass^2": round(pass_k(trials_by_task(events, n), 2), 3)}
    summary["capability_gini"] = round(
        gini([summary[n]["final_pass_rate"] for n in names]), 3)
    summary["adoptions"] = adoption_edges(events)
    shutil.rmtree(workdir, ignore_errors=True)
    return summary


if __name__ == "__main__":
    import json
    for cls, label in [(Autarky, "autarky"), (FreeTrade, "free_trade")]:
        print(json.dumps(run(cls, label), indent=2))
