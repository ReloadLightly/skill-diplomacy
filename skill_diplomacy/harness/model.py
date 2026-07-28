"""Model clients. States run on small/cheap tiers per the ACTIR budget doctrine
('expensive lead, cheap workers'); v0 experiments need headroom, not frontier IQ.

ScriptedModel makes the whole harness testable without API keys or spend —
the institution/quarantine/metrics logic is model-agnostic by construction.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass
class ModelResponse:
    text: str
    tokens_in: int
    tokens_out: int


class ModelClient(Protocol):
    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> ModelResponse: ...


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class ScriptedModel:
    """Deterministic stand-in: yields queued responses, or calls a policy fn."""

    def __init__(self, script: list[str] | Callable[[str, str], str]):
        self._script = script
        self._i = 0

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> ModelResponse:
        if callable(self._script):
            text = self._script(system, prompt)
        else:
            text = self._script[min(self._i, len(self._script) - 1)]
            self._i += 1
        return ModelResponse(text, _approx_tokens(system + prompt), _approx_tokens(text))


class AnthropicModel:
    """Real client (lazy import). Requires ANTHROPIC_API_KEY in the environment."""

    def __init__(self, model_id: str = "claude-haiku-4-5", temperature: float = 0.2):
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError("pip install anthropic to use AnthropicModel") from e
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set — use ScriptedModel for dry runs")
        self._client = anthropic.Anthropic()
        self.model_id = model_id
        self.temperature = temperature

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> ModelResponse:
        msg = self._client.messages.create(
            model=self.model_id, max_tokens=max_tokens, temperature=self.temperature,
            system=system, messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return ModelResponse(text, msg.usage.input_tokens, msg.usage.output_tokens)
