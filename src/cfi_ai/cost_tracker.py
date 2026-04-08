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

    ``cap_context_tokens`` is a configurable hard cap (from ``Config``). When
    > 0, ``cap_reached()`` returns True once the previous turn's prompt size
    meets or exceeds the cap, and ``context_window()`` returns the cap so the
    toolbar shows a tighter denominator. Therapists hit the cap → forced to
    ``/clear`` → fresh conversation → real cost savings.
    """

    model: str
    cap_context_tokens: int = 0
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
        """Effective context window for the toolbar denominator.

        When a cap is configured (``cap_context_tokens > 0``) the smaller of
        the model's native window and the cap is returned, so the displayed
        ``ctx X/Y (Z%)`` agrees with the cap-check denominator.
        """
        model_window = lookup_context_window(self.model)
        if self.cap_context_tokens > 0:
            if model_window is None:
                return self.cap_context_tokens
            return min(model_window, self.cap_context_tokens)
        return model_window

    def cap_reached(self) -> bool:
        """True when the previous turn's prompt size met or exceeded the cap.

        Returns False when the cap is disabled (``cap_context_tokens <= 0``)
        or before the first turn has been recorded (``last_prompt_tokens == 0``),
        so a fresh session always gets at least one turn through.
        """
        if self.cap_context_tokens <= 0:
            return False
        return self.last_prompt_tokens >= self.cap_context_tokens

    def has_pricing(self) -> bool:
        return lookup_pricing(self.model) is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for SessionStore.save. ``model`` and ``cap_context_tokens``
        are intentionally omitted — both come from the live config on resume,
        not from the persisted snapshot."""
        data = asdict(self)
        data.pop("model", None)
        data.pop("cap_context_tokens", None)
        return data

    @classmethod
    def from_dict(
        cls,
        model: str,
        data: dict[str, Any] | None,
        cap_context_tokens: int = 0,
    ) -> "CostTracker":
        """Reconstruct from a SessionStore payload. Missing/extra fields tolerated.

        ``cap_context_tokens`` is supplied by the caller from the live config —
        it is intentionally not persisted, so changing the cap in config takes
        effect immediately on the next ``/resume``.
        """
        if not data:
            return cls(model=model, cap_context_tokens=cap_context_tokens)
        return cls(
            model=model,
            cap_context_tokens=cap_context_tokens,
            last_prompt_tokens=int(data.get("last_prompt_tokens", 0) or 0),
            total_input_billed=int(data.get("total_input_billed", 0) or 0),
            total_cached=int(data.get("total_cached", 0) or 0),
            total_output=int(data.get("total_output", 0) or 0),
            total_cost_usd=float(data.get("total_cost_usd", 0.0) or 0.0),
        )
