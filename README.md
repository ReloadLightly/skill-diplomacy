# Skill Diplomacy

**When self-improving agents can copy each other's improvements, checking what you
receive is paid for out of the same budget as improving yourself. This repository
measures that trade-off.**

---

## The question

AI agents have started to improve themselves in a modest but real way. They do not
retrain their own weights; they write things down. An agent that fails a task can
write a procedure for next time, keep it, and load it when a similar task appears.
Anthropic's Agent Skills format (`SKILL.md` files) is one deployed instance of
this, and there are now public marketplaces holding hundreds of thousands of such
files.

The moment those written procedures are *portable*, something changes that the
literature on self-improving agents has largely not studied: agents can acquire
capability from each other rather than only from their own experience. The unit of
analysis stops being one agent climbing a curve and becomes a **population** with
transmission between its members.

Populations with transmission have well-known pathologies. They converge on a
single variant and lose diversity. They propagate defects as readily as
improvements. And defending against bad transmission is not free — in biology,
immunity is paid for from the same energy budget as growth.

That last point is the one this repository is built around. An agent screening an
incoming skill spends tokens doing it, and those are exactly the tokens it could
have spent improving. **How much should you check?** is therefore not a safety
question that can be answered separately from a capability question. It is the
same question, and it has a measurable answer.

## Three dials

Everything here varies three things, and it is worth holding onto just these three:

**Exchange institution** — who is *permitted* to copy from whom. Autarky (nobody),
free trade (everybody), clubs (disjoint subgroups), adversarial trade (everybody,
including a saboteur).

**Export policy** — who is *willing* to give. Ranges from unconditional donation to
a strict rule of refusing any transfer that helps a rival more than yourself.

**Quarantine** — what you *test* before you keep what you were given. Three tiers:
nothing; a regression suite drawn from tasks you already solve; or fresh probes
drawn from the part of the task space the incoming skill claims to cover. Every
test costs tokens, charged to the importer.

A fourth quantity governs whether any of the three can be measured at all.
**Skill lift** is the difference a doctrine makes: the pass rate of an agent
holding it minus the pass rate of the same agent with an empty library. Where
lift is zero the task is solvable cold, the artifact is decorative, and no
institution can move the outcome. Measuring lift before running anything
institutional is the single cheapest guard against measuring nothing, and it is
the guard this repository did not have (`calibrate.py`).

In biological terms, which is how we now think this is best read: import is
**horizontal gene transfer**, a defective skill is a **parasite**, quarantine is an
**immune system**, and the token budget is a **metabolism**. Those analogies are not
decoration — each corresponds to a literature with results we have to answer to
(see `RELATEDWORK.md`).

## What we have found so far

Results carry an honest status label, because two very different kinds of claim
live in this repository.

**Harness results** come from a deterministic scripted stand-in for the model. They
are properties of the mechanism, not facts about language models — closer to an
analytic derivation than an experiment. They are useful as a *null model*: they
say what the institution does when agents are perfect, tireless solvers.

**Live results** come from a real model behind the same harness and are genuinely
stochastic.

One design fact governs how every live row below can be read, so it is stated
once here rather than buried per-claim. Each live arm has **three seeds**. An
exact permutation test over two arms of three has C(6,3) = 20 arrangements, so
the smallest two-sided *p* it can return is **0.10 — regardless of effect
size**. No three-seed contrast in this repository can reach conventional
significance, including the ones that separate perfectly. Five seeds per arm
would drop that floor to 0.008. `python -m paper.reproduce` prints the floor
beside every p-value; `skill_diplomacy/metrics/stats.py` computes it.

| | status | finding |
|---|---|---|
| **The institution barely moves anything** | **live** | **The headline negative result.** The harness predicts free trade beats autarky by +0.67 capability (0.33 → 1.00). Live, across three seeds each, the gap is **+0.07 — smaller than the seed-to-seed standard deviation (0.11)**. The harness overstates the institutional effect roughly ninefold. The diagnosis is stark: in several live runs every agent finished with an *empty skill library* and still scored 0.89–1.00, because the base model already solves these tasks unaided. An institution can only redistribute capability the agents do not already have. |
| **Three of three original task families were measuring nothing** | **live** | Skill lift — the gain from holding a family's doctrine versus an empty library — is **+0.00 for `unit_chain`, +0.00 for `calendar_math`, and −0.17 for `modmath`**. Measured over six instances per family, which is too few for the instrument to resolve its own thresholds: every Wilson interval spans ≥ 0.39, `unit_chain`'s 6/6 floor is consistent with a true rate of 0.61, and modmath's −0.17 is **not distinguishable from zero** (0.83 [0.44, 0.97] against 0.67 [0.30, 0.90]). The saturated verdict is safe because it is corroborated by the institutional run; the negative-lift reading is not, and should not be leaned on until n rises. The scripted harness scores all three at +1.00 by construction, because it is built to fail without a doctrine. The information-carrying `lexicon` family added in response scores **+1.00 live, from a floor of 0.00**. Run `python calibrate.py --live --lexicon` to reproduce. |
| **The harness's conditional prediction was right; the original tasks violated its premise** | **live** | Re-running the same autarky-versus-free-trade contrast, model, harness and seeds over *load-bearing* families recovers the predicted effect: **autarky 0.333 ± 0.000, free trade 1.000 ± 0.000, a gap of +0.667 with zero variance across three seeds each** — against +0.07 over saturated families. The separation is total and the exact-permutation *p* is nonetheless 0.10, because that is the floor three seeds per arm imposes; the honest reading is "consistent with a large effect, not yet significant", and the remedy is two more seeds rather than a stronger claim. Each state is endowed with one private reference skill, isolating transmission from discovery. The institutional treatment is unchanged; the task and initial knowledge endowment now satisfy the premise that capability tracks the library. |
| Screening blindness | harness | Home-shard regression admits **100%** of poisoned artifacts while consuming 23% of the budget — expensive and perfectly blind. |
| **A fixed screen fails all-or-nothing, across the whole population at once** | harness | **The corrected headline.** Over 24 seeds, a held-out probe suite drawn once per round admits either **0% or 100%** of poisoned artifacts in every single seed — 14 catches, 10 complete misses, nothing in between. Re-drawing probes per screening event never produces either extreme (range 0.08–0.56). The two arms' *mean* admitted rates are **not distinguishable** (0.417 vs 0.333, p = 0.44); their spreads differ by 4.4× (sd 0.493 vs 0.112, p = 5e-05), at 63% and 65% overhead. So re-drawing does not buy a lower expected contamination rate — it removes **correlated, population-wide screening failure**. A fixed suite is one draw shared by every importer, so when it has a hole they all fall into the same hole simultaneously. The exposure is tail risk, not mean risk. An earlier live smoke run showed probes rejecting an overfit skill that regression accepted; the full comparison has not been replicated live. |
| Parity, not abundance, is the boundary condition | harness | Under a **uniform** endowment the relative-gains dial is a two-level step whatever the family count — 3 families or 12, the sweep takes exactly two capability values. Under a **graded** endowment it traces a curve at 3 families already (3 levels), more finely at 12 (5) and at the full v2 scale (7). So exact parity is where the mechanism is inert, and scarcity sets the *resolution* at which the dial can be read rather than switching the effect on. This supersedes an earlier claim that "with three task families every arrangement returns identical capability", which does not reproduce: at three families autarky is 0.333, clubs 0.556, free trade 1.000. The corrected version is what Powell (1991) predicts, since relative-gains sensitivity is endogenous to asymmetry. |
| Inequality is non-monotone | harness | As export restriction tightens, mean capability falls monotonically, but *inequality* peaks at moderate restriction (Gini ≈ 0.68) and falls again under strict autarky — strict refusal produces not a hierarchy but a flat, uniformly poor population. Robust across five endowment shapes; vanishes only under exact symmetry. |
| Austerity admits contagion | harness | Under a binding budget, agents that cannot afford to screen and adopt anyway take on 228 defective skills, 198 of them acquired second-hand through honest intermediaries. When budgets are generous the same policy never triggers. Screening is a luxury good. |
| Governance is costlier live | live | On a real model, screening consumed 53% of the budget versus 20% under the scripted stand-in — the price of governance is substantially steeper than the harness implies. |

## What is not yet true

**Only the autarky-versus-free-trade contrast has been recovered on a live model
over a load-bearing family.** That result uses one model, one information-carrying
archetype, three states and three seeds, with one reference skill endowed per
state. Clubs, adversarial trade, quarantine, inequality and monoculture have not
yet received equivalent live replication. Calibrating each family against an
empty-library control remains a precondition for interpreting any such comparison.

The scripted stand-in cannot speak to monoculture at all: it emits one playbook
text for every skill, so library similarity is 1.0 by construction. That question
needs live runs, which have only just begun.

The new lexicon variants create genuine information scarcity but still constitute
only one archetype. Genuinely distinct load-bearing archetypes are the next
addition; otherwise the live result establishes one mechanism rather than a broad
task-space claim.

The saboteur is scripted rather than adaptive. In evolutionary computation an
adversary that does not itself evolve is a static red-team probe, not coevolution,
and we label it as such.

Several findings above have ancestors we did not know about when we found them.
In-distribution screening being structurally blind is a rediscovery of a result
from artificial immune systems (self-derived detectors provably have uncoverable
"holes"). Open exchange driving monoculture is a known island-model result about
migration and takeover time. `RELATEDWORK.md` states plainly which of our results
are new and which are re-derivations in a new substrate.

## Running it

```bash
pytest -q                                # 119 tests, no API key needed
python -m paper.reproduce --check        # every deterministic number, vs a locked manifest
python -m paper.figures                  # -> paper/fig/*.svg
python calibrate.py --lexicon            # skill lift per family (start here)
python calibrate.py --live --lexicon     # ...against a real model: 1/4 families survive
python run_lex.py free_trade 0           # live institution run over load-bearing families
python run_probes.py --seeds 24          # fixed vs re-drawn probe coverage (scripted)
python run_v1.py                         # the institution × quarantine grid (deterministic)
python run_v2.py --sweep k               # the export-restriction dial → capability and inequality
python run_v2.py --sweep budget          # governance under a budget that actually binds
python run_h1.py free_trade 0            # one live institutional trial
```

Everything except the live path is deterministic and stdlib-only: no API key, no
network, no dependencies beyond `pytest`. Every headline number reproduces from
one command — `python -m paper.reproduce --check`, which CI runs on every push
and which fails if any of them drifts.

Every metric is a pure fold over an append-only event log, so results can be
recomputed from the log alone — and the logs behind the headline deterministic
claims are committed under `runs/logs/` so a reader can do exactly that.
`python -m paper.export_log` regenerates them and then folds them back,
recomputing `poison_spread`, `export_refusals` and `pass^k` from the log alone
and checking each against what the run reported. An exported log nobody folds
over is a file, not evidence.

## How it is built

An append-only JSONL event log is the substrate; nothing mutates history. Task
families come from parameterized generators that compute their own ground truth,
so verification is exact and held-out probes are unlimited and contamination-proof.
Skill libraries are real `SKILL.md` folders with provenance lineage, so the
artifact that transfers is the artifact deployed systems actually use. Whether a
skill is defective is derived from its *content*, not from who sent it, so the
property survives being laundered through an honest intermediary — which is the
only way transitive propagation can be measured at all.

```
skill_diplomacy/
  harness/      event log, token budget with a screening sub-account, model clients
  bank/         self-verifying task generators; variants dial for scarcity
  skills/       Agent-Skills-format libraries, provenance, transactional edits
  institutions/ exchange institutions, export policies, quarantine tiers
  metrics/      capability, Gini, pass^k, adoption graph, contamination spread
                stats: Wilson, bootstrap, exact permutation, dispersion, and the
                design floor a seed count imposes before any data exist
  experiment/   the trial runner and the scripted null model
paper/
  reproduce.py  one command for every deterministic number, checked against a
                locked manifest by CI; live artifacts are audited for provenance
                rather than pretended to be re-derivable
  figures.py    the four figures, rendered as stdlib SVG so that "reproduce the
                figures" does not require a numerical stack the rest does not
```

## Reading

`RELATEDWORK.md` — the four literatures this sits inside, what is genuinely
unclaimed, and what is a rediscovery.
`CRITIQUE.md` — an adversarial review of this repository, including the bugs found
and the experiments that do not yet support their headline.
`DEFECTS.md` — the defect register: every published number that was wrong,
unreproducible, or measuring something other than its claim, with what is closed,
what is still open, and which limitations are being declared rather than fixed.

## Status and provenance

This is basic science for [ACTIR](https://github.com/ReloadLightly), a larger
project on adaptive computational models of international politics. It is a
working research repository, not a library: the interfaces will change, and the
results above are staged toward a paper rather than finished.
