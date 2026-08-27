"""Provenance: a committed number must say what produced it.

The live artifacts in `runs/h1/` and `runs/lex/` recorded institution, seed and
endowment and nothing else — no model, no date, no commit, no temperature. A
reader could not tell which model tier produced "free trade 0.963", nor whether
the code that produced it is the code in the repository. These tests keep that
from regressing, and they lock the failure-accounting that makes a live
capability figure interpretable at all.
"""
from __future__ import annotations

import pytest

from skill_diplomacy.experiment.grid import TrialConfig, run_trial
from skill_diplomacy.harness.provenance import HARNESS_VERSION, run_provenance
from skill_diplomacy.institutions.quarantine import QuarantineLevel


def _cfg(**kw):
    base = dict(institution="free_trade", quarantine=QuarantineLevel.NONE, seed=0,
                rounds=1, tasks_per_round=1, k_trials=1, n_states=3, n_variants=3)
    base.update(kw)
    return TrialConfig(**base)


def test_every_summary_carries_provenance():
    p = run_trial(_cfg())["provenance"]
    assert p["harness_version"] == HARNESS_VERSION
    assert p["timestamp_utc"].endswith("+00:00")
    assert p["python"]
    assert "commit" in p["git"] and "dirty" in p["git"]


def test_provenance_records_the_full_config_not_a_summary():
    """The point is re-runnability: every field of the config that shaped the
    number, not the handful the summary happens to echo."""
    cfg = _cfg(seed=7, n_states=5, endowment="zipf", great_power_weight=4)
    p = run_trial(cfg)["provenance"]
    assert p["config"]["seed"] == 7
    assert p["config"]["n_states"] == 5
    assert p["config"]["endowment"] == "zipf"
    assert p["config"]["great_power_weight"] == 4
    assert p["config"]["fresh_probes"] == cfg.fresh_probes


def test_the_live_status_label_is_derived_not_asserted():
    """Every claim in the README is stamped harness or live. That label is now
    a property of the client that ran, so it cannot drift from the truth."""
    assert run_trial(_cfg())["provenance"]["live"] is False


class _FlakyCLI:
    """Stands in for `CLIModel` when the transport keeps failing."""

    def __init__(self, fail_every: int = 2):
        from skill_diplomacy.harness.cli_model import CLIModel
        self.inner = CLIModel()
        self.fail_every = fail_every

    def complete(self, system, prompt, max_tokens=800):
        from skill_diplomacy.harness.model import ModelResponse
        self.inner.calls += 1
        if self.inner.calls % self.fail_every == 0:
            self.inner.errors += 1
            self.inner.error_kinds["timeout"] += 1
            return ModelResponse("[cli-error: timeout]\nANSWER: __error__", 1, 1)
        return ModelResponse("ANSWER: 1", 1, 1)

    def describe(self):
        return self.inner.describe()


def test_transport_failures_are_counted_not_scored_as_cognition():
    """A timeout used to be indistinguishable from a wrong answer: it returned
    `ANSWER: __error__`, scored as a failure, and depressed capability with no
    record anywhere. The gap claimed in runs/h1/ is 0.074, which a handful of
    timeouts is the same order as."""
    m = _FlakyCLI(fail_every=2)
    for _ in range(10):
        m.complete("sys", "prompt")
    d = m.describe()
    assert d["errors"] == 5 and d["calls"] == 10
    assert d["error_rate"] == 0.5
    assert d["error_kinds"] == {"timeout": 5}
    assert d["capability_is_lower_bound"] is True
    assert "LOWER BOUND" in d["warning"]


def test_a_clean_live_client_makes_no_lower_bound_claim():
    from skill_diplomacy.harness.cli_model import CLIModel
    d = CLIModel().describe()
    assert d["live"] is True
    assert d["errors"] == 0
    assert "capability_is_lower_bound" not in d
    assert d["model_id_requested"]


def test_provenance_degrades_rather_than_raises_on_a_client_it_cannot_describe():
    class Opaque:
        def describe(self):
            raise RuntimeError("nope")

    p = run_provenance(Opaque(), {})
    assert p["model"]["client"] == "Opaque"
    assert "describe_error" in p["model"]
    assert p["live"] is True   # not a ScriptedModel, so treated as live
