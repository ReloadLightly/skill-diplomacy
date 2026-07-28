# Skill Diplomacy — WP1 Harness (v0)

Experimental harness for **"Skill Diplomacy: Exchange Institutions for Co-Evolving
Self-Improving Agents"** (spec, July 2026), built to the ACTIR handoff brief
(2026-07-28). Pure Python, stdlib-only at runtime; `pytest` for tests;
`anthropic` optional for live runs.

## Quick start

```bash
pytest tests/ -q          # 16 tests: generators (independent ground truth),
                          # budget, events, skills, institutions, quarantine, metrics
python run_v0.py          # scripted smoke run: autarky vs free trade, no API spend
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
run_v0.py                  2-state smoke experiment
tests/test_all.py          incl. INDEPENDENT recomputation of generator ground truth
```

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

## What is real vs. stubbed (v0)

Real: event log, budgets + governance accounting, three generators + exact verification,
skill library format + provenance + diversity, all four institutions, tiered quarantine,
metrics, the improve-on-failure loop, end-to-end smoke.

Stubbed / next (v1): live AnthropicModel runs (set `ANTHROPIC_API_KEY`; Haiku-tier workers);
poisoned-artifact injection wired into AdversarialTrade rounds (helper exists, loop wiring
pending); k-trial scheduling for pass^k; git-backed library versioning; 4-state configs for
the full 4-institutions × quarantine-levels × ≥3-seeds grid; per-trial isolated env dirs;
transcript dumps for the read-the-transcripts discipline.

## Provenance

Companion to: exposé "Evolving the Improver"; Skill Diplomacy spec; ACTIR handoff brief
(terminology per its §3 table); Ren et al. (2026) arXiv:2607.13104 §6.4/§8/§9.2-FD5.
