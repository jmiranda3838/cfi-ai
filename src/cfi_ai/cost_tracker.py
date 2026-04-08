"""Session-level token + cost accumulator.

Fed by the agent loop after every successful streaming turn (see the
``finally`` blocks in ``agent.py`` that already call
``stream_result.log_completion()``). The UI's bottom toolbar reads from this
between turns to show the current context-window usage and running cost.

Persisted into the session JSON via ``CostTracker.to_dict()`` /
``from_dict()`` so ``/resume`` continues counting where the previous run left
off.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from cfi_ai.pricing import lookup_context_window, lookup_pricing


@dataclass
class CostTracker:
    """Mutable per-session token and cost accumulator.

    ``last_prompt_tokens`` is the prompt size of the most recent turn — i.e.
    the size of the conversation history that was sent to the model. That's
    the natural "current context window usage" indicator: it grows as the
    conversation accumulates and equals what the next turn will be billed for
    (minus cache hits).
    """

    model: str
    last_prompt_tokens: int = 0
    total_input_billed: int = 0
    total_cached: int = 0
    total_output: int = 0
    total_cost_usd: float = 0.0

    def record(self, usage: Any) -> None:
        """Fold one turn's ``usage_metadata`` into the running totals.

        ``usage`` is the ``GenerateContentResponseUsageMetadata`` object from
        the streaming response. Accessed via ``getattr`` with ``or 0`` defaults
        because some fields are ``None`` on small turns and the protobuf type
        doesn't always populate every attribute.
        """
        if usage is None:
            return
        prompt = getattr(usage, "prompt_token_count", None) or 0
        cached = getattr(usage, "cached_content_token_count", None) or 0
        output = getattr(usage, "candidates_token_count", None) or 0
        billed_input = max(prompt - cached, 0)

        self.last_prompt_tokens = prompt
        self.total_input_billed += billed_input
        self.total_cached += cached
        self.total_output += output

        rates = lookup_pricing(self.model)
        if rates:
            self.total_cost_usd += (
                billed_input * rates["input"]
                + cached * rates["cached"]
                + output * rates["output"]
            ) / 1_000_000

    def context_window(self) -> int | None:
        return lookup_context_window(self.model)

    def has_pricing(self) -> bool:
        return lookup_pricing(self.model) is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for SessionStore.save. ``model`` is intentionally omitted —
        on resume the live config's model wins, not the model that was used
        when the session was first written."""
        data = asdict(self)
        data.pop("model", None)
        return data

    @classmethod
    def from_dict(cls, model: str, data: dict[str, Any] | None) -> "CostTracker":
        """Reconstruct from a SessionStore payload. Missing/extra fields tolerated."""
        if not data:
            return cls(model=model)
        return cls(
            model=model,
            last_prompt_tokens=int(data.get("last_prompt_tokens", 0) or 0),
            total_input_billed=int(data.get("total_input_billed", 0) or 0),
            total_cached=int(data.get("total_cached", 0) or 0),
            total_output=int(data.get("total_output", 0) or 0),
            total_cost_usd=float(data.get("total_cost_usd", 0.0) or 0.0),
        )
