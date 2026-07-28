"""AgentState: one 'state' — a scaffold-only self-improving agent.

The improvement loop (spec §3, survey §6.4 pattern): attempt → on failure,
propose a skill edit → gate → commit. Committed instances join the regression
store (ACTIR's 'never again' suite: solved tasks may never silently regress).

The model is deliberately swappable (ScriptedModel in tests; Haiku-tier in
runs) — institutions and governance must not depend on model identity."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .bank.base import TaskInstance, verify
from .harness.budget import BudgetMeter
from .harness.events import EventLog
from .harness.model import ModelClient
from .skills.format import SkillLibrary

SYSTEM = (
    "You are the strategist of state {name}. Solve tasks exactly; the final "
    "line of your reply MUST be `ANSWER: <value>`. Use your skill library when "
    "relevant — it encodes your accumulated doctrine."
)


@dataclass
class AgentState:
    name: str
    home_family: str
    library: SkillLibrary
    budget: BudgetMeter
    log: EventLog
    regression_store: list[TaskInstance] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, home_family: str, workdir: str | Path,
               budget: BudgetMeter, log: EventLog) -> "AgentState":
        lib = SkillLibrary(Path(workdir) / name / "skills", owner=name)
        return cls(name, home_family, lib, budget, log)

    # -- task attempts -----------------------------------------------------
    def _prompt(self, task: TaskInstance) -> str:
        return f"{self.library.render_index()}\n\n# Task ({task.family})\n{task.prompt}"

    def attempt(self, model: ModelClient, task: TaskInstance, phase: str = "eval") -> bool:
        resp = model.complete(SYSTEM.format(name=self.name), self._prompt(task))
        self.budget.charge(resp.tokens_in, resp.tokens_out, rollouts=1,
                           kind="quarantine" if phase == "quarantine" else "task")
        success = verify(task, resp.text)
        self.log.append("attempt", state=self.name, task_id=task.id,
                        family=task.family, success=success, phase=phase,
                        budget_spent_tokens=self.budget.spent_tokens,
                        rollouts=self.budget.rollouts)
        if success and phase == "eval" and all(t.id != task.id for t in self.regression_store):
            self.regression_store.append(task)
        return success

    # -- self-improvement --------------------------------------------------
    def improve_from_failure(self, model: ModelClient, task: TaskInstance) -> str | None:
        """Ask the model to write/update a doctrine skill for this family.
        v0 gate: the edit must not shrink the library's regression pass-rate
        (checked by the caller via quarantine machinery re-used on self-edits)."""
        prompt = (
            f"You failed this {task.family} task:\n\n{task.prompt}\n\n"
            "Write a concise, reusable playbook (a 'doctrine') that would let you "
            "solve this WHOLE FAMILY of tasks reliably. Output only the playbook "
            "body in markdown, starting with a one-line strategy summary."
        )
        resp = model.complete(SYSTEM.format(name=self.name), prompt)
        self.budget.charge(resp.tokens_in, resp.tokens_out, rollouts=1, kind="improve")
        skill_name = f"{task.family.replace('_', '-')}-doctrine"
        self.library.add_skill(
            skill_name,
            f"Doctrine for {task.family} tasks (home shard of {self.name}).",
            resp.text.strip(),
        )
        self.log.append("skill_commit", state=self.name, skill=skill_name,
                        family=task.family, source="self",
                        content_hash=self.library.content_hash(skill_name))
        return skill_name
