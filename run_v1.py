"""v1 grid run: 4 institutions x 3 quarantine levels x >=3 seeds, ScriptedModel
(deterministic, no API spend). Writes the aggregated price-of-governance table.

    python run_v1.py                 # full grid → runs/grid_{summary,rows}.json + rows.csv
    python run_v1.py --seeds 5       # 5 seeds per cell
    python run_v1.py --quick         # 1 seed, faster smoke of the whole matrix

Swap ScriptedModel for AnthropicModel inside skill_diplomacy/experiment/grid.py
(one line) to run the identical matrix live on Haiku-tier workers.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from skill_diplomacy.experiment.grid import aggregate, run_grid

ROW_COLS = [
    "institution", "quarantine", "seeds", "mean_capability", "capability_std",
    "capability_gini", "governance_overhead", "poison_adoption_rate",
    "poison_offered", "poison_adopted",
]


def _print_table(rows: list) -> None:
    header = ["institution", "quarantine", "cap", "gini", "gov_oh", "poison_adopt"]
    widths = [18, 24, 6, 6, 7, 13]
    line = "  ".join(h.ljust(w) for h, w in zip(header, widths))
    print(line)
    print("-" * len(line))
    for r in rows:
        poison = (f'{r["poison_adopted"]}/{r["poison_offered"]}'
                  if r["poison_offered"] else "-")
        cells = [
            r["institution"].ljust(widths[0]),
            r["quarantine"].ljust(widths[1]),
            f'{r["mean_capability"]:.2f}'.ljust(widths[2]),
            f'{r["capability_gini"]:.2f}'.ljust(widths[3]),
            f'{r["governance_overhead"]:.3f}'.ljust(widths[4]),
            poison.ljust(widths[5]),
        ]
        print("  ".join(cells))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=3, help="seeds per cell")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="1 seed, 2 rounds")
    ap.add_argument("--outdir", type=Path, default=Path("runs"))
    args = ap.parse_args()

    n_seeds, rounds = (1, 2) if args.quick else (args.seeds, args.rounds)
    seeds = tuple(range(n_seeds))

    print(f"Running grid: 4 institutions x 3 quarantine levels x {n_seeds} seed(s), "
          f"{rounds} rounds each ...\n")
    results = run_grid(seeds=seeds, rounds=rounds)
    rows = aggregate(results)

    _print_table(rows)

    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "grid_summary.json").write_text(json.dumps(rows, indent=2))
    (args.outdir / "grid_trials.json").write_text(json.dumps(results, indent=2))
    with (args.outdir / "grid_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ROW_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in ROW_COLS})

    print(f"\nWrote {args.outdir}/grid_summary.json, grid_trials.json, grid_summary.csv")


if __name__ == "__main__":
    main()
