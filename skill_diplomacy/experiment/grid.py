"""The experiment grid: institution x export-policy x quarantine-level x seed.

`run_trial` executes one fully-specified cell; `run_grid` sweeps the matrix;
`aggregate` folds seeds into mean/std per cell. Everything downstream is a fold
over the per-trial event log.

Roster (generalised in sprint 2 from a hard-coded triangle to N states): states
are named A, B, C, ... and sharded round-robin across the three task families,
so with N=9 each family has three specialists. Each state is evaluated on ALL
families every round but self-improves only on its home family, so off-shard
capability arrives ONLY through exchange — which is what the institution and
the export policy gate.

Three states was enough to show that the plumbing worked and too few to show
anything about institutions: with a fully-connected triangle every state
reaches every other in one hop, so there is no diffusion, no cascade, no
intermediary, and no room for a poisoned artifact to travel. N is now a dial;
the v1 defaults are preserved exactly (N=3, `open` export policy, ungated
self-edits) so the published v1 table still reproduces cell-for-cell after the
refactor, and `run_v2.py` selects the new regime explicitly.
"""
from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
import shutil
import string
import tempfile

from ..bank.base import shard_families
from ..bank.generators.calendar_math import CalendarMathGenerator
from ..bank.generators.modmath import ModMathGenerator
from ..bank.generators.unit_chain import UnitChainGenerator
from ..bank.variants import make_bank
from ..harness.budget import BudgetExceeded, BudgetMeter
from ..harness.events import EventLog
from ..harness.provenance import run_provenance
from ..harness.model import ScriptedModel
from ..institutions.exchange import ExchangeContext, make_policy
from ..institutions.institutions import (AdversarialTrade, Autarky, Clubs,
                                         FreeTrade, is_poisoned_artifact,
                                         is_poisoned_body, poison_artifact)
from ..institutions.quarantine import QuarantineLevel, run_quarantine
from ..skills.format import artifact_hash
from ..metrics.metrics import (adoption_edges, distinct_bodies, export_refusals,
                               gini, mean_pairwise_similarity, pass_k,
                               poison_spread, trials_by_task)
from ..state import AgentState
from .oracle import make_oracle

STATES = ["A", "B", "C"]          # v1 default roster, kept for import compat
FAMILIES = ["unit_chain", "calendar_math", "modmath"]
GENS = {
    "unit_chain": UnitChainGenerator(),
    "calendar_math": CalendarMathGenerator(),
    "modmath": ModMathGenerator(),
}


def skill_family(skill_name: str) -> str:
    """`unit-chain-doctrine` -> `unit_chain` (inverse of state.py's naming)."""
    return skill_name.rsplit("-doctrine", 1)[0].replace("-", "_")


def state_names(n: int) -> list[str]:
    """A..Z then A2..Z2 — stable, index-ordered, no hashing."""
    letters = string.ascii_uppercase
    return [letters[i] if i < 26 else f"{letters[i % 26]}{i // 26 + 1}" for i in range(n)]


@dataclass
class TrialConfig:
    institution: str            # autarky | free_trade | clubs | adversarial_trade
    quarantine: QuarantineLevel
    seed: int
    rounds: int = 3
    tasks_per_round: int = 3
    k_trials: int = 3           # eval repeats per task → populates pass^k
    n_probes: int = 6           # fresh off-shard probes per adoption
    # -- roster -------------------------------------------------------------
    n_states: int = 3           # v1 default; run_v2 uses 9
    poisoner: str = "A"         # adversarial_trade only (single-poisoner v1 form)
    n_poisoners: int = 1
    clubs: tuple | None = None  # None → contiguous clubs of `club_size`
    club_size: int = 2
    # -- task bank (sprint 2) ----------------------------------------------
    n_variants: int = 1          # variants per archetype → 3*n_variants families.
                                 # 1 reproduces v1 exactly; >1 creates scarcity.
    # -- task bank (sprint 3) ----------------------------------------------
    archetypes: tuple | None = None   # None → the v1 three. ("lexicon",) selects
                                      # only load-bearing families, which is the
                                      # only setting where an institutional
                                      # comparison measures anything at all.
    seed_references: bool = False     # give each state the reference doctrine for
                                      # its HOME families at t=0. Required for
                                      # information-carrying archetypes: a model
                                      # cannot invent a private glyph table by
                                      # introspection, so without this a
                                      # specialist never holds anything worth
                                      # exporting. It separates the DISCOVERY
                                      # question (how does the first copy arise?)
                                      # from the TRANSMISSION question (what
                                      # happens once it exists), and this
                                      # repository is about the second.
    # -- endowment (sprint 2) ----------------------------------------------
    endowment: str = "uniform"   # uniform | step | zipf
    n_great_powers: int = 0      # `step` only: how many states are great powers
    great_power_weight: int = 3  # shares of the family pool a great power gets
    # -- exchange policy (sprint 2) ----------------------------------------
    export_policy: str = "open"          # open | reciprocal | relative_gains | defector
    relative_gains_sensitivity: int = 0  # Grieco k: 0 open, 1 reciprocity, >1 strict
    relative_gains_mode: str = "return"  # return | balance
    n_defectors: int = 0                 # last n states export nothing
    # -- governance ---------------------------------------------------------
    gate_self_edits: bool = False        # v1 behaviour is False; run_v2 sets True
    fresh_probes: bool = False           # re-draw the probe suite per screening
                                         # event rather than once per round. See
                                         # _consider_adoption. False reproduces v1.
    screen_bankruptcy: str = "refuse"    # refuse | adopt_unscreened — what a
                                         # state does when it CANNOT AFFORD to
                                         # screen an import. E4's core modelled
                                         # choice; default 'refuse' keeps binding-
                                         # budget runs safe AND runnable.
    # -- budget -------------------------------------------------------------
    max_tokens: int = 2_000_000  # generous by default: capability reflects
    max_rollouts: int = 20_000   # institution, not starvation. Sweep to bind.
    dump_transcripts: bool = False


# --------------------------------------------------------------------------
# roster / topology
# --------------------------------------------------------------------------

def _roster(cfg: TrialConfig) -> list[str]:
    return state_names(cfg.n_states)


def _auto_clubs(names: list[str], size: int) -> list[list[str]]:
    return [names[i:i + size] for i in range(0, len(names), size)]


def _make_institution(cfg: TrialConfig, names: list[str]):
    if cfg.institution == "autarky":
        return Autarky(states=list(names))
    if cfg.institution == "free_trade":
        return FreeTrade(states=list(names))
    if cfg.institution == "clubs":
        clubs = ([list(c) for c in cfg.clubs] if cfg.clubs
                 else _auto_clubs(names, cfg.club_size))
        return Clubs(states=list(names), clubs=clubs)
    if cfg.institution == "adversarial_trade":
        poisoners = [n for n in names[:max(1, cfg.n_poisoners)]]
        if cfg.poisoner and cfg.poisoner in names and cfg.poisoner not in poisoners:
            poisoners.append(cfg.poisoner)
        return AdversarialTrade(states=list(names), poisoner=cfg.poisoner,
                                poisoners=poisoners)
    raise ValueError(f"unknown institution: {cfg.institution}")


def _policies(cfg: TrialConfig, names: list[str]) -> dict:
    base = make_policy(cfg.export_policy, cfg.relative_gains_sensitivity,
                       cfg.relative_gains_mode)
    pol = {n: base for n in names}
    # clamp: n_defectors > n_states must mean "everybody", not a negative slice
    # that silently wraps to the LAST few states (which read as a small-defector
    # arm and would have quietly corrupted the free-rider sweep's tail).
    d = max(0, min(cfg.n_defectors, len(names)))
    for n in names[len(names) - d:] if d else []:
        pol[n] = make_policy("defector")
    return pol


ENDOWMENTS = ("uniform", "step", "zipf")


def _weights(cfg: TrialConfig, n: int) -> list[int]:
    """Shares of the family pool per state — the capability distribution.

    Dispatches on `cfg.endowment` and nothing else. It used to branch on
    `endowment == "step" or n_great_powers`, which made two silent traps:

      * `--endowment step` WITHOUT `--great-powers` returned all-ones, i.e. it
        ran `uniform` while reporting itself as a graded endowment. Every
        relative-gains result over that arm was a parity run in disguise, and
        parity is precisely the condition under which the realist mechanism is
        definitionally inert — so the arm could not have shown an effect and its
        null was uninformative rather than evidential.
      * `--endowment zipf --great-powers 3` took the STEP branch and discarded
        zipf entirely, while `_summarise` then labelled the run `"step"`
        regardless of the flag actually passed.

    A misconfiguration that changes which distribution you sampled must not be
    recoverable only by reading the source, so both now raise."""
    if cfg.endowment not in ENDOWMENTS:
        raise ValueError(f"unknown endowment {cfg.endowment!r}; "
                         f"expected one of {ENDOWMENTS}")
    if cfg.endowment == "step":
        if cfg.n_great_powers <= 0:
            raise ValueError(
                "endowment='step' needs n_great_powers > 0 (CLI: --great-powers). "
                "Without it every state gets an equal share, which is 'uniform' "
                "under a different name and silently removes the asymmetry the "
                "step endowment exists to create.")
        if cfg.n_great_powers >= n:
            raise ValueError(
                f"n_great_powers={cfg.n_great_powers} with n_states={n}: every "
                "state would be a great power, which is 'uniform' again.")
        return [cfg.great_power_weight if i < cfg.n_great_powers else 1
                for i in range(n)]
    if cfg.n_great_powers:
        raise ValueError(
            f"n_great_powers={cfg.n_great_powers} is a 'step' parameter but "
            f"endowment={cfg.endowment!r}. Pass --endowment step, or drop "
            f"--great-powers; silently applying one while reporting the other "
            f"is how a zipf run came to be published as a step run.")
    if cfg.endowment == "zipf":
        return [max(1, -(-cfg.great_power_weight // (i + 1))) for i in range(n)]
    return [1] * n


def _shards(cfg: TrialConfig, names: list[str], families: list[str]) -> dict:
    """Home-shard assignment: which families a state can self-improve on.

    Uniform (v1) is one family per state, round-robin. That is the assumption
    that quietly killed the sprint's first export-policy sweep: if every state
    holds exactly one doctrine at every decision point, then for every pair
    |theirs \\ mine| = |mine \\ theirs| = 1, the relative-gains score is the same
    constant for all pairs, and the dial can only ever be a step between free
    trade and autarky. A `step` distribution (a few great powers) breaks the
    symmetry into a handful of levels; `zipf` — shares falling as 1/rank —
    grades it finely enough for the dial to trace a curve.

    Asymmetric capability is the *condition* under which relative-gains
    reasoning has content. Holding it fixed at parity does not test the realist
    claim; it assumes the claim away."""
    weights = _weights(cfg, len(names))
    if all(w == 1 for w in weights):
        return {s: [families[i % len(families)]] for i, s in enumerate(names)}
    slots: list[str] = []
    for n, w in zip(names, weights):
        slots.extend([n] * w)
    homes: dict = {n: [] for n in names}
    for j, fam in enumerate(families):
        homes[slots[j % len(slots)]].append(fam)
    for i, n in enumerate(names):          # nobody is left with an empty shard
        if not homes[n]:
            homes[n].append(families[i % len(families)])
    return homes


def _bank(cfg: TrialConfig) -> tuple[dict, list[str]]:
    """Per-config task bank. At n_variants=1 with default archetypes this is
    byte-identical in behaviour to the module-level GENS/FAMILIES, so the
    published v1 table reproduces."""
    gens = make_bank(cfg.n_variants, archetypes=cfg.archetypes)
    return gens, list(gens.keys())


def _seed_references(cfg: TrialConfig, states: dict, gens: dict) -> None:
    """Install each state's home-family reference doctrines at t=0.

    Only generators that carry information expose `reference_body()`; for the
    rest this is a no-op, so switching the flag on cannot disturb the v1 grid."""
    if not cfg.seed_references:
        return
    for name, st in states.items():
        for fam in st.home_families:
            inner = getattr(gens[fam], "inner", gens[fam])
            body = getattr(inner, "reference_body", None)
            if body is None:
                continue
            skill = f"{fam.replace('_', '-')}-doctrine"
            st.library.add_skill(skill, f"Doctrine for {fam} tasks "
                                        f"(home shard of {name}).", body())
            st.log.append("skill_commit", state=name, skill=skill, family=fam,
                          source="endowment",
                          content_hash=st.library.content_hash(skill))


def _eval_seed(cfg: TrialConfig, rnd: int, name: str, fam: str,
               names: list[str], families: list[str]) -> int:
    # stable index, NOT hash(name): Python salts str hashes per process, which
    # would make trials irreproducible across runs.
    return (cfg.seed * 1_000_003 + rnd * 9973 + names.index(name) * 31
            + families.index(fam) * 7)


def _stable_hash(text: str) -> str:
    """sha256 hex — NOT Python's hash(), which is salted per process and would
    make probe draws irreproducible across runs."""
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def _artifact_hash(artifact: dict) -> str:
    """Delegates to the one definition of content identity (skills/format.py).

    These were two separate implementations that disagreed: this one hashed
    name+body+scripts, `SkillLibrary.content_hash` hashed the whole SKILL.md
    including provenance frontmatter. Adoption events keyed on the first and
    lineage (`origin_hash`) on the second, so the two could not be joined and
    `distinct_bodies` counted copies rather than contents. One definition now."""
    return artifact_hash(artifact["name"], artifact["body"],
                         artifact.get("scripts", {}))


def _poison_lookup(states: dict):
    """Ground truth for the oracle, DERIVED from what is installed right now.

    This is the root fix for defect 3.1. v1 kept a `(state, family) -> bool`
    dict that the harness updated at the point of import, keying it on the
    exporter's identity; a poisoned body that reached a third state through an
    honest second one therefore arrived unflagged and behaved correctly. Here
    the oracle simply reads the installed SKILL.md, so the property travels
    with the artifact across arbitrarily many hops and disappears the instant
    a skill is rolled back — no bookkeeping to forget."""
    def lookup(name: str, family: str) -> bool:
        st = states.get(name)
        if st is None:
            return False
        skill = f"{family.replace('_', '-')}-doctrine"
        if skill not in st.library.skill_names():
            return False
        return is_poisoned_body(st.library.body(skill))
    return lookup


# --------------------------------------------------------------------------
# one trial
# --------------------------------------------------------------------------

def run_trial(cfg: TrialConfig, model=None) -> dict:
    """Run one grid cell. Returns a JSON-serialisable summary dict.

    `model` defaults to the deterministic ScriptedModel + poison-aware oracle.
    Pass an AnthropicModel (see run_v2.py --live) for a real run; the oracle is
    then bypassed entirely and the poison acts the way it is supposed to — as
    text in the doctrine the model actually reads."""
    workdir = Path(tempfile.mkdtemp(prefix=f"sd_{cfg.institution}_{cfg.quarantine.value}_"))
    try:
        return _run_trial_in(cfg, workdir, model)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _run_trial_in(cfg: TrialConfig, workdir: Path, model=None) -> dict:
    log = EventLog(workdir / "events.jsonl")
    names = _roster(cfg)
    gens, families = _bank(cfg)
    shards = _shards(cfg, list(names), list(families))
    inst = _make_institution(cfg, names)
    policies = _policies(cfg, names)

    states: dict = {}
    if model is None:
        model = ScriptedModel(make_oracle(_poison_lookup(states)))

    states.update({
        n: AgentState.create(n, shards[n], workdir,
                             BudgetMeter(cfg.max_tokens, cfg.max_rollouts), log,
                             keep_transcripts=cfg.dump_transcripts)
        for n in names
    })
    _seed_references(cfg, states, gens)
    capability_by_round: dict = {n: [] for n in names}
    # Affordability, kept separate from ability. Under a non-binding budget this
    # is 1.0 everywhere and capability is unchanged; where the budget binds, the
    # two must be read together -- a state at capability 1.0 and coverage 0.1
    # answered everything it could pay for and could pay for almost nothing.
    coverage_by_round: dict = {n: [] for n in names}
    # `gate_self_edits` reuses the import quarantine tier, so asking for the
    # gate without naming a tier used to yield QuarantineLevel.NONE — a flag
    # that reads as "self-edits are screened" and screens nothing. Same species
    # of silent no-op as `--endowment step` without `--great-powers`, and with
    # sharper consequences: with a fallible agent the ungated path is not merely
    # unprotected, it is destructive (see `run_ratchet.py`). So it raises.
    if cfg.gate_self_edits and cfg.quarantine is QuarantineLevel.NONE:
        raise ValueError(
            "gate_self_edits=True with quarantine=NONE gates nothing: the "
            "self-edit gate reuses the import quarantine tier, and NONE accepts "
            "unconditionally. Choose a tier (REGRESSION or "
            "REGRESSION_PLUS_PROBES), or set gate_self_edits=False to state "
            "plainly that self-edits are uncontrolled.")
    self_gate = cfg.quarantine if cfg.gate_self_edits else QuarantineLevel.NONE

    for rnd in range(cfg.rounds):
        # ---- eval + self-improve phase (all families, k trials each) --------
        for name, st in states.items():
            succ = ran = scheduled = 0
            for fam in families:
                for task in gens[fam].batch(
                        seed=_eval_seed(cfg, rnd, name, fam, names, families),
                        n=cfg.tasks_per_round):
                    ok_any = False
                    for _ in range(cfg.k_trials):
                        scheduled += 1
                        try:
                            ok = st.attempt(model, task)
                        except BudgetExceeded:
                            # An attempt that never ran is not a wrong answer.
                            # It used to be scored as one and still counted in
                            # the denominator, so under a binding budget
                            # `capability` silently became ability x
                            # affordability -- and the austerity experiment,
                            # which exists precisely to study binding budgets,
                            # read a state that could not afford to try as a
                            # state that could not solve. Same defect as scoring
                            # a transport failure as cognition (see
                            # harness/cli_model.py); both are now counted rather
                            # than folded into the outcome.
                            continue
                        ran += 1
                        succ += 1 if ok else 0
                        ok_any = ok_any or ok
                    if not ok_any and st.is_home(fam):
                        probes = (gens[fam].batch(seed=cfg.seed * 977 + rnd * 41 + 5,
                                                  n=cfg.n_probes)
                                  if cfg.gate_self_edits else None)
                        try:
                            st.improve_from_failure(model, task, level=self_gate,
                                                    probes=probes)
                        except BudgetExceeded:
                            pass
            capability_by_round[name].append(round(succ / ran, 4) if ran else 0.0)
            coverage_by_round[name].append(
                round(ran / scheduled, 4) if scheduled else 0.0)

        # ---- exchange phase (institution-gated, policy-gated, quarantined) --
        ctx = ExchangeContext()
        for importer_name, st in states.items():
            for exporter_name in inst.visible(importer_name):
                if not inst.may_adopt(importer_name, exporter_name):
                    continue
                ctx.libraries = {n: set(s.library.skill_names())
                                 for n, s in states.items()}
                for skill in states[exporter_name].library.skill_names():
                    if skill in st.library.skill_names():
                        continue
                    granted, reason = policies[exporter_name].will_export(
                        exporter=exporter_name, importer=importer_name,
                        skill=skill, ctx=ctx)
                    log.append("export_decision", exporter=exporter_name,
                               importer=importer_name, skill=skill,
                               granted=granted, reason=reason,
                               policy=policies[exporter_name].name)
                    if not granted:
                        continue
                    ctx.record_grant(exporter_name, importer_name)
                    _consider_adoption(cfg, inst, log, model, gens,
                                       importer=st, exporter_name=exporter_name,
                                       exporter=states[exporter_name],
                                       skill=skill, rnd=rnd)

    return _summarise(cfg, log, states, capability_by_round, names, gens,
                      model, coverage_by_round)


def _consider_adoption(cfg, inst, log, model, gens, *, importer, exporter_name,
                       exporter, skill, rnd) -> None:
    """Tentatively install a candidate skill, run tiered quarantine against it
    (probes see the INSTALLED candidate), then keep it or roll it back."""
    fam = skill_family(skill)
    artifact = exporter.library.export_skill(skill)

    # first_hand: this exporter is a designated poisoner introducing the defect.
    # Everything else that arrives poisoned arrived that way — laundered through
    # an intermediary — and that is the case RQ3 is about.
    first_hand = (isinstance(inst, AdversarialTrade)
                  and inst.is_poisoner(exporter_name)
                  and inst.poisons_family(fam))
    if first_hand:
        artifact = poison_artifact(artifact)
    poisoned = is_poisoned_artifact(artifact)
    chash = _artifact_hash(artifact)

    # defect 3.2: a rejected artifact is remembered, not re-screened every round.
    # Without this the probes arm pays for the same screening decision once per
    # round and 'governance overhead' silently includes retry churn.
    if chash in importer.rejected_hashes:
        log.append("adoption_skipped", state=importer.name, exporter=exporter_name,
                   skill=skill, family=fam, content_hash=chash, reason="denylist")
        return

    before = importer.library.snapshot(skill)
    importer.library.import_skill(artifact, exporter_name)
    importer.screened_hashes.add(chash)

    regression = importer.regression_store[:5]
    # Probe freshness. Keyed only on (trial seed, round), ONE probe suite screens
    # every adoption in a round -- so a defect the suite happens to miss is
    # missed by every importer simultaneously, and once adopted it is never
    # re-examined. That is a coverage hole of exactly the kind D'haeseleer,
    # Forrest & Helman (1996) proved is unavoidable for finite self-derived
    # detector sets, and here it is severe enough to hide a targeted defect
    # completely. `fresh_probes` re-draws per screening event, which is what
    # "fresh held-out probes" was always supposed to mean. Default False keeps
    # the published v1 numbers; the comparison between the two is a result.
    pseed = cfg.seed * 131 + rnd * 17 + 3
    if cfg.fresh_probes:
        pseed += int(_stable_hash(f"{importer.name}|{exporter_name}|{skill}"), 16) % 100_000
    probes = gens[fam].batch(seed=pseed, n=cfg.n_probes)
    try:
        report = run_quarantine(
            cfg.quarantine, regression, probes,
            evaluate=lambda t: importer.attempt(model, t, phase="quarantine"))
    except BudgetExceeded:
        # The importer ran out of budget MID-SCREEN. v1/sprint-2 let this
        # exception escape the exchange phase and kill the whole trial, which is
        # exactly why E4 (--sweep budget) was 'wired but unanalysed': it crashes
        # at precisely the budgets where governance starts to bite. It is also a
        # modelling question, not just a bug: a state that cannot afford to
        # screen either REFUSES the import (forgoes the capability) or ADOPTS IT
        # UNSCREENED (takes the capability and the contamination risk). Which one
        # is a swept parameter (screen_bankruptcy); default 'refuse' is safe.
        adopt = cfg.screen_bankruptcy == "adopt_unscreened"
        if not adopt:
            importer.library.restore(skill, before)
            importer.rejected_hashes.add(chash)
        log.append("adoption_decision", state=importer.name, exporter=exporter_name,
                   skill=skill, family=fam, accepted=adopt, level=cfg.quarantine.value,
                   poisoned=poisoned, first_hand=first_hand, content_hash=chash,
                   regression_passed=0, regression_total=len(regression),
                   probes_passed=0, probes_total=len(probes), budget_exhausted=True)
        return

    if not report.accepted:  # roll back to the exact prior state
        importer.library.restore(skill, before)
        importer.rejected_hashes.add(chash)

    log.append("adoption_decision", state=importer.name, exporter=exporter_name,
               skill=skill, family=fam, accepted=report.accepted,
               level=report.level, poisoned=poisoned, first_hand=first_hand,
               content_hash=chash,
               regression_passed=report.regression_passed,
               regression_total=report.regression_total,
               probes_passed=report.probes_passed, probes_total=report.probes_total)


def _summarise(cfg, log, states, capability_by_round, names, gens,
               model=None, coverage_by_round=None) -> dict:
    events = log.read()
    per_state = {}
    for n, st in states.items():
        traj = capability_by_round[n]
        per_state[n] = {
            "final_capability": traj[-1] if traj else 0.0,
            "capability_by_round": traj,
            "attempt_coverage": (
                round(coverage_by_round[n][-1], 4)
                if coverage_by_round and coverage_by_round[n] else 1.0),
            "attempt_coverage_by_round": (
                coverage_by_round[n] if coverage_by_round else []),
            "pass^k": round(pass_k(trials_by_task(events, n), cfg.k_trials), 3),
            "library": st.library.skill_names(),
            "budget": st.budget.snapshot(),
            "screened": len(st.screened_hashes),
            "rejected": len(st.rejected_hashes),
        }
    caps = [per_state[n]["final_capability"] for n in names]
    snaps = [per_state[n]["budget"] for n in names]
    libs = [states[n].library for n in names]

    def _mean(key):
        return round(sum(s[key] for s in snaps) / len(snaps), 4)

    screened = sum(per_state[n]["screened"] for n in names)
    quarantine_tokens = sum(s["quarantine_tokens"] for s in snaps)
    return {
        "institution": cfg.institution,
        "quarantine": cfg.quarantine.value,
        "export_policy": cfg.export_policy,
        "n_states": len(names),
        "n_variants": cfg.n_variants,
        # count the bank, do not assume three archetypes: cfg.archetypes can
        # select a single one, and a wrong denominator here misreports every
        # capability figure that is read against it.
        "n_families": len(gens),
        # Who and what produced this number. Without it a live result cannot be
        # attributed to a model, a date or a commit, and the harness/live status
        # label every claim in the README depends on rests on memory.
        "provenance": run_provenance(model, dataclasses.asdict(cfg)),
        # Population-level affordability. Below 1.0 the budget bound, and
        # `mean_capability` describes only the attempts that could be paid for.
        "attempt_coverage": round(
            sum(per_state[n]["attempt_coverage"] for n in names) / len(names), 4)
        if names else 1.0,
        "budget_bound": any(per_state[n]["attempt_coverage"] < 1.0 for n in names),
        "endowment": cfg.endowment,   # the flag actually passed, not a guess
        "n_great_powers": cfg.n_great_powers,
        "great_power_weight": cfg.great_power_weight,
        "shard_sizes": {n: len(states[n].home_families) for n in names},
        "seed": cfg.seed,
        "states": per_state,
        "mean_capability": round(sum(caps) / len(caps), 4),
        "capability_gini": round(gini(caps), 4),
        "governance_overhead": _mean("governance_overhead"),
        "import_screen_overhead": _mean("import_screen_overhead"),
        "self_screen_overhead": _mean("self_screen_overhead"),
        # defect 3.2: cost per UNIQUE artifact screened is the comparable number
        "unique_artifacts_screened": screened,
        "tokens_per_screen": round(quarantine_tokens / screened, 1) if screened else 0.0,
        "poison_spread": poison_spread(events),
        "exports": export_refusals(events),
        # RQ2: monoculture
        "library_similarity": round(mean_pairwise_similarity(libs), 4),
        "distinct_bodies": distinct_bodies(libs),
        "adoptions": adoption_edges(events),
        "transcripts": [t for n in names for t in states[n].transcripts] if cfg.dump_transcripts else [],
    }


# --------------------------------------------------------------------------
# sweeping the matrix
# --------------------------------------------------------------------------

DEFAULT_INSTITUTIONS = ["autarky", "free_trade", "clubs", "adversarial_trade"]
DEFAULT_LEVELS = [QuarantineLevel.NONE, QuarantineLevel.REGRESSION,
                  QuarantineLevel.REGRESSION_PLUS_PROBES]
DEFAULT_SEEDS = (0, 1, 2)


def run_grid(institutions=None, levels=None, seeds=DEFAULT_SEEDS, model=None,
             **cfg_kwargs) -> list:
    """Cartesian sweep institutions x levels x seeds. Returns a flat list of
    per-trial summaries (each also carrying its institution/level/seed)."""
    institutions = institutions or DEFAULT_INSTITUTIONS
    levels = levels or DEFAULT_LEVELS
    results = []
    for institution in institutions:
        for level in levels:
            for seed in seeds:
                results.append(run_trial(TrialConfig(
                    institution=institution, quarantine=level, seed=seed,
                    **cfg_kwargs), model=model))
    return results


def _mean_std(xs):
    """Mean and SAMPLE standard deviation (n-1).

    This used to divide by n. Seeds here are replicates drawn to estimate a
    population, not the population itself, so n-1 is the right convention — and
    more concretely, the +/- figures published in LETTER.md were computed by
    hand under n-1 (0.111 and 0.064) while every `capability_std` the code
    emitted used n (0.091 and 0.052). Two conventions, one of them in the paper
    and the other in the artifacts, is a discrepancy a replicator finds
    immediately and cannot explain."""
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mean = sum(xs) / n
    if n == 1:
        return mean, 0.0
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    return mean, var ** 0.5


def aggregate(results: list) -> list:
    """Fold seeds → one row per (institution, quarantine level, export policy)
    with mean/std of the headline metrics."""
    cells: dict = {}
    order: list = []
    for r in results:
        key = (r["institution"], r["quarantine"], r.get("export_policy", "open"))
        if key not in cells:
            cells[key] = []
            order.append(key)
        cells[key].append(r)
    rows = []
    for key in order:
        trials = cells[key]
        cap_m, cap_s = _mean_std([t["mean_capability"] for t in trials])
        gini_m, _ = _mean_std([t["capability_gini"] for t in trials])
        gov_m, gov_s = _mean_std([t["governance_overhead"] for t in trials])
        imp_m, _ = _mean_std([t.get("import_screen_overhead", 0.0) for t in trials])
        self_m, _ = _mean_std([t.get("self_screen_overhead", 0.0) for t in trials])
        poison_m, _ = _mean_std([t["poison_spread"]["adoption_rate"] for t in trials])
        sim_m, _ = _mean_std([t.get("library_similarity", 0.0) for t in trials])
        ref_m, _ = _mean_std([t.get("exports", {}).get("refusal_rate", 0.0) for t in trials])
        rows.append({
            "institution": key[0],
            "quarantine": key[1],
            "export_policy": key[2],
            "seeds": len(trials),
            "mean_capability": round(cap_m, 4),
            "capability_std": round(cap_s, 4),
            "capability_gini": round(gini_m, 4),
            "governance_overhead": round(gov_m, 4),
            "governance_overhead_std": round(gov_s, 4),
            "import_screen_overhead": round(imp_m, 4),
            "self_screen_overhead": round(self_m, 4),
            "poison_adoption_rate": round(poison_m, 4),
            "poison_offered": sum(t["poison_spread"]["offered"] for t in trials),
            "poison_adopted": sum(t["poison_spread"]["adopted"] for t in trials),
            "poison_transitive": sum(t["poison_spread"].get("transitive_adopted", 0)
                                     for t in trials),
            "unique_screened": sum(t.get("unique_artifacts_screened", 0) for t in trials),
            "library_similarity": round(sim_m, 4),
            "distinct_bodies": sum(t.get("distinct_bodies", 0) for t in trials),
            "export_refusal_rate": round(ref_m, 4),
        })
    return rows
