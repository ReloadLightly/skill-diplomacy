"""v1 experiment layer: the full institution x quarantine x seed grid.

v0 (`run_v0.py`) proved the plumbing on a 2-state smoke run. This package turns
that into the measured experiment the workshop paper needs:

  * a poison-aware scripted oracle (`oracle`) whose off-shard capability actually
    degrades when a poisoned doctrine is installed — so quarantine has something
    real to catch;
  * real quarantine sandboxing (`grid.run_trial`): the candidate skill is
    installed BEFORE probes run, then kept or rolled back — fixing the v0 stub
    where probes tested nothing;
  * k-trial scheduling so `pass^k` is populated;
  * the 3-institution/4-institution x 3-quarantine-level x >=3-seed matrix with
    per-cell aggregation (`grid.run_grid`, `grid.aggregate`).

Still ScriptedModel-only: no API spend. Swap in `AnthropicModel` (unchanged
interface) to run the identical grid live.
"""
