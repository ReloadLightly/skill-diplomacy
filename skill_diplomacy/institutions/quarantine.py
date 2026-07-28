"""Import quarantine — tiered, per the handoff brief's H3 upgrade:

  NONE                : adopt on sight (the no-governance baseline)
  REGRESSION          : candidate must not break the importer's stored
                        regression instances (the ACTIR 'never again' suite)
  REGRESSION_PLUS_PROBES : regression + k FRESH generator instances drawn
                        off-shard (contamination-proof held-out probes)

Reporting quarantine level as a variable turns 'governance has a price' into a
price CURVE: protection vs. budget overhead, charged to the importer."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from ..bank.base import TaskInstance


class QuarantineLevel(Enum):
    NONE = "none"
    REGRESSION = "regression"
    REGRESSION_PLUS_PROBES = "regression_plus_probes"


@dataclass
class QuarantineReport:
    accepted: bool
    level: str
    regression_passed: int = 0
    regression_total: int = 0
    probes_passed: int = 0
    probes_total: int = 0


def run_quarantine(
    level: QuarantineLevel,
    regression_suite: list[TaskInstance],
    probe_suite: list[TaskInstance],
    evaluate: Callable[[TaskInstance], bool],
    regression_threshold: float = 1.0,
    probe_threshold: float = 0.6,
) -> QuarantineReport:
    """`evaluate` runs a task WITH the candidate skill installed (the harness
    wires model, library and budget charging; quarantine only decides).
    Regression is strict by default: the 'never again' suite may not regress."""
    if level is QuarantineLevel.NONE:
        return QuarantineReport(True, level.value)

    reg_pass = sum(evaluate(t) for t in regression_suite)
    report = QuarantineReport(False, level.value, reg_pass, len(regression_suite))
    reg_ok = (reg_pass >= regression_threshold * len(regression_suite)) if regression_suite else True

    if level is QuarantineLevel.REGRESSION:
        report.accepted = reg_ok
        return report

    probe_pass = sum(evaluate(t) for t in probe_suite)
    report.probes_passed, report.probes_total = probe_pass, len(probe_suite)
    probe_ok = (probe_pass >= probe_threshold * len(probe_suite)) if probe_suite else True
    report.accepted = reg_ok and probe_ok
    return report
