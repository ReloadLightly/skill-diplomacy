"""Ship the event log, and prove the claim that rests on it.

    python -m paper.export_log            # -> runs/logs/*.jsonl.gz + a recompute check

README.md says: "Every metric is a pure fold over an append-only event log, so
results can be recomputed from the log alone." The property is real — the folds
are in `metrics/metrics.py` and nothing mutates history — but `.gitignore`
excluded `events.jsonl` and the log lived in a temp directory that `run_trial`
deletes in a `finally`. So no reader could ever exercise the claim, which is the
one claim an artifact evaluator is most likely to try.

This does two things, and the second matters more than the first.

**Ships the log.** Runs the headline deterministic trials, exports each event
log gzipped into `runs/logs/`, and normalises it first: `EventLog.append` stamps
`time.time()` on every event, so a committed log would differ on every run and
be useless as a fixture. Wall-clock is dropped; `seq` already carries ordering.

**Recomputes the metrics from the shipped log and checks they match.** An
exported log that nobody folds over is a file, not evidence. `verify()` reads
each log back from disk and recomputes `poison_spread`, `export_refusals` and
`pass^k` using only the public fold functions, then compares them against the
summary the run reported. If the two ever disagree, the substrate claim is
false and this fails loudly.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from skill_diplomacy.experiment.grid import TrialConfig, _run_trial_in
from skill_diplomacy.institutions.quarantine import QuarantineLevel
from skill_diplomacy.metrics.metrics import (export_refusals, pass_k,
                                             poison_spread, trials_by_task)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "logs"

# The deterministic trials whose logs back a claim in README.md. Each is small
# enough to commit and complete enough to fold over.
EXPORTS = {
    "autarky": dict(institution="autarky", quarantine=QuarantineLevel.NONE),
    "free_trade": dict(institution="free_trade", quarantine=QuarantineLevel.NONE),
    "clubs": dict(institution="clubs", quarantine=QuarantineLevel.NONE),
    "adversarial_regression": dict(institution="adversarial_trade",
                                   quarantine=QuarantineLevel.REGRESSION),
    "adversarial_probes": dict(institution="adversarial_trade",
                               quarantine=QuarantineLevel.REGRESSION_PLUS_PROBES),
}

BASE = dict(seed=0, rounds=3, tasks_per_round=3, k_trials=3, n_states=3,
            n_variants=1)

VOLATILE = ("ts",)   # wall clock: not part of the run, and would churn the diff


def _normalise(event: dict) -> dict:
    return {k: v for k, v in event.items() if k not in VOLATILE}


def export_one(name: str, overrides: dict, workdir: Path) -> tuple[Path, dict]:
    """Run one trial in a directory we control, so the log survives the run."""
    cfg = TrialConfig(**{**BASE, **overrides})
    summary = _run_trial_in(cfg, workdir)
    events = [_normalise(e) for e in
              (json.loads(line) for line in
               (workdir / "events.jsonl").read_text().splitlines() if line.strip())]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.jsonl.gz"
    body = "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n"
                   for e in events)
    # mtime=0: the gzip container stores a modification time, so the default
    # would give a byte-different file on every export and churn the git diff
    # even when not one event changed. A committed fixture has to be stable.
    with open(path, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz:
            gz.write(body.encode())
    return path, summary


def read_log(path: Path) -> list[dict]:
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f if line.strip()]


def recompute(events: list[dict], states: list[str], k: int) -> dict:
    """Every headline quantity this log can support, folded from the log alone —
    no libraries on disk, no trial object, nothing but the events."""
    return {
        "poison_spread": poison_spread(events),
        "exports": export_refusals(events),
        "pass^k": {s: round(pass_k(trials_by_task(events, s), k), 3) for s in states},
    }


def verify(path: Path, summary: dict) -> list[str]:
    """Fold the shipped log and compare against what the run reported."""
    events = read_log(path)
    names = sorted(summary["states"])
    got = recompute(events, names, summary["provenance"]["config"]["k_trials"])
    problems = []
    if got["poison_spread"] != summary["poison_spread"]:
        problems.append(f"{path.name}: poison_spread differs — "
                        f"log {got['poison_spread']} vs summary {summary['poison_spread']}")
    if got["exports"] != summary["exports"]:
        problems.append(f"{path.name}: export_refusals differs")
    for s in names:
        if got["pass^k"][s] != summary["states"][s]["pass^k"]:
            problems.append(f"{path.name}: pass^k for {s} differs — "
                            f"log {got['pass^k'][s]} vs summary "
                            f"{summary['states'][s]['pass^k']}")
    return problems


def main() -> int:
    import shutil
    import tempfile

    problems: list[str] = []
    for name, overrides in EXPORTS.items():
        workdir = Path(tempfile.mkdtemp(prefix=f"sd_export_{name}_"))
        try:
            path, summary = export_one(name, overrides, workdir)
            events = read_log(path)
            found = verify(path, summary)
            problems += found
            status = "OK" if not found else f"MISMATCH ({len(found)})"
            print(f"  {name:<24} {len(events):>5} events  "
                  f"{path.stat().st_size / 1024:>6.1f} KB  recompute: {status}")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    if problems:
        print("\nFAIL — a metric could not be recomputed from its own log:")
        for p in problems:
            print(f"  ! {p}")
        return 1
    print(f"\nOK — every metric recomputes from the shipped log alone "
          f"({OUT.relative_to(ROOT)}/)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
