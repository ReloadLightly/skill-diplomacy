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
from .institutions.quarantine import QuarantineLevel, run_quarantine
from .skills.format import SkillLibrary

SYSTEM = (
    "You are the strategist of state {name}. Solve tasks exactly; the final "
    "line of your reply MUST be `ANSWER: <value>`. Use your skill library when "
    "relevant — it encodes your accumulated doctrine."
)


def _family_skill(family: str) -> str:
    return f"{family.replace('_', '-')}-doctrine"


@dataclass
class AgentState:
    name: str
    home_family: str            # primary shard (kept as a str for v0/v1 compat)
    library: SkillLibrary
    budget: BudgetMeter
    log: EventLog
    regression_store: list[TaskInstance] = field(default_factory=list)
    # sprint 2: content hashes of artifacts this state has already screened and
    # rejected. A denylist is both the realistic behaviour and the fix for the
    # overhead denominator (defect 3.2) — v1 re-screened the same rejected
    # artifact once per round, so 'governance overhead' included retry churn.
    rejected_hashes: set = field(default_factory=set)
    screened_hashes: set = field(default_factory=set)
    transcripts: list = field(default_factory=list)
    keep_transcripts: bool = False
    # sprint 2: a state may hold several home shards. Uniform endowments make
    # every state's library the same size at every decision point, so the
    # relative-gains balance is identically zero and the export dial degenerates
    # to a step. Capability asymmetry is the precondition for relative-gains
    # reasoning to have anything to bite on — so it is a parameter, not a
    # constant. `home_family` remains the primary shard for v0/v1 compatibility.
    home_families: list = field(default_factory=list)

    def is_home(self, family: str) -> bool:
        return family == self.home_family or family in self.home_families

    @classmethod
    def create(cls, name: str, home_family: str | list, workdir: str | Path,
               budget: BudgetMeter, log: EventLog,
               keep_transcripts: bool = False) -> "AgentState":
        homes = [home_family] if isinstance(home_family, str) else list(home_family)
        lib = SkillLibrary(Path(workdir) / name / "skills", owner=name)
        return cls(name, homes[0], lib, budget, log,
                   keep_transcripts=keep_transcripts, home_families=homes)

    # -- task attempts -----------------------------------------------------
    def _prompt(self, task: TaskInstance) -> str:
        """Progressive disclosure: the full index always, plus the FULL BODY of
        the doctrine for this task's family when one is installed.

        v1 injected names and descriptions only. That is invisible to the
        scripted oracle's name-matching rule but fatal for a live model: the
        doctrine text — the thing that is inherited, mutated and poisoned —
        never reached the context, so skills could not causally affect
        behaviour and poison could not act. Fixed here so the live path is
        meaningful, without changing what the scripted oracle sees."""
        parts = [self.library.render_index()]
        skill = _family_skill(task.family)
        if skill in self.library.skill_names():
            parts.append(self.library.render_full(skill))
        parts.append(f"# Task ({task.family})\n{task.prompt}")
        return "\n\n".join(parts)

    def attempt(self, model: ModelClient, task: TaskInstance, phase: str = "eval") -> bool:
        resp = model.complete(SYSTEM.format(name=self.name), self._prompt(task))
        kind = phase if phase.startswith("quarantine") else "task"
        self.budget.charge(resp.tokens_in, resp.tokens_out, rollouts=1, kind=kind)
        success = verify(task, resp.text)
        if self.keep_transcripts:
            self.transcripts.append({"state": self.name, "task_id": task.id,
                                     "family": task.family, "phase": phase,
                                     "prompt": self._prompt(task),
                                     "response": resp.text,
                                     "expected": task.answer, "success": success})
        self.log.append("attempt", state=self.name, task_id=task.id,
                        family=task.family, success=success, phase=phase,
                        budget_spent_tokens=self.budget.spent_tokens,
                        rollouts=self.budget.rollouts)
        if success and phase == "eval" and all(t.id != task.id for t in self.regression_store):
            self.regression_store.append(task)
        return success

    # -- self-improvement --------------------------------------------------
    def improve_from_failure(self, model: ModelClient, task: TaskInstance, *,
                             level: QuarantineLevel = QuarantineLevel.NONE,
                             probes: list[TaskInstance] | None = None,
                             regression_cap: int = 5,
                             mode: str = "replace") -> str | None:
        """Ask the model to write/update a doctrine skill, then GATE the edit.

        Sprint 2, defect 3.3. v1's docstring promised that 'the edit must not
        shrink the library's regression pass-rate (checked by the caller)' and
        no caller ever checked. Imported skills faced quarantine; self-authored
        ones were committed unconditionally — an asymmetry that is precisely
        what a reviewer asks about, and that made 'the price of governance'
        an under-count.

        The gate is the SAME machinery imports face, so the comparison is
        apples-to-apples, and its cost is charged to a separate sub-account so
        governance can be reported as a two-term decomposition. Returns the
        committed skill name, or None if the edit was rejected and rolled back.
        """
        skill_name = _family_skill(task.family)
        existing = (self.library.body(skill_name)
                    if skill_name in self.library.skill_names() else "")
        if mode == "revise" and existing:
            prompt = (
                f"You failed this {task.family} task:\n\n{task.prompt}\n\n"
                f"Your current doctrine for this family is:\n\n{existing}\n\n"
                "Revise it so it solves this task as well as everything it already "
                "handled. Output only the revised playbook body in markdown."
            )
        else:
            prompt = (
                f"You failed this {task.family} task:\n\n{task.prompt}\n\n"
                "Write a concise, reusable playbook (a 'doctrine') that would let you "
                "solve this WHOLE FAMILY of tasks reliably. Output only the playbook "
                "body in markdown, starting with a one-line strategy summary."
            )
        resp = model.complete(SYSTEM.format(name=self.name), prompt)
        self.budget.charge(resp.tokens_in, resp.tokens_out, rollouts=1, kind="improve")

        before = self.library.snapshot(skill_name)          # transactional edit
        # WHAT the edit does to the existing doctrine, which turns out to matter
        # more than whether it is screened. `replace` is what this harness always
        # did: the new text is written over the old, and the model was never
        # shown the old (see the prompt above), so the loop is a BLIND FULL-BODY
        # OVERWRITE triggered by a single failure. No deployed SKILL.md editing
        # loop works that way, and it is the operator, not the absence of a gate,
        # that destroys an endowed doctrine.
        new_body = resp.text.strip()
        if mode == "append" and existing:
            new_body = existing.rstrip() + "\n\n" + new_body
        self.library.add_skill(
            skill_name,
            f"Doctrine for {task.family} tasks (home shard of {self.name}).",
            new_body,
        )

        # A self-edit gate needs evidence. Instrumenting the sweep behind the
        # ratchet result showed the REGRESSION tier accepting 492 of 492
        # self-edits vacuously and none on the merits: an agent that has just
        # failed its home family often has an empty regression store, and an
        # empty suite passed unconditionally. Failing closed instead does not
        # fix it -- it rejects every edit, so the gate still never discriminates,
        # it just errs the other way. Both settings measure self-editing being
        # off or on rather than screened or unscreened.
        #
        # So when there is no history to regress against, escalate to the probes
        # the caller already supplied. Fresh instances of the family the edit
        # claims to serve are exactly the evidence a first-time author lacks,
        # and consulting them is what makes acceptance mean something.
        regression = self.regression_store[:regression_cap]
        effective = level
        if not regression and probes and level is QuarantineLevel.REGRESSION:
            effective = QuarantineLevel.REGRESSION_PLUS_PROBES
        report = run_quarantine(
            effective, regression, probes or [],
            evaluate=lambda t: self.attempt(model, t, phase="quarantine_self"),
            empty_suite_passes=False)

        if not report.accepted:
            self.library.restore(skill_name, before)
            self.log.append("self_edit_decision", state=self.name, skill=skill_name,
                            family=task.family, accepted=False, level=report.level,
                            regression_passed=report.regression_passed,
                            regression_total=report.regression_total,
                            probes_passed=report.probes_passed,
                            probes_total=report.probes_total)
            return None

        self.log.append("self_edit_decision", state=self.name, skill=skill_name,
                        family=task.family, accepted=True, level=report.level,
                        regression_passed=report.regression_passed,
                        regression_total=report.regression_total,
                        probes_passed=report.probes_passed,
                        probes_total=report.probes_total)
        self.log.append("skill_commit", state=self.name, skill=skill_name,
                        family=task.family, source="self",
                        content_hash=self.library.content_hash(skill_name))
        return skill_name
