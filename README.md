# Skill Diplomacy — WP1 Harness (v0)

Experimental harness for **"Skill Diplomacy: Exchange Institutions for Co-Evolving
Self-Improving Agents"** (spec, July 2026), built to the ACTIR handoff brief
(2026-07-28). Pure Python, stdlib-only at runtime; `pytest` for tests;
`anthropic` optional for live runs.

## Quick start

```bash
pytest tests/ -q          # 28 tests: v0 units + v1 grid (capability gradient,
                          # price-of-governance curve, poison mechanism, determinism)
python run_v0.py          # scripted smoke run: autarky vs free trade, no API spend
python run_v1.py          # the full grid → runs/grid_summary.{json,csv} (no API spend)
python run_v1.py --quick  # 1 seed, 2 rounds: fast smoke of the whole matrix
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
run_v1.py                  full grid runner → runs/grid_summary.{json,csv}
tests/test_all.py          v0 units; INDEPENDENT recomputation of generator truth
tests/test_experiment.py   v1 grid: the orderings/mechanism the experiment shows
```

## The v1 result (deterministic ScriptedModel, 4×3×3 grid, no API spend)

```
institution         quarantine                cap    gini   gov_oh   poison_adopt
autarky             none/regression/probes    0.33   0.00   0.000    -
free_trade          none                      1.00   0.00   0.000    -
free_trade          regression                1.00   0.00   0.048    -
free_trade          regression_plus_probes    1.00   0.00   0.170    -
clubs               none/regression/probes    0.56   0.13   0.0–0.07 -
adversarial_trade   none                      0.86   0.07   0.000    6/6
adversarial_trade   regression                0.86   0.07   0.048    6/6
adversarial_trade   regression_plus_probes    0.78   0.10   0.298    0/18
```

Reading: institutions produce a real capability gradient (autarky 1/3 → clubs 0.56,
unequal → free trade 1.0). Governance is a **price curve** — overhead rises
monotonically none→regression→probes. The headline (`adversarial_trade`):
home-shard **regression is blind** to an off-shard poison (adopts 6/6, still pays),
while **regression+probes catches every one** (0/18) — but forgoes the capability
and pays the most. That is H1 + H3 + the price of governance, as separable curves.

## Handoff-brief compliance

- Skills-as-genome: libraries are Agent-Skills folders; artifacts transfer to ACTIR unchanged.
- Verifier discipline: generators compute their own answers; tests recompute them independently
  (modmath via hand-rolled repeated squaring, calendar via datetime, chains via re-product).
- Append-only event log; adoption graph and trajectories are folds over it.
- Quarantine strength is a variable (three levels) and its cost is charged to the importer's
  budget under a separate sub-account → "governance has a price" is a curve, not a claim.
- pass^k implemented (C(s,k)/C(n,k)); v0 smoke uses single trials, so schedule k-trial
  repeats in v1 configs before quoting it.
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

Stubbed / next: live AnthropicModel runs (set `ANTHROPIC_API_KEY`; Haiku-tier workers —
swap ScriptedModel for AnthropicModel in `experiment/grid.py`, one line; pass^k becomes an
informative curve once the model is stochastic); git-backed library versioning; transcript
dumps for the read-the-transcripts discipline; poison variants for calendar/modmath families.

## Provenance

Companion to: exposé "Evolving the Improver"; Skill Diplomacy spec; ACTIR handoff brief
(terminology per its §3 table); Ren et al. (2026) arXiv:2607.13104 §6.4/§8/§9.2-FD5.
