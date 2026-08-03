"""The v1 experiment grid: institution x quarantine-level x seed.

`run_trial` executes one fully-specified cell deterministically on the
ScriptedModel; `run_grid` sweeps the matrix; `aggregate` folds seeds into
mean/std per (institution, quarantine level). Everything downstream is a fold
over the per-trial event log, exactly as v0.

Setup (fixed, three unique family-experts so every institution is separable):

    state  home family      role
    -----  ---------------  -----------------------------
    A      unit_chain       designated poisoner (adversarial only)
    B      calendar_math
    C      modmath

Each state is evaluated on ALL families every round, but self-improves only on
its home family. Off-shard capability therefore comes ONLY through trade — which
is exactly what the institution gates. Autarky → each masters 1/3; free trade →
3/3; clubs → the club's union; adversarial trade → free-trade topology with A
publishing a poisoned unit_chain doctrine that only mixed-depth probes catch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import tempfile

from ..bank.base import shard_families
from ..bank.generators.calendar_math import CalendarMathGenerator
from ..bank.generators.modmath import ModMathGenerator
from ..bank.generators.unit_chain import UnitChainGenerator
from ..harness.budget import BudgetExceeded, BudgetMeter
from ..harness.events import EventLog
from ..harness.model import ScriptedModel
from ..institutions.institutions import (AdversarialTrade, Autarky, Clubs,
                                         FreeTrade, poison_artifact)
from ..institutions.quarantine import QuarantineLevel, run_quarantine
from ..metrics.metrics import (adoption_edges, gini, pass_k, poison_spread,
                               trials_by_task)
from ..state import AgentState
from .oracle import make_oracle

STATES = ["A", "B", "C"]
FAMILIES = ["unit_chain", "calendar_math", "modmath"]
GENS = {
    "unit_chain": UnitChainGenerator(),
    "calendar_math": CalendarMathGenerator(),
    "modmath": ModMathGenerator(),
}


def skill_family(skill_name: str) -> str:
    """`unit-chain-doctrine` -> `unit_chain` (inverse of state.py's naming)."""
    return skill_name.rsplit("-doctrine", 1)[0].replace("-", "_")


@dataclass
class TrialConfig:
    institution: str            # autarky | free_trade | clubs | adversarial_trade
    quarantine: QuarantineLevel
    seed: int
    rounds: int = 3
    tasks_per_round: int = 3
    k_trials: int = 3           # eval repeats per task → populates pass^k
    n_probes: int = 6           # fresh off-shard probes per adoption
    poisoner: str = "A"         # adversarial_trade only
    clubs: tuple = (("A", "B"), ("C",))
    max_tokens: int = 2_000_000  # generous: capability reflects institution, not starvation
    max_rollouts: int = 20_000


def _make_institution(cfg: TrialConfig):
    if cfg.institution == "autarky":
        return Autarky(states=list(STATES))
    if cfg.institution == "free_trade":
        return FreeTrade(states=list(STATES))
    if cfg.institution == "clubs":
        return Clubs(states=list(STATES), clubs=[list(c) for c in cfg.clubs])
    if cfg.institution == "adversarial_trade":
        return AdversarialTrade(states=list(STATES), poisoner=cfg.poisoner)
    raise ValueError(f"unknown institution: {cfg.institution}")


def _eval_seed(cfg: TrialConfig, rnd: int, name: str, fam: str) -> int:
    # stable index, NOT hash(name): Python salts str hashes per process, which
    # would make trials irreproducible across runs.
    return (cfg.seed * 1_000_003 + rnd * 9973 + STATES.index(name) * 31
            + FAMILIES.index(fam) * 7)


def run_trial(cfg: TrialConfig) -> dict:
    """Run one grid cell. Returns a JSON-serialisable summary dict."""
    workdir = Path(tempfile.mkdtemp(prefix=f"sd_{cfg.institution}_{cfg.quarantine.value}_"))
    try:
        return _run_trial_in(cfg, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _run_trial_in(cfg: TrialConfig, workdir: Path) -> dict:
    log = EventLog(workdir / "events.jsonl")
    shards = shard_families(list(STATES), list(FAMILIES))
    inst = _make_institution(cfg)

    # ground-truth poison registry, shared with the oracle (never seen by agents)
    registry: dict = {}
    model = ScriptedModel(make_oracle(registry))

    states = {
        n: AgentState.create(n, shards[n], workdir,
                             BudgetMeter(cfg.max_tokens, cfg.max_rollouts), log)
        for n in STATES
    }
    capability_by_round: dict = {n: [] for n in STATES}

    for rnd in range(cfg.rounds):
        # ---- eval + self-improve phase (all families, k trials each) --------
        for name, st in states.items():
            succ = tot = 0
            for fam in FAMILIES:
                for task in GENS[fam].batch(seed=_eval_seed(cfg, rnd, name, fam),
                                            n=cfg.tasks_per_round):
                    ok_any = False
                    for _ in range(cfg.k_trials):
                        try:
                            ok = st.attempt(model, task)
                        except BudgetExceeded:
                            ok = False
                        tot += 1
                        succ += 1 if ok else 0
                        ok_any = ok_any or ok
                    if not ok_any and fam == st.home_family:
                        try:
                            st.improve_from_failure(model, task)
                        except BudgetExceeded:
                            pass
            capability_by_round[name].append(round(succ / tot, 4) if tot else 0.0)

        # ---- exchange phase (institution-gated, quarantined) ----------------
        for name, st in states.items():
            for exporter in inst.visible(name):
                for skill in states[exporter].library.skill_names():
                    if skill in st.library.skill_names():
                        continue
                    if not inst.may_adopt(name, exporter):
                        continue
                    _consider_adoption(cfg, inst, log, model, registry,
                                       importer=st, exporter_name=exporter,
                                       exporter=states[exporter], skill=skill, rnd=rnd)

    return _summarise(cfg, log, states, capability_by_round)


def _consider_adoption(cfg, inst, log, model, registry, *, importer, exporter_name,
                       exporter, skill, rnd) -> None:
    """Tentatively install a candidate skill, run tiered quarantine against it
    (this is where the v0 stub is fixed — probes see the INSTALLED candidate),
    then keep it or roll it back. Poison, if any, is applied to the artifact by
    the designated poisoner and recorded in the ground-truth registry."""
    fam = skill_family(skill)
    artifact = exporter.library.export_skill(skill)

    poisoned = (isinstance(inst, AdversarialTrade)
                and inst.is_poisoner(exporter_name) and fam == "unit_chain")
    if poisoned:
        artifact = poison_artifact(artifact)

    # tentative install + register ground-truth poison status
    importer.library.import_skill(artifact, exporter_name)
    if poisoned:
        registry[(importer.name, fam)] = True

    regression = importer.regression_store[:5]
    probes = GENS[fam].batch(seed=cfg.seed * 131 + rnd * 17 + 3, n=cfg.n_probes)
    report = run_quarantine(
        cfg.quarantine, regression, probes,
        evaluate=lambda t: importer.attempt(model, t, phase="quarantine"))

    if not report.accepted:  # roll back
        importer.library.remove_skill(skill)
        registry.pop((importer.name, fam), None)

    log.append("adoption_decision", state=importer.name, exporter=exporter_name,
               skill=skill, family=fam, accepted=report.accepted,
               level=report.level, poisoned=poisoned,
               regression_passed=report.regression_passed,
               regression_total=report.regression_total,
               probes_passed=report.probes_passed, probes_total=report.probes_total)


def _summarise(cfg, log, states, capability_by_round) -> dict:
    events = log.read()
    per_state = {}
    for n, st in states.items():
        traj = capability_by_round[n]
        per_state[n] = {
            "final_capability": traj[-1] if traj else 0.0,
            "capability_by_round": traj,
            "pass^k": round(pass_k(trials_by_task(events, n), cfg.k_trials), 3),
            "library": st.library.skill_names(),
            "budget": st.budget.snapshot(),
        }
    caps = [per_state[n]["final_capability"] for n in STATES]
    overheads = [per_state[n]["budget"]["governance_overhead"] for n in STATES]
    return {
        "institution": cfg.institution,
        "quarantine": cfg.quarantine.value,
        "seed": cfg.seed,
        "states": per_state,
        "mean_capability": round(sum(caps) / len(caps), 4),
        "capability_gini": round(gini(caps), 4),
        "governance_overhead": round(sum(overheads) / len(overheads), 4),
        "poison_spread": poison_spread(events),
        "adoptions": adoption_edges(events),
    }


# --------------------------------------------------------------------------
# sweeping the matrix
# --------------------------------------------------------------------------

DEFAULT_INSTITUTIONS = ["autarky", "free_trade", "clubs", "adversarial_trade"]
DEFAULT_LEVELS = [QuarantineLevel.NONE, QuarantineLevel.REGRESSION,
                  QuarantineLevel.REGRESSION_PLUS_PROBES]
DEFAULT_SEEDS = (0, 1, 2)


def run_grid(institutions=None, levels=None, seeds=DEFAULT_SEEDS, **cfg_kwargs) -> list:
    """Cartesian sweep institutions x levels x seeds. Returns a flat list of
    per-trial summaries (each also carrying its institution/level/seed)."""
    institutions = institutions or DEFAULT_INSTITUTIONS
    levels = levels or DEFAULT_LEVELS
    results = []
    for institution in institutions:
        for level in levels:
            for seed in seeds:
                results.append(run_trial(TrialConfig(
                    institution=institution, quarantine=level, seed=seed, **cfg_kwargs)))
    return results


def _mean_std(xs):
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / n
    return mean, var ** 0.5


def aggregate(results: list) -> list:
    """Fold seeds → one row per (institution, quarantine level) with mean/std of
    the headline metrics. Rows are ordered by the DEFAULT sweep order."""
    cells: dict = {}
    order: list = []
    for r in results:
        key = (r["institution"], r["quarantine"])
        if key not in cells:
            cells[key] = []
            order.append(key)
        cells[key].append(r)
    rows = []
    for key in order:
        trials = cells[key]
        cap_m, cap_s = _mean_std([t["mean_capability"] for t in trials])
        gini_m, gini_s = _mean_std([t["capability_gini"] for t in trials])
        gov_m, gov_s = _mean_std([t["governance_overhead"] for t in trials])
        poison_m, poison_s = _mean_std([t["poison_spread"]["adoption_rate"] for t in trials])
        offered = sum(t["poison_spread"]["offered"] for t in trials)
        adopted = sum(t["poison_spread"]["adopted"] for t in trials)
        rows.append({
            "institution": key[0],
            "quarantine": key[1],
            "seeds": len(trials),
            "mean_capability": round(cap_m, 4),
            "capability_std": round(cap_s, 4),
            "capability_gini": round(gini_m, 4),
            "governance_overhead": round(gov_m, 4),
            "governance_overhead_std": round(gov_s, 4),
            "poison_adoption_rate": round(poison_m, 4),
            "poison_offered": offered,
            "poison_adopted": adopted,
        })
    return rows
