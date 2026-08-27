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

    def describe(self) -> dict:
        """Declares itself NOT live, which is what makes a summary's status
        label derivable instead of hand-asserted."""
        return {"client": "ScriptedModel", "live": False,
                "kind": "policy_fn" if callable(self._script) else "queued_script",
                "errors": 0, "calls": self._i}


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
        self.calls = 0
        self.served_models: dict[str, int] = {}

    def complete(self, system: str, prompt: str, max_tokens: int = 800) -> ModelResponse:
        msg = self._client.messages.create(
            model=self.model_id, max_tokens=max_tokens, temperature=self.temperature,
            system=system, messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        self.calls += 1
        # `model_id` is what we asked for and may be a moving alias; the response
        # carries what actually served the call. Recording only the former makes
        # a live number unattributable to specific weights after the alias moves.
        served = getattr(msg, "model", None)
        if served:
            self.served_models[served] = self.served_models.get(served, 0) + 1
        return ModelResponse(text, msg.usage.input_tokens, msg.usage.output_tokens)

    def describe(self) -> dict:
        return {"client": "AnthropicModel", "live": True,
                "model_id_requested": self.model_id,
                "models_served": dict(self.served_models),
                "temperature": self.temperature,
                "calls": self.calls, "errors": 0}
