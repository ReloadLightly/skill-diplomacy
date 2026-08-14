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

| | status | finding |
|---|---|---|
| **The institution barely moves anything** | **live** | **The headline negative result.** The harness predicts free trade beats autarky by +0.67 capability (0.33 → 1.00). Live, across three seeds each, the gap is **+0.07 — smaller than the seed-to-seed standard deviation (0.11)**. The harness overstates the institutional effect roughly ninefold. The diagnosis is stark: in several live runs every agent finished with an *empty skill library* and still scored 0.89–1.00, because the base model already solves these tasks unaided. An institution can only redistribute capability the agents do not already have. |
| **Three of three original task families were measuring nothing** | **live** | Skill lift — the gain from holding a family's doctrine versus an empty library — is **+0.00 for `unit_chain`, +0.00 for `calendar_math`, and −0.17 for `modmath`** (the generic playbook actively *hurts*). The scripted harness scores all three at +1.00 by construction, because it is built to fail without a doctrine. The information-carrying `lexicon` family added in response scores **+1.00 live, from a floor of 0.00**. Run `python calibrate.py --live --lexicon` to reproduce. |
| Screening blindness | harness + live | A regression suite drawn from what you already do well accepts every defective skill offered (6/6). Fresh off-distribution probes catch every one, at ~4× the token cost. Reproduced on a live model, where probes rejected an overfitted self-authored skill that regression testing passed. |
| Scarcity precondition | harness | Institutions have no measurable effect unless skills are scarce relative to the task space. With three task families every arrangement returns identical capability. This is a methodological warning about a whole class of multi-agent evaluations. |
| Inequality is non-monotone | harness | As export restriction tightens, mean capability falls monotonically, but *inequality* peaks at moderate restriction (Gini ≈ 0.68) and falls again under strict autarky — strict refusal produces not a hierarchy but a flat, uniformly poor population. Robust across five endowment shapes; vanishes only under exact symmetry. |
| Austerity admits contagion | harness | Under a binding budget, agents that cannot afford to screen and adopt anyway take on 228 defective skills, 198 of them acquired second-hand through honest intermediaries. When budgets are generous the same policy never triggers. Screening is a luxury good. |
| Governance is costlier live | live | On a real model, screening consumed 53% of the budget versus 20% under the scripted stand-in — the price of governance is substantially steeper than the harness implies. |

## What is not yet true

**The institutional results above are not yet supported on live models.** The
negative result in the first row is the honest headline: with these task families
and this model, the exchange institution is measuring a variable that barely moves
the outcome. Until the tasks are hard enough that an agent without the relevant
skill reliably fails, every institutional comparison here is a comparison between
two ways of arriving at the same saturated score. Calibrating task difficulty
against an empty-library control is therefore the precondition for all of it, not
an improvement to it.

The scripted stand-in cannot speak to monoculture at all: it emits one playbook
text for every skill, so library similarity is 1.0 by construction. That question
needs live runs, which have only just begun.

The task families are variants of three archetypes, which creates skill *scarcity*
but not task *diversity* — a live model may transfer across variants far more
easily than across archetypes. Genuinely distinct archetypes are the next addition.

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
pytest -q                                # 70 tests, ~4s, no API key needed
python calibrate.py --lexicon            # skill lift per family (start here)
python calibrate.py --live --lexicon     # ...against a real model: 1/4 families survive
python run_v1.py                         # the institution × quarantine grid (deterministic)
python run_v2.py --sweep k               # the export-restriction dial → capability and inequality
python run_v2.py --sweep budget          # governance under a budget that actually binds
python run_h1.py free_trade 0            # one live institutional trial
```

Everything except the live path is deterministic and stdlib-only: no API key, no
network, no dependencies beyond `pytest`. Every headline number reproduces from one
command. Every metric is a pure fold over an append-only event log, so results can
be recomputed from the log alone.

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
  experiment/   the trial runner and the scripted null model
```

## Reading

`RELATEDWORK.md` — the four literatures this sits inside, what is genuinely
unclaimed, and what is a rediscovery.
`CRITIQUE.md` — an adversarial review of this repository, including the bugs found
and the experiments that do not yet support their headline.

## Status and provenance

This is basic science for [ACTIR](https://github.com/ReloadLightly), a larger
project on adaptive computational models of international politics. It is a
working research repository, not a library: the interfaces will change, and the
results above are staged toward a paper rather than finished.
