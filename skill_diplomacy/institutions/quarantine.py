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
    vacuous: bool = False
    """True when acceptance rested on an EMPTY suite rather than on evidence.

    A gate with nothing to check accepts, and that acceptance is
    indistinguishable in every downstream metric from one earned by passing
    tests. It is not the same thing, and the difference has already produced a
    wrong result: an experiment reported as "screened versus unscreened" turned
    out, on instrumentation, to have accepted 492 of 492 self-edits vacuously
    and none on the merits, which made it a measurement of self-editing being
    off versus on. Anything that counts screening decisions must be able to
    exclude these."""


def run_quarantine(
    level: QuarantineLevel,
    regression_suite: list[TaskInstance],
    probe_suite: list[TaskInstance],
    evaluate: Callable[[TaskInstance], bool],
    regression_threshold: float = 1.0,
    probe_threshold: float = 0.6,
    empty_suite_passes: bool = True,
) -> QuarantineReport:
    """`evaluate` runs a task WITH the candidate skill installed (the harness
    wires model, library and budget charging; quarantine only decides).
    Regression is strict by default: the 'never again' suite may not regress.

    `empty_suite_passes` decides what a gate does when it has NOTHING to check.
    The default True is the behaviour every published number here was produced
    under, and it is defensible for an IMPORT — an importer with no regression
    history has no grounds to refuse. It is not defensible for a SELF-EDIT: an
    agent replacing a doctrine it has no evidence against should not have that
    edit committed because it happens to have no evidence at all.
    `state.improve_from_failure` therefore passes False, which is the difference
    between a gate that screens and a gate that reads as though it does."""
    if level is QuarantineLevel.NONE:
        return QuarantineReport(True, level.value)

    reg_pass = sum(evaluate(t) for t in regression_suite)
    report = QuarantineReport(False, level.value, reg_pass, len(regression_suite))
    if regression_suite:
        reg_ok = reg_pass >= regression_threshold * len(regression_suite)
    else:
        reg_ok = empty_suite_passes
        report.vacuous = True

    if level is QuarantineLevel.REGRESSION:
        report.accepted = reg_ok
        return report

    probe_pass = sum(evaluate(t) for t in probe_suite)
    report.probes_passed, report.probes_total = probe_pass, len(probe_suite)
    if probe_suite:
        probe_ok = probe_pass >= probe_threshold * len(probe_suite)
        report.vacuous = report.vacuous and not regression_suite
    else:
        probe_ok = empty_suite_passes
        report.vacuous = True
    report.accepted = reg_ok and probe_ok
    return report
