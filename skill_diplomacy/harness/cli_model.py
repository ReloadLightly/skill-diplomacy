"""CLIModel — a ModelClient that shells out to the `claude` CLI.

Lets `run_trial(..., model=CLIModel())` do a real live run in environments that
have the Claude CLI authenticated but no ANTHROPIC_API_KEY (e.g. this sandbox).
Duck-types harness.model.ModelClient. Tools are disabled so the call behaves as
a plain completion, and the harness system prompt REPLACES the CLI default so
the agent is our 'state strategist', not Claude Code.

A note on failure, because it changed how live numbers must be read
-------------------------------------------------------------------
When every retry is exhausted this client returns `ANSWER: __error__` so the
run continues rather than dying. That is the right behaviour — one flaky call
should not destroy a multi-hour trial — but it has a consequence the harness
previously did not record anywhere: a transport failure is scored as a WRONG
ANSWER. Capability is a mean over binary outcomes, so every timeout, every
non-zero exit, every truncated JSON payload silently pushed the reported
capability down, and nothing in the run summary distinguished "the model
answered incorrectly" from "the model was never reached".

That matters for the live results already committed. `runs/h1/` reports autarky
0.889 against free trade 0.963 — a gap of 0.074 — with no way to tell how many
of the underlying failures were transport rather than cognition. A handful of
timeouts is the same order as the effect being claimed.

So this client now counts its own failures and exposes them through
`describe()`, which `harness/provenance.py` stamps into the trial summary. A
live run whose `model.errors` is non-zero is a run whose capability figure is a
LOWER BOUND, and the summary now says so in the artifact instead of leaving it
to be discovered.
"""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import dataclass, field

from .model import ModelResponse

_DISALLOWED = "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,TodoWrite,Task,NotebookEdit"

ERROR_SENTINEL = "__error__"


@dataclass
class CLIModel:
    model_id: str = "claude-haiku-4-5"
    timeout_s: int = 120
    retries: int = 2

    calls: int = 0
    errors: int = 0
    retried_calls: int = 0
    error_kinds: Counter = field(default_factory=Counter)
    served_models: Counter = field(default_factory=Counter)

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> ModelResponse:
        cmd = [
            "claude", "-p", prompt,
            "--system-prompt", system,
            "--model", self.model_id,
            "--output-format", "json",
            "--disallowedTools", _DISALLOWED,
        ]
        self.calls += 1
        last = ""
        for attempt in range(self.retries + 1):
            try:
                out = subprocess.run(
                    cmd, capture_output=True, text=True,
                    timeout=self.timeout_s, stdin=subprocess.DEVNULL,
                ).stdout
                d = json.loads(out)
                text = d.get("result", "") or ""
                u = d.get("usage", {}) or {}
                tin = int(u.get("input_tokens", 0)) + int(u.get("cache_read_input_tokens", 0)) \
                    + int(u.get("cache_creation_input_tokens", 0))
                tout = int(u.get("output_tokens", 0))
                if text:
                    # The alias we asked for may not be the snapshot that served
                    # the call; record whatever the CLI reports so the run stays
                    # attributable after the alias moves.
                    for key in ("modelUsage", "model_usage"):
                        usage = d.get(key)
                        if isinstance(usage, dict):
                            for served in usage:
                                self.served_models[served] += 1
                            break
                    else:
                        served = d.get("model")
                        if served:
                            self.served_models[str(served)] += 1
                    if attempt:
                        self.retried_calls += 1
                    return ModelResponse(text, max(1, tin), max(1, tout))
                last = "empty_result"
            except subprocess.TimeoutExpired:
                last = "timeout"
            except json.JSONDecodeError:
                last = "bad_json"
            except Exception as e:  # non-zero exit, missing binary, anything else
                last = type(e).__name__
        # Give up. The task will score as a failure — see the module docstring:
        # this is counted, not hidden, because it biases capability downward.
        self.errors += 1
        self.error_kinds[last] += 1
        return ModelResponse(f"[cli-error: {last}]\nANSWER: {ERROR_SENTINEL}", 1, 1)

    # -- provenance ---------------------------------------------------------
    @property
    def error_rate(self) -> float:
        return (self.errors / self.calls) if self.calls else 0.0

    def describe(self) -> dict:
        d = {
            "client": "CLIModel",
            "live": True,
            "model_id_requested": self.model_id,
            "models_served": dict(self.served_models),
            "timeout_s": self.timeout_s,
            "retries": self.retries,
            "calls": self.calls,
            "errors": self.errors,
            "error_rate": round(self.error_rate, 4),
            "error_kinds": dict(self.error_kinds),
            "retried_calls": self.retried_calls,
        }
        if self.errors:
            d["capability_is_lower_bound"] = True
            d["warning"] = (
                f"{self.errors}/{self.calls} completions failed after retries and were "
                f"scored as wrong answers. Reported capability is a LOWER BOUND; the "
                f"gap being measured must exceed this error rate to be interpretable.")
        return d
