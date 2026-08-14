"""Minimal LIVE smoke run via the Claude CLI. Purpose (per PAPERSKELETON step 1):
find out what breaks on a real model — answer-format parsing, doctrine use, and
whether an injected poison actually acts. Tiny by design."""
from __future__ import annotations
import json, sys
from pathlib import Path
from skill_diplomacy.experiment.grid import TrialConfig, run_trial
from skill_diplomacy.institutions.quarantine import QuarantineLevel
from skill_diplomacy.harness.cli_model import CLIModel

cfg = TrialConfig(
    institution="adversarial_trade",
    quarantine=QuarantineLevel.REGRESSION_PLUS_PROBES,
    seed=0, rounds=2, tasks_per_round=1, k_trials=1,
    n_states=3, n_variants=1, endowment="uniform",
    n_probes=2, gate_self_edits=True,
    max_tokens=5_000_000, max_rollouts=100_000,
    dump_transcripts=True,
)
model = CLIModel(model_id=sys.argv[1] if len(sys.argv) > 1 else "claude-haiku-4-5")
res = run_trial(cfg, model=model)
Path("runs").mkdir(exist_ok=True)
Path("runs/smoke.json").write_text(json.dumps(res, indent=2))
tr = res.pop("transcripts", [])
Path("runs/smoke_transcripts.json").write_text(json.dumps(tr, indent=2))
print("=== SUMMARY (transcripts stripped) ===")
print(json.dumps(res, indent=2))
print(f"\n=== {len(tr)} transcripts written to runs/smoke_transcripts.json ===")
