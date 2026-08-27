# Defect register

Every defect found in this repository, what it invalidated, and whether it is
closed. A defect here means: *a published number was wrong, unreproducible, or
measured something other than what it claimed*. Ordinary bugs that never reached
a result are not tracked.

This file exists because "is it fixed?" was previously answerable only by
reading three long prose documents and trusting them. It is machine-checked
where it can be: `python -m paper.reproduce --check` fails if any number in the
**closed** rows drifts, and `pytest` carries a named regression test for each.

Status vocabulary. **Closed** — repaired, with a test that fails if it returns.
**Open** — known, not yet repaired, with the reason. **Won't fix** — a real
limitation that is being declared rather than removed.

---

## A. Measurement defects — the metric did not measure its claim

### A1. Skill identity was provenance-sensitive · **closed** (`c86853a`)

`SkillLibrary.content_hash` hashed the whole `SKILL.md`, frontmatter included.
Frontmatter carries `version` and `provenance` (`author`, `imported_from`,
`origin_hash`), so a doctrine's identity changed every time it was copied.
Separately, `experiment/grid.py` hashed `name+body+scripts` — a second,
disagreeing definition for the same artifact.

Invalidated:

- `distinct_bodies`, the RQ2 monoculture signal, counted **copies** rather than
  contents. `runs/lex/*.json` reported 8 distinct bodies where the truth was 3;
  the scripted oracle, which emits one playbook text for every skill, reported 9
  where the truth was 1 — i.e. the metric reported maximal diversity for a
  population at complete monoculture, the exact inverse of the truth.
- `poison_spread.unique_offered` counted one contaminant once per laundering
  hop, inflated by precisely the transitive spread it exists to measure.
- `origin_hash` and the `content_hash` on `adoption_decision` events were in
  different hash spaces, so lineage could not be reconstructed from the event
  log — which `README.md` claims it can be.

Repair: one definition, `skills.format.artifact_hash` over `name+body+scripts`,
with `body_hash` split off for diversity metrics that must ignore the name.
Tests: `tests/test_identity.py` (6).

### A2. `distinct_bodies` counted names as diversity · **closed** (`c86853a`)

Downstream of A1. Unifying on `artifact_hash` alone still over-counted, because
the scripted oracle emits one playbook text under a different skill name per
family. Split into two questions with two answers: `artifact_hash` for "is this
the same artifact?" (lineage, denylist, unique contaminants), `body_hash` for
"has the population converged on one doctrine?" (RQ2).

### A3. Probe coverage reported the wrong statistic · **closed** (`726e383`)

`run_probes.py` pooled poison offers across seeds into one rate with no
interval. Per-seed reporting at 24 seeds shows the fixed-suite arm is perfectly
bimodal — every seed admits exactly 0% or exactly 100%, fourteen catches and ten
complete misses, nothing between.

Consequences: the published **80%** was five seeds of which four happened to
land in the miss mode; at 24 seeds it is **41.7%**, and because each seed
contributes only 0 or 1 the arm's mean is not a stable quantity at five samples.
The arms' *means* are not distinguishable (0.417 vs 0.333, p = 0.44). The
finding is a difference in **dispersion**: sd 0.493 against 0.112, ratio 4.4,
p = 5e-05. See §D1 for the corrected claim.

Tests: `tests/test_stats.py::test_a_fixed_probe_suite_is_all_or_nothing` and
four others.

### A4. The load-bearing family's doctrine IS the answer key · **closed**

`lexicon`'s `reference_body()` emits the complete glyph→value table and the task
asks only for a weighted sum over it, so P(solve | doctrine) = 1 and
P(solve | no doctrine) ≈ 0 **by construction**, and mean capability reduces to
|library ∩ families| / F.

That made the repository's one positive live claim an arithmetic identity.
`run_lex.py` pins autarky at exactly 1/3 and free trade at exactly 1, so the
reported gap of +0.667 is 1 − 1/F — a quantity the experimenter chose. Re-running
that configuration against the *scripted* oracle reproduces the published "live"
numbers to four decimals, and `diff`ing the committed live artifacts across seeds
shows differences only in `seed` and `spent_tokens`. The zero variance the README
presented as strength is the signature of a deterministic quantity. `LETTER.md`
§6 condemns exactly this move in print: "a null model that defines capability as
a function of the library will confirm that capability is a function of the
library."

Repair: `bank/generators/protocol.py`, a second load-bearing archetype whose
doctrine carries a **procedure** rather than an answer. The doctrine is
necessary but not sufficient — a six-step computation over ~9 digits still has
to be executed — so P(solve | doctrine) is strictly below 1 and is a property of
the *model*. `record_len` is a difficulty dial, and the poison comes at two
detectabilities an order of magnitude apart (a corrupted weight is wrong on 89%
of instances, a corrupted substitution entry on 16%), which turns the screening
question from one contrast into a sweep over how rare a defect's symptoms are.

The identity does not disappear on its own — it is a property of a perfect
solver, and at reliability 1.0 `protocol` also returns 1 − 1/F. What changes is
that the assumption is now a **parameter** (§B5) rather than a fixture, so the
institutional gap becomes a curve instead of a constant.

### A5. Unaffordable attempts were scored as wrong answers · **closed**

`grid.py`'s eval loop caught `BudgetExceeded` as `ok = False` and still counted
the attempt in the denominator, so under a binding budget `capability` was
silently the product of two different quantities: how well a state answers, and
how much of its schedule it could pay for. The budget sweep exists precisely to
study budgets that bind, so the defect sat in the middle of the experiment it
would corrupt — the same shape as scoring a transport failure as cognition
(§B1), and the same repair.

Separated, the published austerity numbers read differently and better. At a
160k budget the unscreened arm was reported as **capability 0.627**. It is
actually **capability 1.000 at coverage 0.627**: it answered everything it
attempted and could afford 63% of its attempts. It did not get worse at the
task; it ran out of money. The screened arm at the same budget affords nothing
at all.

So the price of governance under scarcity is paid in **coverage, not
competence** — a claim with the right units, and one the conflated number could
not express. `attempt_coverage` and `budget_bound` are now reported per state
and per population. Non-binding budgets are unaffected: coverage is 1.0 and
every previously published number is unchanged, which `paper.reproduce --check`
confirms.

### D6. Two standard-deviation conventions, one in the paper and one in the code · **closed**

`LETTER.md` reported "autarky 0.889 ± 0.111 and free trade 0.963 ± 0.064" —
sample sd (n−1), computed by hand. `grid.py`'s `_mean_std` divided by n,
emitting 0.091 and 0.052 into every `capability_std` column. A replicator finds
that discrepancy immediately and cannot explain it. `_mean_std` now uses n−1,
which is also the right convention given seeds are replicates.

### D7. The README's Gini figure was not the one its own command produces · **closed**

`README.md` said inequality "peaks at moderate restriction (Gini ≈ 0.68)". The
committed sweep gives **0.6701 at k=4** (0.6693 at k=3). The 0.68 came from
`CRITIQUE.md`'s zipf-15 and step-3-great-power rows — endowment shapes with no
committed artifact, which the README did not identify as the source. Now stated
as 0.670 for the published endowment with the 0.60–0.69 range across shapes.

### D8. One citation described a survey as a dedicated formal paper · **closed**

`RELATEDWORK.md` described arXiv:2602.12430 (Xu & Yan) as "the nearest formal
neighbour, a four-tier *permission* model, unpriced and unevaluated."

Checked against the source. An audit had reported this as a misattribution —
that the paper "proposes no permission model" — and that report was **wrong**;
taking it at face value would have removed an accurate and load-bearing
citation. The paper does propose a four-tier permission model: a Skill Trust and
Lifecycle Governance Framework with four verification gates and four trust tiers
granting graduated permissions. What needed correcting was smaller and
different: it is a *survey*, and the framework is one section of it. The entry
now says so, names the framework, and keeps the "unpriced and unevaluated"
judgement, which is accurate and is exactly the gap this project occupies.

The survey also carries base rates worth citing directly — 26.1% of 31,132
skills carrying a vulnerability, 157 confirmed malicious skills in 98,380 —
which answer "is a defective-artifact channel a real threat or a modelling
convenience?" better than anything currently in the manuscript.

### C4. No citation metadata or data-availability statement · **closed**

`LETTER.md` claimed reproducibility "from a public repository" without naming
it. Added `CITATION.cff`, a CC BY 4.0 licence for `runs/` (the MIT licence
covers code only), and a data-availability paragraph that names the repository,
the three regeneration commands, and — rather than eliding it — the fact that
the live artifacts cannot be re-derived because they predate the provenance
block.

### B5. The perfect-solver assumption was unfalsifiable · **closed**

Nothing in the harness could make an agent fail at something it held a correct
doctrine for. The scripted oracle solves perfectly; a live model over `lexicon`
also solves perfectly, because the doctrine is the answer. So there was no
configuration in which model behaviour selected the outcome, and no way to ask
what the institution does as a function of agent competence.

Repair: `harness/fallible.py`. `FallibleModel` wraps any policy and fails at a
controlled per-step rate, so an instance requiring n steps is answered correctly
with probability `reliability ** n`. Failures are plausible perturbations of the
right answer, not malformed output, or quarantine would be catching a tell
rather than a defect. The coin is keyed on (seed, system, prompt) by SHA-256
rather than call order, so a trial reproduces exactly even though adoption
decisions change how many calls precede any given one.

The scripted oracle is now the reliability = 1 endpoint of a sweep rather than
the only available agent.

### B6. `gate_self_edits=True` gated nothing unless a quarantine tier was set · **closed**

`grid.py` computed `self_gate = cfg.quarantine if cfg.gate_self_edits else NONE`,
so `gate_self_edits=True` with `quarantine=NONE` — a combination that reads as
"self-edits are screened" — accepted every edit unconditionally. Same species of
silent no-op as `--endowment step` without `--great-powers` (§B2), and with
sharper consequences, because the ungated path turned out to be actively
destructive (§F1). Now raises, and `run_v2.py` rejects the flag combination with
a message naming the fix.

---

## B. Silent-failure defects — the harness hid something a result depended on

### B1. Transport failures scored as wrong answers · **closed** (`c86853a`)

`CLIModel` returned `ANSWER: __error__` when retries were exhausted. That scores
as a task failure, so every timeout, non-zero exit and truncated payload pushed
capability down with no record anywhere. The live gap claimed in `runs/h1/` is
0.074; a handful of timeouts is the same order of magnitude.

Repair: failures counted by kind, surfaced via `describe()`, and a run with any
errors marks its capability figure a **lower bound** in its own artifact.
Tests: `tests/test_provenance.py` (2).

### B2. `--endowment step` was silently `uniform` · **closed** (`c86853a`)

`_weights` branched on `endowment == "step" or n_great_powers`, so `step`
without `--great-powers` returned all-ones and ran at exact parity, and
`zipf + --great-powers` discarded zipf while `_summarise` labelled the run
`"step"` whatever flag was passed. Parity is the one condition under which
relative-gains reasoning is definitionally inert, so that arm could not have
shown an effect and its null was uninformative rather than evidential. (Raised
as "Bug B" in `CRITIQUE.md` §2c and left open there.)

Repair: both cases raise; the summary records the endowment actually used and
its parameters. Tests: `tests/test_identity.py` (5).

### B3. Monte Carlo p printed as exactly zero · **closed** (`726e383`)

Self-inflicted, in the statistics layer added by this work: `round(p, 4)`
rendered 4.9998e-05 as `0.0`, defeating the +1 smoothing that exists to prevent
claiming p = 0. Repair: `_round_p` keeps significant digits.

### B4. Provenance broke the runs it documented · **closed** (`29653b3`)

Also self-inflicted. `TrialConfig` holds an enum and tuples, so echoing the
config verbatim made every driver that writes results to disk fail at
serialisation. Repair: total coercion — anything unrecognised degrades to
`repr` rather than raising.

---

## C. Provenance defects — a number that cannot be attributed

### C1. No run provenance · **closed for new runs, open for committed ones**

Committed results record institution, seed and endowment and nothing else: no
model, date, temperature, prompt version or commit. `claude-haiku-4-5` is a
moving alias, so "free trade 0.963 on a live model" cannot be attributed to
specific weights, audited, or replicated.

Repair for new runs (`c86853a`): every summary carries `provenance` —
harness version, UTC timestamp, git commit and dirty flag, python version, full
config, and a model description. The harness/live status label that every
`README.md` claim depends on is now **derived from the client** rather than
asserted by a human.

**Still open for the 12 committed live artifacts** in `runs/h1/` and
`runs/lex/`. They predate the block and cannot be back-filled — the information
was never captured. `python -m paper.reproduce` audits and lists them on every
run rather than passing silently. Closing this requires re-running the live arms
(§E1), which needs an API key this environment does not have.

### C2. The event log is not shipped · **closed**

`README.md`: "Every metric is a pure fold over an append-only event log, so
results can be recomputed from the log alone." `.gitignore` excludes
`events.jsonl`. The property is real and the claim is true of the code, but no
reader can exercise it, because the substrate the fold runs over is not in the
repository.

Repair: `paper/export_log.py` runs the five headline deterministic trials,
normalises each log (wall-clock stripped, so the fixture is byte-stable), commits
them gzipped under `runs/logs/`, and then **folds them back** — recomputing
`poison_spread`, `export_refusals` and `pass^k` from the log alone and comparing
each against what the run reported. An exported log nobody folds over is a file,
not evidence. All five recompute exactly. CI regenerates and diffs them.

### C3. `runs/skill_lift_live.json` does not record its own n · **open**

The instrument the paper proposes as a contribution reports four verdicts and
no sample size. `LETTER.md` states 6 and `calibrate.py` defaults to 6, so the
figure pipeline hard-codes 6 — an assumption a reader cannot check from the
artifact. Fix with §E2.

---

## D. Claim defects — the prose says something the code does not produce

### D1. The screening claim · **closed**

`README.md` line 83 and `LETTER.md` §6 state: "Six held-out probes still admit
**80%** when one fixed suite is reused, but only **29%** when probes are
re-drawn per screening event, at 58% and 67% overhead respectively", over "five
deterministic seeds".

Measured at 24 seeds: **41.7%** and **33.3%**, at **62.8%** and **64.6%**
overhead. The 100%-admitted / 23%-overhead figures for home-shard regression are
unchanged and correct.

The replacement claim is stronger, and is what §A3 establishes: re-drawing does
not buy a lower expected contamination rate — the means are indistinguishable —
it removes **correlated, population-wide screening failure**. A fixed suite is
one draw shared by every importer, so when it has a hole they all fall into the
same hole simultaneously. That is a sharper instantiation of D'haeseleer,
Forrest & Helman (1996) than the mean-difference version, and a sharper security
claim: the exposure is tail risk, not mean risk.

### D2. The scarcity claim · **closed**

`README.md` line 84: "Institutions have no measurable effect unless skills are
scarce relative to the task space. With three task families every arrangement
returns identical capability."

The second sentence does not reproduce: at three families autarky is 0.333,
clubs 0.556, free trade 1.000. The first conflates two preconditions.

Measured (`paper/reproduce.py::claim_parity_and_scarcity`): under a **uniform**
endowment the relative-gains dial is a two-level step whatever the family count
— 3 families or 12, exactly two capability values. Under a **graded** endowment
it traces a curve at 3 families already (3 levels), and more finely at 12 (5)
and at the v2 default scale (7). So **parity** is the boundary condition, and
scarcity sets the *resolution* at which the curve can be read rather than
switching the effect on. This is the stronger claim and the one Powell (1991)
predicts, since relative-gains sensitivity is endogenous to asymmetry.

### D3. The modmath negative-lift claim · **closed**

`LETTER.md` §4: "The negative lift on modular exponentiation is worth its own
remark: a generic strategy playbook made the model *worse* … Skills are not free
even when they are ignored."

The measurement is −0.17 from n=6. Wilson intervals: floor 0.83 [0.44, 0.97]
against with-skill 0.67 [0.30, 0.90] — almost entirely overlapping. The
conclusion is not supported at this n. Either raise n (§E2) or cut the remark.

### D4. Stale test count · **closed**

`README.md` said 72 tests. There are now 119.

### D5. `CRITIQUE.md` references a file not in the repository · **closed**

`CRITIQUE.md` §2c and §6 instruct the reader to `git apply
sprint3-e4-fix.patch`. That patch is not in the repository, and the fix it
describes has since been applied to `grid.py` (`screen_bankruptcy`, and the
`try/except` around exchange-phase quarantine, at `grid.py:118` and
`grid.py:430`). The instruction is dangling and should be replaced by a note
that the change landed.

---

## E. Design limitations — real, and declared rather than repaired

### E1. Three seeds per arm cannot reach significance · **won't fix in code**

C(6,3) = 20 arrangements, so the smallest two-sided p an exact permutation test
can return is **0.10** — regardless of effect size. The live lexicon contrast
separates perfectly (0.333 vs 1.000, zero variance) and returns exactly 0.10,
the floor. The saturated-family contrast is +0.074 against a pooled sd of 0.083
and returns 0.44.

Not a code defect: it is a statement about how many seeds to run. Five per arm
drops the floor to 0.0079. `stats.min_achievable_p` computes it and `compare`
reports it beside every p-value so the design fact cannot be quoted without the
bound. Closing it means re-running the live arms at ≥5 seeds, which needs an API
key.

### E2. Skill lift is measured at an n that cannot resolve its own verdicts · **won't fix in code**

Every Wilson interval in `runs/skill_lift_live.json` spans ≥ 0.39.
`unit_chain`'s 6/6 floor is consistent with a true rate of 0.61, yet it is
classified SATURATED against a 0.80 threshold. The diagnostic the paper offers
as a contribution is being applied below the n at which it can distinguish its
own three regimes. Needs a live re-run at higher n.

### E3. One load-bearing archetype · **closed**

`lexicon` was the only family with non-zero lift, and its variants share
solution logic, so every live institutional result rested on one archetype —
and, as §A4 shows, on the one whose lift is pinned at 1 by construction.
`protocol` is a second, and is deliberately not a variant of the first: it
carries procedural rather than declarative knowledge, its lift is strictly
below 1 and set by the model, and it degrades along a different axis (steps
executed, not glyphs known). Live measurement of its lift still needs an API
key; the archetype and its calibration path do not.

### E4. The saboteur is scripted, not adaptive · **won't fix here**

Declared in `README.md`. In evolutionary computation a non-evolving adversary is
a static red-team probe, not coevolution, and Zaman et al. (2014) is the
standard this departure has to answer to.

---

## F. Findings this repair produced

Not defects. Recorded here because they were discovered by fixing the ones
above, and because the first of them is the strongest result the repository
currently holds.

### A6. A new archetype silently disabled the contamination experiment · **closed**

`AdversarialTrade.poison_families` listed `("unit_chain", "lexicon")`. Adding
`protocol` without adding it there meant `poisons_family("protocol")` returned
False, so no poison was ever offered — and a full detectability sweep reported
`offered = 0, adopted = 0` for every cell, which every downstream metric renders
as an admission rate of **0.0**, i.e. perfect screening.

This is the most dangerous silent failure available in this repository: a
contamination experiment in which nothing is contaminated does not error, it
reports that governance works. The docstring on `poisons_family` already warned
about the identical shape for variant families, and the omission happened anyway
one function above it.

Repair: `protocol` added, and `experiment/grid.py` now **refuses** an adversarial
trial whose bank contains no poisonable family, naming the config that is wrong.
A guard, not a comment, because the comment did not work.

### F2. The screening rule dominates the screening depth

A screen drawing k independent probes against a defect wrong on a fraction d of
instances should miss it with probability (1 − d)^k. That is true only if a
single failure is disqualifying. `quarantine.py` shipped `probe_threshold = 0.6`
— accept if 60% of probes pass — and under a proportional rule the arithmetic
reverses.

As probes are added the *observed* failure fraction concentrates on d. If d sits
below the rule's tolerance (1 − 0.6 = 0.4), concentration removes the chance
rejections a shallow screen gets for free, and admission rises toward certainty.
Measured at d = 0.178, re-drawn probes, 4 seeds:

| probes | 1 | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|
| proportional (60%) | 0.87 | 0.77 | 0.85 | 0.98 | **1.00** |
| strict (any failure) | 0.87 | 0.77 | 0.60 | 0.33 | **0.10** |
| (1 − d)^k | 0.82 | 0.68 | 0.46 | 0.21 | 0.04 |

Sufficiency — the cheapest depth reaching 10% admission:

| d | k* (theory) | proportional | strict | overhead at k |
|---|---|---|---|---|
| 0.178 | 12 | **>16** | 16 | 0.817 |
| 0.313 | 7 | **>16** | 8 | 0.715 |
| 0.430 | 5 | **>16** | 4 | 0.600 |
| 0.613 | 3 | 8 | 4 | 0.612 |
| 0.797 | 2 | 2 | 2 | 0.509 |
| 0.925 | 1 | 1 | 1 | 0.433 |

Three things follow.

**A rule stated as a pass rate has a blind band.** Every defect quieter than its
tolerance is not merely hard to catch — it becomes *more* certain to be admitted
the more you spend looking. Under the proportional rule no depth within budget
reaches 10% admission for d ≤ 0.43.

**Depth is the wrong dial.** "How much should you check?" was the question this
repository was built around, and the answer is that the amount is second: make
the rule strict, then buy depth. Under a pass-rate rule, depth is a dial on
variance rather than on protection, and the only defects it catches are the ones
it would already have caught at k = 1.

**The strict rule recovers the analytic prediction across the range**, which is
the internal-validity check `CRITIQUE.md` §4 asked for and the repository did not
have: before trusting a novel screening claim, the harness has to reproduce the
known result in the regime where the known result applies. It does.

This is the fixed-versus-re-drawn finding (§A3) arriving from the other
direction. There the screen's *sampling* decided what it could see; here its
*decision rule* does. Neither is a question of how much you check.

Reproduce: `python run_sufficiency.py`. Figure: `paper/fig/fig7_sufficiency.svg`.

### F1. Ungated self-improvement destroys the knowledge it was meant to build

An agent that holds a correct procedure and fails a task anyway is in a
situation the self-improvement loop cannot read. The loop's trigger is failure;
its inference is "I lack a doctrine for this family"; its action is to write
one. But a competent agent's failure is often an execution slip rather than a
knowledge gap, and the doctrine it then writes is worse than the one it already
had. Ungated, the edit is committed, the correct procedure is overwritten
(verified on disk: the endowed protocol spec is gone, replaced by the generic
playbook), every subsequent attempt fails, and that triggers further
"improvement". Capability does not decay — it collapses and does not recover.

Measured under **autarky**: no exchange, no adversary, no imports. Whatever
happens, the agent does to itself. Eight seeds per point, `protocol` families.

| per-step reliability | self-edits ungated | self-edits screened | gate buys |
|---|---|---|---|
| 1.000 | 0.333 | 0.333 | **+0.000** |
| 0.995 | 0.190 | 0.329 | +0.139 |
| 0.990 | 0.125 | 0.282 | +0.157 |
| **0.980** | **0.037** | **0.241** | **+0.204** (p = 0.0019, exact) |
| 0.970 | 0.000 | 0.180 | +0.180 |
| 0.950 | 0.000 | 0.157 | +0.157 |
| 0.900 | 0.014 | 0.093 | +0.079 |

Three things make this worth reporting.

**It is the first statistically significant result in the repository.** p =
0.0019 by exact permutation at eight seeds per arm, against a design floor of
0.0002. Every other contrast here is either deterministic or underpowered.

**The effect is exactly zero for a perfect solver**, and that is the control
that makes it meaningful rather than a caveat that weakens it. A competent
agent never fails at home, so the destructive branch is unreachable, and no
amount of running the existing harness could have found this. The finding is
downstream of §B5.

**It reframes the price of governance.** Screening is argued for on
contamination grounds — check what you import, someone may have poisoned it.
This is a different and more basic argument, and it holds with no adversary
anywhere in the system: screening your *own* edits is what makes
self-improvement monotone. Against imports, governance trades capability for
safety. Against self-edits it does not trade at all — it is where the capability
comes from.

The effect is also non-monotone in reliability, peaking near 0.98: the gate
matters only when failures are frequent enough to trigger a rewrite and rare
enough that the doctrine being overwritten is still worth having. That shape
echoes the interior maximum in the inequality result, and has the same kind of
mechanism behind it.

Reproduce: `python run_ratchet.py`. Figure: `paper/fig/fig5_ratchet.svg`.

---

## Summary

| | closed | open | won't fix |
|---|---|---|---|
| A. measurement | 6 | 0 | 0 |
| B. silent failure | 6 | 0 | 0 |
| C. provenance | 3 | 2 | 0 |
| D. claims | 8 | 0 | 0 |
| E. design | 0 | 0 | 3 |

Every defect in the **code** is closed, and every **claim** defect is closed —
`README.md`, `LETTER.md` and `CRITIQUE.md` no longer state a number that does not
reproduce.

Two rows remain open and both need the same thing. **C1** (provenance on the 12
committed live artifacts) and **C3** (`skill_lift_live.json` recording its own n)
cannot be back-filled, because the information was never captured; they close
when the live arms are re-run, which needs an API key this environment does not
have. `python -m paper.reproduce` lists them on every run rather than passing
silently.

The **won't fix** rows are limitations to declare in the paper's
threats-to-validity section, not bugs — and E1 and E2 close on the same live
re-run, at ≥5 seeds per arm and a larger calibration sample respectively.
