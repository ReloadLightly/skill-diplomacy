"""The institutional battery, re-run over LOAD-BEARING families.

Every institutional result in this repository was previously measured over task
families a competent model solves cold (runs/skill_lift_live.json: lift +0.00,
+0.00, -0.17). This script repeats the comparison over `lexicon` families, whose
answers require information that appears only in the doctrine, so capability is
genuinely a function of what an agent holds.

Usage: python run_lex.py <institution> <seed> [quarantine]
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from skill_diplomacy.experiment.grid import TrialConfig, run_trial
from skill_diplomacy.institutions.quarantine import QuarantineLevel
from skill_diplomacy.harness.cli_model import CLIModel

LEVELS = {"none": QuarantineLevel.NONE, "regression": QuarantineLevel.REGRESSION,
          "probes": QuarantineLevel.REGRESSION_PLUS_PROBES}

inst = sys.argv[1]
seed = int(sys.argv[2])
qname = sys.argv[3] if len(sys.argv) > 3 else "none"

cfg = TrialConfig(
    institution=inst, quarantine=LEVELS[qname], seed=seed,
    rounds=2, tasks_per_round=1, k_trials=1,
    n_states=3, n_variants=3, archetypes=("lexicon",),
    seed_references=True, endowment="uniform", n_probes=3,
    max_tokens=50_000_000, max_rollouts=1_000_000, dump_transcripts=True,
)
res = run_trial(cfg, model=CLIModel(model_id="claude-haiku-4-5"))
out = Path("runs/lex"); out.mkdir(parents=True, exist_ok=True)
tag = f"{inst}_{qname}_s{seed}"
tr = res.pop("transcripts", [])
(out / f"{tag}.json").write_text(json.dumps(res, indent=2))
(out / f"{tag}_transcripts.json").write_text(json.dumps(tr, indent=2))
ps = res["poison_spread"]
print(f"{tag}: capability={res['mean_capability']} gini={res['capability_gini']} "
      f"gov_overhead={res['governance_overhead']} "
      f"poison offered/adopted={ps['offered']}/{ps['adopted']} "
      f"per_state={ {n: res['states'][n]['final_capability'] for n in res['states']} }")
