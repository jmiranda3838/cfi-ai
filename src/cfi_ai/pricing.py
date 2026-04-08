"""Static model pricing and context-window tables.

These power the bottom-toolbar context/cost readout. Verify against current
Vertex AI pricing when adding a new model — Google updates these periodically.

All rates are USD per 1,000,000 tokens. ``cached`` is the rate Vertex bills
when a prompt prefix hits the context cache (typically ~25% of ``input``).

Tiered pricing (e.g. gemini-2.5-pro charging more above 200k input tokens) is
not modeled here — single flat rate per model. Revisit if precision matters.
"""

from __future__ import annotations

# TODO: tiered pricing for models that price differently above 200k input tokens.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-pro":         {"input": 1.25, "cached": 0.3125, "output": 10.0},
    "gemini-2.5-flash":       {"input": 0.30, "cached": 0.075,  "output":  2.50},
    "gemini-2.5-flash-lite":  {"input": 0.10, "cached": 0.025,  "output":  0.40},
    "gemini-3-flash-preview": {"input": 0.30, "cached": 0.075,  "output":  2.50},
}

MODEL_CONTEXT_WINDOW: dict[str, int] = {
    "gemini-2.5-pro":         1_048_576,
    "gemini-2.5-flash":       1_048_576,
    "gemini-2.5-flash-lite":  1_048_576,
    "gemini-3-flash-preview": 1_048_576,
}


def normalize_model(model: str) -> str:
    """Strip Vertex publisher prefixes / version suffixes for table lookup.

    Examples:
        publishers/google/models/gemini-2.5-pro -> gemini-2.5-pro
        gemini-2.5-flash@001                    -> gemini-2.5-flash
    """
    return model.rsplit("/", 1)[-1].split("@", 1)[0]


def lookup_pricing(model: str) -> dict[str, float] | None:
    return MODEL_PRICING.get(normalize_model(model))


def lookup_context_window(model: str) -> int | None:
    return MODEL_CONTEXT_WINDOW.get(normalize_model(model))
