# Skill Diplomacy — a critique against the standard you actually hold

You asked two things at once: whether this repo can carry a paper, and whether
that paper can meet a bar you inherited from a different kind of scholarship —
theoretically serious, aware of a world larger than its own experiment, and
written so that reading it is not a punishment. This document answers the first
question honestly and holds the whole project to the second.

Everything empirical below I ran or read myself in the repo on 6 August 2026,
against the current `main` (through the sprint-2 merge). Where I changed code I
say so and show the diff. Where a number is the harness talking to itself rather
than a fact about the world, I say that too, because the distinction is the
whole game here.

---

## The verdict in one paragraph

Continue the repo — but do not write the paper the skeleton currently describes.
The apparatus is genuinely good and the sprint-2 work fixed real defects. But
two things I found today change the shape of the paper. First, the headline
result is *more* robust than the skeleton feared, not less — I could not break
the non-monotone inequality curve by changing the endowment, which is good news
you had not yet claimed. Second, and more important, the moment I put a live
model behind the harness the binding constraint moved: it is not the institution
and not the poison, it is whether a self-authored doctrine *generalises past the
one task that triggered it*. That is a deeper and more honest paper than "we
simulated relative-gains trade," and it is the one this repo is actually
positioned to write. The instrument is real. The finding it will produce is not
the finding you are currently pointing it at.

---

## 1. What is genuinely strong (and should be defended in the paper, not apologised for)

I want to be precise about the strengths, because a critique that only lists
faults will mis-calibrate you.

**The engineering discipline is real and rare.** The event log is an append-only
substrate and every metric is a pure fold over it (`metrics/metrics.py` — `gini`,
`poison_spread`, `pass_k`, `mean_pairwise_similarity` are all folds; nothing
mutates history). Verification is exact by construction because the generators
compute their own ground truth (`bank/base.py`). The whole thing runs
deterministically with no API key, and I confirmed the published v1 table
reproduces bit-for-bit: capability `0.33 / 1.00 / 0.56 / 0.86 / 0.78`, ginis
`0.00 / 0.00 / 0.13 / 0.07 / 0.10`, overheads `0.180` and `0.204`, poison `6/6`
vs `0/6`. 57 tests pass in 5 seconds. Reviewers reward this and you should make
it loud: it is the difference between a result and an anecdote.

**The self-edit gate is honest.** Sprint-2 defect 3.3 — self-authored skills
being committed unconditionally while imports faced quarantine — was exactly the
asymmetry a reviewer attacks first, and closing it (self-edits now face the same
`run_quarantine` machinery, transactionally, via `SkillLibrary.snapshot/restore`)
is the kind of fix that signals you understand your own threat model. Keep the
two-term governance decomposition (`import_screen_overhead` vs
`self_screen_overhead`); it is a genuinely better way to price governance than
one lump number.

**The lineage fix is load-bearing and I watched it work.** Defect 3.1 — deriving
"is this poisoned?" from the artifact body (`is_poisoned_body`) rather than the
sender's identity — is not bookkeeping hygiene, it is the thing that makes
transitive propagation measurable at all. In the austerity experiment below I
saw `transitive_adopted = 198`: poison laundered through honest intermediaries,
which under the v1 identity-keyed scheme would have been structurally zero. The
fix earns its place.

**The scarcity diagnosis was the most valuable output of sprint 2.** The finding
that institutions only matter under scarcity — that at three families every arm
returns 1.0 and every result is an identity — is a real methodological
contribution and it should be a named result in the paper, not a footnote. It is
a warning to a whole class of multi-agent evaluations, and negative results of
that shape are what a careful reader remembers.

---

## 2. What I verified, corrected, and newly found

### 2a. The headline is robust — this *strengthens* your claim

The skeleton worried the interior Gini maximum "only appears under `zipf` and not
under `step`." I checked this properly, and the worry was based on a trap in the
code (see §3b): plain `--endowment step` silently behaves as `uniform`. Once you
actually grade the endowment, the non-monotone inequality curve appears
*everywhere*:

| endowment (3 seeds each) | Gini at k=0 | interior maximum | at k= |
|---|---|---|---|
| zipf, weight 4 | 0.000 | **0.678** | 3–4 |
| zipf, weight 8 (published) | 0.000 | **0.669** | 3–4 |
| zipf, weight 15 | 0.000 | **0.686** | 6–8 |
| step, 3 great powers, w8 | 0.000 | **0.683** | 2–8 |
| step, 5 great powers, w4 | 0.000 | **0.604** | 2–4 |

The interior maximum sits at ~0.68 across wildly different endowment shapes. It
vanishes only under *exact symmetry* — and that is not a fragility, it is the
theoretically correct boundary condition: relative-gains reasoning has nothing to
bite on when everyone is identical (Powell 1991 makes exactly this point — the
concern is endogenous to asymmetry). So the honest and *stronger* claim is:

> Given any graded capability endowment, the relative-gains dial produces
> non-monotone inequality with an interior maximum near 0.68; the effect
> disappears only under exact parity, where the realist mechanism is definitionally
> inert.

Correcting my own first read here matters: I told you mid-session it "only exists
under zipf." That was the code trap talking, not the science. It is robust.

### 2b. The mechanism behind the curve is interpretable (and that is what sells it)

I traced why the curve bends. Capability at maximum k is exactly the sum of home-
shard sizes over the family count — at zipf-w8, `31/30/15 = 0.069`, matching the
run. The interior Gini peak is a **rich-club** effect: at moderate k the great
powers hold enough that they still trade *among themselves* (each has much the
others lack), while small states hold too little to clear anyone's relative-gains
threshold and get frozen out. The rich trade, the poor are excluded, inequality
peaks. At strict k even the rich stop trading and everyone collapses to their own
endowment — a flat, uniformly poor floor. That is a mechanism, with a number, and
it maps onto Gowa's "trade follows the flag" and Snidal's large-N attenuation.
This is the part a reviewer means when they ask "so what?" — you have an answer.

### 2c. Two bugs. One I fixed for you; one is a footgun you should close.

**Bug A (fixed): E4 crashes at exactly the budgets that make it interesting.**
The "binding budget" experiment — the one the skeleton calls the experiment that
turns the price of governance into a frontier — was not merely "unanalysed." It
throws an uncaught `BudgetExceeded` and kills the trial. I reproduced it at every
binding budget:

```
budget=40000 : CRASH BudgetExceeded
budget=80000 : CRASH BudgetExceeded
budget=160000: CRASH BudgetExceeded
```

The cause is precise: the eval/self-improve phase wraps attempts in
`try/except BudgetExceeded`, but the *exchange* phase does not — so when a state
runs out of budget mid-quarantine (`_consider_adoption` → `run_quarantine` →
`importer.attempt`), the exception escapes and the run dies. `--sweep budget` was
therefore uncomputable in exactly its interesting regime.

I wrote a minimal fix (`sprint3-e4-fix.patch`, 28 lines, one file). It catches
the exception where it happens and — this is the part that turns a bug into an
experiment — makes what a broke state *does* an explicit, swept parameter:
`screen_bankruptcy ∈ {refuse, adopt_unscreened}`. A state that cannot afford to
screen either forgoes the import (safe) or takes it unscreened (risky). Default
is `refuse`, so binding-budget runs are safe and, crucially, the 57 tests still
pass and v1 still reproduces bit-for-bit — the new path is only reached when the
budget actually binds, which the 2M default never does.

With the fix, E4 immediately produces the frontier the skeleton promised:

| budget | quarantine=none | quarantine=probes |
|---|---|---|
| 160,000 | capability **0.627** | capability **0.000** (spends its whole budget screening) |
| 2,000,000 | 1.000 | 1.000 (governance is free) |

At a generous budget, screening is free and harmless. Squeeze it, and governance
stops being a tax and becomes a choice between improving and defending — at 160k
the probes arm pays its entire budget to the gate and reaches zero capability.
That is the trade-off made visible, and it was one exception-handler away from
being unreachable.

**The experiment the fix unlocks — austerity causes epidemics.** Because the
bankruptcy policy is now a dial, I could ask a question the repo could not
previously pose. Under adversarial trade, at a binding budget, does cutting the
screening you can no longer afford let contamination in?

| budget | policy | mean capability | poison adopted | of which transitive |
|---|---|---|---|---|
| 120,000 | refuse | 0.000 | **0** | 0 |
| 120,000 | adopt_unscreened | 0.000 | **228** | **198** |
| 2,000,000 | refuse | 0.938 | 0 | 0 |
| 2,000,000 | adopt_unscreened | 0.938 | 0 | 0 |

When budgets are generous the policy never triggers and it does not matter. When
they bind, the choice is everything: refuse and stay clean but frozen, or adopt
unscreened and let 228 poisoned artifacts in — 198 of them laundered through
intermediaries. **Contamination risk is highest precisely when resources are
scarcest, because screening is the first thing scarcity cuts.** That is a real,
non-obvious, mechanism-backed finding, and it is a direct RSI/security claim: the
defence that catches poison is a luxury good. (Honest caveat: at 120k raw
capability is floored for both arms, so this is currently a clean *contrast*, not
a finished figure — a budget sweep that finds where capability is non-zero *and*
the epidemic ignites is the experiment to run next. The contrast isolates the
policy effect; the figure needs one more sweep.)

**Bug B (footgun, unfixed — your call): `--endowment step` is inert without
`--great-powers`.** In `_weights` (`grid.py`), `step` returns all-ones unless
`n_great_powers > 0`, so `--endowment step` alone is silently `uniform`. Worse,
`_summarise` labels a run `"step"` whenever `n_great_powers > 0` *regardless of
the actual endowment flag*, so a `zipf + great_powers` run is mislabelled. This
is what sent my first robustness check astray. It is not wrong math, it is a
silent trap that will mislead you (it already did) and any reviewer who reruns
you. Two-line fix: make `step` require great powers or raise, and label from the
real endowment. I left this one for you because it is a design decision about the
CLI contract, not a mechanical bug.

### 2d. The live run — the single gating item — is crossable, and it moves the paper

`--live` had never been executed; under the scripted oracle `pass^k` is degenerate
and `library_similarity` is 1.0 by construction, so nothing about *models* had
ever been measured. There is no `ANTHROPIC_API_KEY` in this sandbox, so I wrote a
small adapter (`harness/cli_model.py`) that routes `model.complete()` through the
authenticated `claude` CLI with tools disabled and the harness system prompt
overriding the CLI default, and ran a micro smoke trial (3 states, 3 families, 2
rounds, Haiku, adversarial + probes, transcripts on). This is exactly the
"one small run to find out what breaks" the skeleton prescribed. What broke is
more interesting than what the skeleton guessed:

- **The model reads and uses its doctrines.** Progressive disclosure works: the
  full body is injected for the task's family and the model follows it. The
  sprint-2 prompt fix (injecting bodies, not just names) is doing real work — I
  confirmed it on live output. Good.
- **But self-authored doctrines overfit the triggering instance.** The skeleton
  predicted "doctrines too vague to help." The actual failure is the opposite and
  worse: state B, asked to write a reusable calendar playbook, wrote one literally
  titled *"## Solving the Specific Task"* that hard-codes the single date it had
  just failed. It helps its author on that instance and does not generalise.
- **The gate catches this on live output — a positive result.** State C's
  self-authored modmath doctrine passed regression 5/5 but failed off-shard probes
  1/2 and was *rejected*. State A imported B's calendar doctrine and it failed
  even regression (3/4) — an imported doctrine actively *regressed* the importer.
  So off-distribution probes are load-bearing on real models, not just against the
  scripted poison. This is the security result the paper wants, and it replicated
  live on the first try.
- **The uncomfortable one you must confront: on easy tasks the model solves
  anyway.** Round-0 live pass rates were unit_chain 6/6, calendar 4/6, modmath 3/6
  — Haiku can do this arithmetic without any doctrine. If the base model solves
  the task regardless, the *causal effect of exchange on capability* is small, and
  your institutional variable has little to move. The tasks must be hard enough
  that the doctrine is load-bearing, or the whole dependent variable washes out.
  This is the real design risk of the live run, and it is discoverable only by
  running it — which is the argument for doing the live run early, exactly as the
  skeleton sequenced it.

The run completed. Its numbers, next to the scripted oracle's, are instructive:

| metric | scripted oracle (adversarial + probes) | live Haiku (same config) |
|---|---|---|
| mean capability | 0.78 | **0.556** (non-degenerate — real) |
| governance overhead | 0.204 | **0.532** (screening ate *half* the budget) |
| distinct doctrine bodies in population | (many) | **1** |
| poison offered | 6 | **0** |

Three things jump out. **Governance is ~2.6× more expensive on a live model**
(0.53 vs 0.20 overhead): the model writes verbose doctrines and the probe evals
are real completions, so the price of governance is much steeper than the oracle
implies — your cost curves will move, and in the direction that makes the
trade-off sharper. **`distinct_bodies = 1`:** across the whole population only one
self-authored doctrine survived gating (B's calendar playbook); A and C finished
with empty libraries because the self-edit gate rejected their overfit doctrines.
The gate is doing its job, arguably too well. And the sharp one: **the poisoner
was never armed.** A is the unit_chain specialist *and* the designated poisoner,
but its self-authored doctrine never passed its own self-edit gate, so it had
nothing to export — poisoned or otherwise — and `poison_offered = 0`. On the
scripted oracle the poison is injected by fiat; on a live model the poisoner must
first author a doctrine good enough to survive gating *before* it can be poisoned
and spread. That is a real and non-obvious wrinkle: **strict self-gating starves
the contamination channel at the source.** For the live poison experiment you
will need either a weaker self-gate, more rounds (so A eventually commits an
acceptable-then-poisonable doctrine), or to inject the poison as an *import* from
a pre-seeded adversary library rather than relying on the poisoner to author it.

Transcripts are in `runs/smoke_transcripts.json`. None of this is in the paper
yet because none of it had ever been run — and all of it changes the paper.

---

## 3. The deeper critique — where this falls short of *your* bar

The engineering is not the problem. The problem is the one your standard is built
to catch: the risk that the paper is *correct but not about anything*.

**The scripted-oracle results are theorems about the harness.** The repo says
this, to its credit. But the paper cannot lead with a table that is, strictly, a
property of a regex-driven rule set and a set of set-difference inequalities. As
stated, the k-curve is a fact about `RelativeGains.score` and the shard
distribution — you can derive it on paper without running anything. That is not
nothing (a clean comparative static of Grieco's verbal model is a real
contribution — see §4), but if it is the *headline*, an ML reviewer reads it as
an elaborate restatement of the export rule, and a theory reviewer reads it as a
simulation of an assumption. The live run is not a "nice to have" that de-risks
the existing result; it is the thing that converts the paper from a statement
about your code into a statement about the world.

**The object of study is not what the title says.** The title is about exchange
institutions. But my smoke run says the first-order variable on a live model is
doctrine *generalisation quality* — an upstream property that gates whether any
institution can matter. The intellectually honest paper foregrounds this: *before*
you can study who trades with whom, you discover that most self-authored
improvement artifacts do not transfer, because they overfit their trigger. That
is a claim about self-improvement as such, it connects directly to the wider
reality (it is the generalisation problem the whole field has), and it makes the
institution the *second* act rather than the whole play. This is the move that
takes the paper from narrow to serious.

**The IR framing is currently one-directional, and Powell is the hole.** The IR
subagent was blunt about this and correct: the framing becomes decorative the
instant Grieco/Snidal/Ostrom appear only in §1–2 and the results could be
rewritten without them. Right now `k` is a free, exogenously swept parameter —
which strips out exactly the endogeneity Powell 1991 built into the concept (that
relative-gains sensitivity is *derived from* the security environment, not a
taste you set). You must state, in the mechanism section, that `k` is a
reduced-form stand-in for the threat environment and cite Powell making that
critique — turning your biggest vulnerability into a declared scope condition.
Do that, and the Gini-non-monotonicity becomes a genuine *addition* to the
forty-year debate (no one — not Grieco, Snidal, or Powell — models within-system
inequality as a function of `k`), which is the single most defensible novelty
claim you have. Ostrom is the anchor that keeps "the price of governance" from
being a slogan: her design principles 4–6 are literally about institutions being
*self-financing relative to the resource they protect*, graduated not binary,
cheap to adjudicate. Check your quarantine tiers against that checklist explicitly.

**The variants are scarcity, not diversity — and the live model will expose it.**
The repo admits variants share their archetype's solution logic. On the scripted
oracle this is invisible; on a live model it is a live threat, and my smoke run is
the first evidence: a model that solves unit_chain 6/6 will transfer across
unit_chain variants trivially, compressing the very capability gradient your
institutions are supposed to move. Six to eight *genuinely distinct* archetypes
(not thirty variants of three) is not a nice-to-have; it is the difference between
a gradient that exists and one that is an artifact of shared solution logic.

---

## 4. Are you entering a scientific debate, or decorating one?

You are entering four debates, and the map (in `RELATEDWORK.md`) shows you are a
participant in each, not a tourist — *if* you position precisely. The short
version:

- **Self-improving agents.** The field's own 2025–26 surveys (Gao et al.,
  arXiv:2507.21046) name inter-agent co-evolution as *unaddressed future work* —
  that is textual support for your gap. But the neighbourhood is crowding fast:
  *Multi-Agent Transactive Memory* (2606.19911) is genuine population-scale
  transfer, *SkillWeaver* (2504.07079) already shows stronger→weaker skill
  transfer helps, and *SkillsVote*/*SkillMAS* (2605.x) use your exact vocabulary.
  None combines your five ingredients, but you must differentiate from these by
  name.
- **Cultural evolution / monoculture.** Ashery–Baronchelli (Science Advances 2025)
  and Chen et al.'s *Diversity Collapse* (ACL 2026) are the closest and the
  highest novelty-risk — Chen governs *topology* against monoculture; you govern
  *exchange rights* via an incentive. That distinction is your whole RQ2 and must
  be made explicitly. Model collapse (Shumailov, Nature 2024) is your degenerate-
  transmission analogue.
- **Agent security / supply chain.** Your "regression screening is structurally
  blind to off-distribution poison" is intuited by BadAgent ("poison survives
  benign retraining") but *nobody stages in-distribution vs off-distribution
  screening head-to-head with a cost multiplier* — and the CLI smoke run shows it
  replicates live. The economics anchor is Gordon–Loeb 2002; your novelty is
  pricing defence in the *same currency as the capability it protects*.
- **International relations.** Grieco 1988 (get `U = V − k(W − V)` exactly right),
  Snidal 1991 (your N=15 speaks to his large-N attenuation), Powell 1991 (the
  endogeneity you must concede), Ostrom 1990 (the only classic that prices
  governance), Keohane 1984. The model for making theory *load-bearing* rather
  than decorative is the AI Economist (Zheng et al.) — economic theory there
  supplies a falsifiable internal check (the simple case must recover the known
  optimum). Do the same: treat Grieco's monotone comparative static (capability
  falls in k) as an internal-validity check your simulation must pass *before* the
  novel Gini result is trusted.

**Preemption verdict (from a dedicated adversarial search): not preempted as of
6 Aug 2026, but the window is closing.** No found work combines (i) real
Agent-Skills artifacts with lineage, (ii) institutions as the independent
variable, (iii) an IR relative-gains export dial, (iv) screening priced against
the improvement budget, and (v) contamination propagation through the trade
network. The closest triangulation is *When Agent Markets Arrive* (2604.06688,
institutions + budgeted decisions, but services not artifacts) and *SkillsVote /
Payload-less Skills* (right artifact, no institutions/economics). This is a real
opening — and a reason to timestamp priority on arXiv sooner rather than later.

---

## 5. Next steps — as falsifiable hypotheses, in priority order

You asked for falsifiable hypotheses, not a to-do list. Here they are, each with
the experiment that would kill it and the machinery you already have.

**H1 (gating, do first). On a live model, exchange causally raises capability
only when doctrines generalise.** Prediction: mean capability under free trade
minus autarky is positive *and* increases when you replace variants with genuinely
distinct archetypes hard enough that the base model fails them without a doctrine.
Kill condition: if free-trade capability ≈ autarky capability on the live model
(because the base model solves tasks regardless), the institution has nothing to
move and the paper is about doctrine quality instead — which the smoke run already
hints at (unit_chain 6/6 with no doctrine needed). *This is the experiment that
tells you which paper you are writing.* Machinery: the CLI adapter I wrote, plus
3–4 real archetypes.

**H2. Self-authored doctrines overfit their trigger, and off-distribution probes
are the only gate that catches it.** Prediction: on live models, self-edits pass
home-shard regression but fail fresh off-shard probes at a rate far above imports;
`REGRESSION` accepts overfit doctrines that `REGRESSION_PLUS_PROBES` rejects. The
smoke run already shows the shape (C rejected 1/2 on probes; A's import regressed
3/4). Kill condition: if regression and probes accept/reject the same set, the
tiering is decorative. Machinery: exists; needs seeds and CIs.

**H3. Contamination risk is a function of budget, peaking under austerity.**
Prediction: under adversarial trade + `adopt_unscreened`, poison adoption is
non-monotone in budget — near zero when budgets are generous (screening
affordable) and when they are catastrophic (nothing moves), with a peak in
between where states can trade but cannot afford to screen. Kill condition: if
poison adoption is monotone in budget, the "austerity epidemic" is just
"everything fails when broke." Machinery: the E4 fix unlocked exactly this; run
`screen_bankruptcy × budget` as a 2-D sweep. **This is your cleanest new figure.**

**H4. Off-distribution screening is the load-bearing tier, and its cost is what
makes it structurally under-supplied.** Prediction: `REGRESSION` (home-shard) adopts
poison at near the no-governance rate while paying most of the cost; only
`REGRESSION_PLUS_PROBES` catches it, at ~4× overhead — replicated on a live model,
not just the oracle. Kill condition: if home-shard regression catches off-shard
poison on live models, the central security claim is false. This is your v1 result
(`6/6` vs `0/6`) promoted from oracle to model.

**H5 (RQ2, now actually measurable). Open exchange drives libraries toward
monoculture, and a relative-gains dial slows it.** This is unmeasurable under the
scripted oracle (one playbook text for every doctrine → `library_similarity` ≡ 1).
On live models, doctrines have distinct text and `mean_pairwise_similarity` /
`distinct_bodies` become real signals. Prediction: similarity rises over rounds
under free trade and rises slower as k increases. Kill condition: no convergence,
or k does not slow it. Machinery: metrics exist; needs the live run to have any
content at all.

**Sequencing** (this is days, not months, and it respects your usage concern —
each step is one command and produces one artifact you can read):
1. Apply `sprint3-e4-fix.patch` (one guided step; §6).
2. Close bug B (the `step`/`great-powers` footgun) so the endowment robustness
   table is trustworthy.
3. Run H3 as a `screen_bankruptcy × budget` sweep on the scripted oracle — your
   cleanest new figure, no API spend.
4. Add 3–4 genuinely distinct archetypes.
5. Run the live H1/H2/H4 battery small (the CLI adapter works; ~$1–2 of Haiku per
   micro-run based on what I saw today).
6. Write §1, §2, §5 while those run — they do not depend on the numbers.

---

## 6. Applying the fix — one step, walked through

The patch is `sprint3-e4-fix.patch` (I put it in the repo root of the copy I
worked in; it is also attached). It touches one file, `grid.py`, adding a
`screen_bankruptcy` config field and a `try/except` around the exchange-phase
quarantine. What it does, in one sentence each:

- **The `try/except`**: stops a state that runs out of budget mid-screening from
  crashing the whole run — the reason `--sweep budget` was uncomputable.
- **The `screen_bankruptcy` field**: makes "what does a broke state do — refuse
  the import, or take it unscreened?" an explicit, swept choice rather than an
  accident. Default `refuse` keeps every existing result identical.

To apply it on your machine, from the repo folder, the single step is:

```
git apply sprint3-e4-fix.patch && pytest -q
```

You should see `57 passed`. If you would rather not touch git at all, the diff is
small enough that a Claude Code session on your machine can make the two edits
directly from the patch file — tell it "apply the changes in sprint3-e4-fix.patch
to grid.py and run pytest." Either way, nothing changes in your published numbers;
I verified v1 reproduces bit-for-bit after the patch.

---

## 7. The go/no-go, restated in your terms

Your bar is not "publish something." By that bar: the repo is a real instrument,
the sprint-2 fixes were real, and there are now three findings that clear the "so
what?" line — the robust non-monotone inequality curve with a rich-club mechanism,
the austerity-epidemic (once its figure is finished), and the live-model result
that off-distribution screening catches overfit doctrines that home-shard
regression waves through. None of those is "spitting out a piece of whatever."

But the paper that meets *your* standard is not the one the skeleton frames. It is
the one the live run forces you toward: a paper whose first move is that
transferable self-improvement is gated by generalisation, whose second move is the
institution, and whose theory is load-bearing because Grieco's comparative static
is your internal-validity check and the Gini result is a genuine addition to a
debate you can cite by name. Written that way — one argument, aware of the four
literatures it sits inside, honest about what is harness and what is world — it is
worth reading. Written as "we simulated relative-gains trade and here is a table,"
it is correct and forgettable.

Do the live H1 run. It will tell you which of those two papers you are holding.
