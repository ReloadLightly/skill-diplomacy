# Skill Diplomacy — WP1 Harness (v2)

Experimental harness for **"Skill Diplomacy: Exchange Institutions for Co-Evolving
Self-Improving Agents"** (spec, July 2026), built to the ACTIR handoff brief
(2026-07-28). Pure Python, stdlib-only at runtime; `pytest` for tests;
`anthropic` optional for live runs.

## Quick start

```bash
pytest tests/ -q             # 57 tests: v0 units, v1 grid, v2 defect/scarcity/export suite
python run_v0.py             # scripted smoke run: autarky vs free trade, no API spend
python run_v1.py             # the v1 grid → runs/grid_summary.{json,csv} (no API spend)
python run_v2.py --sweep k   # the v2 headline: relative-gains dial → runs/v2_k.{json,csv}
python run_v2.py --sweep defectors    # free-rider sweep
python run_v2.py --live --model claude-haiku-4-5 --states 6 --variants 3 --rounds 2 --seeds 1
```

Smoke result (deterministic): under autarky each state masters only its home
family (final pass 0.4 / 0.6, Gini 0.1, zero adoptions); under free trade both
adopt the other's doctrine through quarantine and reach 1.0 (Gini 0.0) — at a
measured governance overhead of ~10% of budget. That is H1 + the price-of-
governance measurement, demonstrated in plumbing.

## Architecture (everything folds over the event log)

```
skill_diplomacy/
  harness/events.py        append-only JSONL event log (brief §4: the durable substrate)
  harness/budget.py        per-state b_t ceilings; quarantine sub-account → governance overhead
  harness/model.py         ModelClient protocol; ScriptedModel (tests) / AnthropicModel (live)
  bank/base.py             TaskInstance, ANSWER: convention, exact verify(), sharding
  bank/generators/         unit_chain (invented units), calendar_math, modmath
                           — parameterized, self-verifying, contamination-proof
  bank/variants.py         K variants per archetype → the scarcity dial (3*K families)
  institutions/exchange.py export policies: open / reciprocal / relative_gains / defector
  skills/format.py         Agent-Skills-compatible libraries (SKILL.md + scripts/),
                           provenance lineage, export/import, shingle Jaccard
  institutions/            Autarky / FreeTrade / Clubs / AdversarialTrade (+ poison_artifact)
  institutions/quarantine.py  NONE / REGRESSION / REGRESSION+PROBES → the price curve
  metrics/metrics.py       pass-rate trajectories (eval-phase only), pass^k, Gini,
                           adoption graph, poison spread
  state.py                 AgentState: attempt → improve_from_failure → commit;
                           'never again' regression store
  experiment/oracle.py     poison-aware scripted oracle (off-shard capability
                           actually degrades under a poisoned doctrine)
  experiment/grid.py       run_trial / run_grid / aggregate — the institution ×
                           quarantine × seed matrix with REAL quarantine sandboxing
run_v0.py                  2-state smoke experiment
run_v1.py                  v1 grid runner → runs/grid_summary.{json,csv}
run_v2.py                  v2 sweeps (k / defectors / institutions / budget), --live
tests/test_all.py          v0 units; INDEPENDENT recomputation of generator truth
tests/test_experiment.py   v1 grid: the orderings/mechanism the experiment shows
tests/test_sprint2.py      v2: the four defects, scarcity, endowments, export layer —
                           several assert a DIFFERENCE the mechanism's removal would erase
```

## The v1 result (deterministic ScriptedModel, 4×3×3 grid, no API spend)

```
institution         quarantine                cap    gini   gov_oh   poison_adopt
autarky             none/regression/probes    0.33   0.00   0.000    -
free_trade          none                      1.00   0.00   0.000    -
free_trade          regression                1.00   0.00   0.052    -
free_trade          regression_plus_probes    1.00   0.00   0.180    -
clubs               none/regression/probes    0.56   0.13   0.0–0.07 -
adversarial_trade   none                      0.86   0.07   0.000    6/6
adversarial_trade   regression                0.86   0.07   0.050    6/6
adversarial_trade   regression_plus_probes    0.78   0.10   0.204    0/6
```

Reading: institutions produce a real capability gradient (autarky 1/3 → clubs 0.56,
unequal → free trade 1.0). Governance is a **price curve** — overhead rises
monotonically none→regression→probes. The headline (`adversarial_trade`):
home-shard **regression is blind** to an off-shard poison (adopts 6/6, still pays),
while **regression+probes catches every one** (0/6) — but forgoes the capability
and pays the most. That is H1 + H3 + the price of governance, as separable curves.

Two overhead columns moved in sprint 2 and the change is intended, not a
regression. Capability and Gini reproduce bit-for-bit. Overhead rose slightly
(free trade probes 0.170 → 0.180) because doctrine **bodies** are now injected
into prompts, which enlarges the token denominator; and the adversarial probes
figure fell (0.298 → 0.204, offered 18 → 6) because rejected artifacts are now
denylisted by content hash instead of being re-screened once per round. The old
number counted retry churn as governance. Cost per **unique artifact screened**
is the comparable quantity and is reported as `tokens_per_screen`.

## The v2 layer: scarcity, endowments, and an export decision

v1's institutions were visibility masks — they answered *who can see whom*, and
no state ever made a decision. v2 adds the exporter's choice, and two conditions
without which that choice cannot express itself:

| dial | flag | why it exists |
|---|---|---|
| task-space size | `--variants` (3·K families) | with 3 families a library saturates at 3 items; every export policy collapses to a step and free-riding is costless |
| capability distribution | `--endowment {uniform,step,zipf}` | if every state holds one doctrine, the relative-gains score is the same constant for every pair, so the dial can only ever be a step |
| relative-gains sensitivity | `--k` (Grieco's coefficient) | export iff `\|their skills I lack\| + credits ≥ k` |

Headline v2 sweep (`python run_v2.py --sweep k`, free trade, N=15, 30 families,
zipf endowment, no quarantine, seed 0):

```
k     0      1      2      3      4      5..8    9+
cap   1.000  0.936  0.484  0.235  0.175  0.118   0.069
gini  0.000  0.064  0.497  0.669  0.670  0.606   0.374
```

Capability falls monotonically to the autarky floor, as realism predicts. But
inequality is **non-monotone with an interior maximum around k≈3–4**: moderate
relative-gains sensitivity is what stratifies the system. Strict realism does not
produce a hierarchy, it produces a flat, uniformly poor one. That is a claim v1
could not have made, because at three families every arm returned 1.0.

Two negative results are pinned as tests so they cannot be lost: `test_scarcity_is_what_makes_autarky_bite`
and `test_defectors_free_ride_and_depress_the_commons`.

## Handoff-brief compliance

- Skills-as-genome: libraries are Agent-Skills folders; artifacts transfer to ACTIR unchanged.
- Verifier discipline: generators compute their own answers; tests recompute them independently
  (modmath via hand-rolled repeated squaring, calendar via datetime, chains via re-product).
- Append-only event log; adoption graph and trajectories are folds over it.
- Quarantine strength is a variable (three levels) and its cost is charged to the importer's
  budget under a separate sub-account → "governance has a price" is a curve, not a claim.
- pass^k implemented (C(s,k)/C(n,k)); degenerate under the deterministic oracle, so it
  is not quoted anywhere — it becomes informative only on a live stochastic model.
- Budget doctrine: swappable model tiers; ScriptedModel decouples logic-testing from spend.

## What is real vs. stubbed

Real (v0): event log, budgets + governance accounting, three generators + exact
verification, skill library format + provenance + diversity, all four institutions,
tiered quarantine, metrics, the improve-on-failure loop, end-to-end smoke.

Real (v1, this layer): poisoned-artifact injection wired into AdversarialTrade rounds;
**quarantine sandboxing fixed** — the candidate skill is now installed *before* probes
run, then kept or rolled back (v0 evaluated probes against nothing); k-trial scheduling
so pass^k is populated; the full institution × quarantine-level × ≥3-seed grid with
per-trial isolated env dirs and seed aggregation (mean/std).

Real (v2, sprint 2): poison keyed on artifact **content** rather than sender identity, so it
survives laundering through an intermediary (v1 silently zeroed transitive propagation);
content-hash denylist so screening cost is per unique artifact; self-edits gated by the same
quarantine imports face, transactionally (snapshot/restore, byte-exact); governance reported
as a two-term decomposition (import screening vs self-edit screening); doctrine bodies
injected into prompts via progressive disclosure, so a skill can causally affect a live model;
population size, task-bank size and endowment distribution as dials; export policies
(`open`/`reciprocal`/`relative_gains`/`defector`) with logged, auditable refusal reasons;
diversity metrics (`library_similarity`, `distinct_bodies`) actually reported; `run_v2.py`
with `--live`, transcript dumps, and four sweeps (k, defectors, institutions, budget).

Stubbed / next: **live AnthropicModel runs have not been executed** — `run_v2.py --live`
exists and is wired end to end, but every number in this README comes from the scripted
oracle, so `pass^k` is degenerate and `library_similarity` is 1.0 by construction (the
oracle emits one playbook text for every doctrine). Also open: git-backed library versioning;
poison variants for the calendar/modmath archetypes; genuinely distinct archetypes alongside
the surface variants, since variants create *skill* scarcity rather than task diversity.

## Provenance

Companion to: exposé "Evolving the Improver"; Skill Diplomacy spec; ACTIR handoff brief
(terminology per its §3 table); Ren et al. (2026) arXiv:2607.13104 §6.4/§8/§9.2-FD5.
