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

### E3. One load-bearing archetype · **won't fix here**

`lexicon` is the only family with non-zero lift, and its variants share solution
logic. Every live institutional result rests on one archetype. `README.md`
already declares this.

### E4. The saboteur is scripted, not adaptive · **won't fix here**

Declared in `README.md`. In evolutionary computation a non-evolving adversary is
a static red-team probe, not coevolution, and Zaman et al. (2014) is the
standard this departure has to answer to.

---

## Summary

| | closed | open | won't fix |
|---|---|---|---|
| A. measurement | 3 | 0 | 0 |
| B. silent failure | 4 | 0 | 0 |
| C. provenance | 2 | 2 | 0 |
| D. claims | 5 | 0 | 0 |
| E. design | 0 | 0 | 4 |

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
