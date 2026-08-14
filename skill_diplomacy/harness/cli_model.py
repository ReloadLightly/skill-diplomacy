"""CLIModel — a ModelClient that shells out to the `claude` CLI.

Lets `run_trial(..., model=CLIModel())` do a real live run in environments that
have the Claude CLI authenticated but no ANTHROPIC_API_KEY (e.g. this sandbox).
Duck-types harness.model.ModelClient. Tools are disabled so the call behaves as
a plain completion, and the harness system prompt REPLACES the CLI default so
the agent is our 'state strategist', not Claude Code.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from .model import ModelResponse

_DISALLOWED = "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,TodoWrite,Task,NotebookEdit"


@dataclass
class CLIModel:
    model_id: str = "claude-haiku-4-5"
    timeout_s: int = 120
    retries: int = 2

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> ModelResponse:
        cmd = [
            "claude", "-p", prompt,
            "--system-prompt", system,
            "--model", self.model_id,
            "--output-format", "json",
            "--disallowedTools", _DISALLOWED,
        ]
        last = ""
        for _ in range(self.retries + 1):
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
                    return ModelResponse(text, max(1, tin), max(1, tout))
                last = "empty result"
            except Exception as e:  # timeout, JSON error, non-zero exit
                last = str(e)
        # give up: empty response → the task simply fails, run continues
        return ModelResponse(f"[cli-error: {last}]\nANSWER: __error__", 1, 1)
