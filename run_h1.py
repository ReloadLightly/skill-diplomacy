"""H1, live: does exchange causally raise capability on a REAL model?

The scripted oracle predicts autarky=0.33, free_trade=1.00 (v1 table). That
prediction is a theorem about the harness. This script asks the same question of
a live model, across seeds, so the effect can be measured against real noise.

Usage: python run_h1.py <institution> <seed>
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from skill_diplomacy.experiment.grid import TrialConfig, run_trial
from skill_diplomacy.institutions.quarantine import QuarantineLevel
from skill_diplomacy.harness.cli_model import CLIModel

inst, seed = sys.argv[1], int(sys.argv[2])
cfg = TrialConfig(
    institution=inst,
    quarantine=QuarantineLevel.NONE,   # isolate the exchange effect
    seed=seed, rounds=3, tasks_per_round=1, k_trials=1,
    n_states=3, n_variants=1, endowment="uniform",
    gate_self_edits=False,             # v1 default
    max_tokens=50_000_000, max_rollouts=1_000_000,
    dump_transcripts=True,
)
res = run_trial(cfg, model=CLIModel(model_id="claude-haiku-4-5"))
out = Path("runs/h1"); out.mkdir(parents=True, exist_ok=True)
tr = res.pop("transcripts", [])
(out / f"{inst}_s{seed}.json").write_text(json.dumps(res, indent=2))
(out / f"{inst}_s{seed}_transcripts.json").write_text(json.dumps(tr, indent=2))
print(f"{inst} seed={seed}: capability={res['mean_capability']} "
      f"per_state={ {n: res['states'][n]['final_capability'] for n in res['states']} }")
