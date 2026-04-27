"""Static model pricing and context-window tables.

These power the bottom-toolbar context/cost readout. Verify against current
Vertex AI pricing when adding a new model — Google updates these periodically.

All rates are USD per 1,000,000 tokens. ``cached`` is the rate Vertex bills
when a prompt prefix hits the context cache (typically ~10-25% of ``input``).

Some models (the Gemini 3 Pro family today) charge a higher long-context rate
once the prompt exceeds ``tier_threshold`` input tokens. Per Vertex docs the
flip applies to the entire call — input, cached, AND output are all billed at
``tier_rates`` whenever the prompt is over the threshold. Models with no
``tier_threshold`` key are billed at a single flat rate.
"""

from __future__ import annotations

from typing import Any

MODEL_PRICING: dict[str, dict[str, Any]] = {
    "gemini-2.5-pro":                       {"input": 1.25, "cached": 0.3125, "output": 10.0},
    "gemini-2.5-flash":                     {"input": 0.30, "cached": 0.075,  "output":  2.50},
    "gemini-2.5-flash-lite":                {"input": 0.10, "cached": 0.025,  "output":  0.40},
    "gemini-3-flash-preview":               {"input": 0.30, "cached": 0.075,  "output":  2.50},
    "gemini-3.1-pro-preview": {
        "input": 2.00, "cached": 0.20, "output": 12.00,
        "tier_threshold": 200_000,
        "tier_rates": {"input": 4.00, "cached": 0.40, "output": 18.00},
    },
    "gemini-3.1-pro-preview-customtools": {
        "input": 2.00, "cached": 0.20, "output": 12.00,
        "tier_threshold": 200_000,
        "tier_rates": {"input": 4.00, "cached": 0.40, "output": 18.00},
    },
}

MODEL_CONTEXT_WINDOW: dict[str, int] = {
    "gemini-2.5-pro":                       1_048_576,
    "gemini-2.5-flash":                     1_048_576,
    "gemini-2.5-flash-lite":                1_048_576,
    "gemini-3-flash-preview":               1_048_576,
    "gemini-3.1-pro-preview":               1_048_576,
    "gemini-3.1-pro-preview-customtools":   1_048_576,
}


def normalize_model(model: str) -> str:
    """Strip Vertex publisher prefixes / version suffixes for table lookup.

    Examples:
        publishers/google/models/gemini-2.5-pro -> gemini-2.5-pro
        gemini-2.5-flash@001                    -> gemini-2.5-flash
    """
    return model.rsplit("/", 1)[-1].split("@", 1)[0]


def lookup_pricing(model: str) -> dict[str, Any] | None:
    return MODEL_PRICING.get(normalize_model(model))


def lookup_context_window(model: str) -> int | None:
    return MODEL_CONTEXT_WINDOW.get(normalize_model(model))


def lookup_active_rates(model: str, prompt_tokens: int) -> dict[str, float] | None:
    """Return the per-call ``{input, cached, output}`` rate dict for a prompt size.

    For tiered models the long-context ``tier_rates`` are returned whenever
    ``prompt_tokens`` strictly exceeds ``tier_threshold`` (the Vertex docs
    phrase the rule as "longer than" the threshold, so an exact-threshold
    prompt stays in the standard tier). Flat-rate models ignore prompt size.
    Returns ``None`` for unknown models.
    """
    entry = MODEL_PRICING.get(normalize_model(model))
    if entry is None:
        return None
    threshold = entry.get("tier_threshold")
    if threshold is not None and prompt_tokens > threshold:
        tier = entry.get("tier_rates")
        if tier is not None:
            return {"input": tier["input"], "cached": tier["cached"], "output": tier["output"]}
    return {"input": entry["input"], "cached": entry["cached"], "output": entry["output"]}
