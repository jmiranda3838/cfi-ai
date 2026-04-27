"""Tests for CostTracker math, formatting, and serialization."""

from __future__ import annotations

from types import SimpleNamespace

from cfi_ai.cost_tracker import CostTracker
from cfi_ai.pricing import MODEL_CONTEXT_WINDOW, MODEL_PRICING, lookup_active_rates
from cfi_ai.ui import _format_cost_segment, _format_tokens


def _usage(prompt: int, cached: int, output: int) -> SimpleNamespace:
    """Stand-in for ``GenerateContentResponseUsageMetadata`` — CostTracker
    only reads attributes via getattr, so a SimpleNamespace is enough."""
    return SimpleNamespace(
        prompt_token_count=prompt,
        cached_content_token_count=cached,
        candidates_token_count=output,
        total_token_count=prompt + output,
    )


# --- record() math ---

def test_record_single_turn_no_cache():
    t = CostTracker(model="gemini-2.5-flash")
    t.record(_usage(prompt=10_000, cached=0, output=2_000))

    assert t.last_prompt_tokens == 10_000
    assert t.total_input_billed == 10_000
    assert t.total_cached == 0
    assert t.total_output == 2_000

    rates = MODEL_PRICING["gemini-2.5-flash"]
    expected = (10_000 * rates["input"] + 2_000 * rates["output"]) / 1_000_000
    assert t.total_cost_usd == expected


def test_record_single_turn_with_cache():
    """Cached portion is billed at the cached rate; the rest at the input rate."""
    t = CostTracker(model="gemini-2.5-flash")
    t.record(_usage(prompt=10_000, cached=4_000, output=500))

    assert t.last_prompt_tokens == 10_000
    assert t.total_input_billed == 6_000  # 10000 - 4000
    assert t.total_cached == 4_000
    assert t.total_output == 500

    rates = MODEL_PRICING["gemini-2.5-flash"]
    expected = (
        6_000 * rates["input"] + 4_000 * rates["cached"] + 500 * rates["output"]
    ) / 1_000_000
    assert t.total_cost_usd == expected


def test_record_two_turns_accumulates_cost_but_replaces_context_indicator():
    """last_prompt_tokens MUST be the most recent prompt size (not a sum) —
    it represents the current context-window snapshot. total_cost_usd, by
    contrast, accumulates across turns."""
    t = CostTracker(model="gemini-2.5-pro")
    t.record(_usage(prompt=20_000, cached=0, output=1_000))
    t.record(_usage(prompt=22_500, cached=18_000, output=1_500))

    assert t.last_prompt_tokens == 22_500
    assert t.total_input_billed == 20_000 + 4_500  # 22500 - 18000
    assert t.total_cached == 18_000
    assert t.total_output == 2_500

    rates = MODEL_PRICING["gemini-2.5-pro"]
    turn1 = (20_000 * rates["input"] + 1_000 * rates["output"]) / 1_000_000
    turn2 = (
        4_500 * rates["input"] + 18_000 * rates["cached"] + 1_500 * rates["output"]
    ) / 1_000_000
    assert t.total_cost_usd == turn1 + turn2


def test_record_unknown_model_skips_cost_but_still_counts_tokens():
    t = CostTracker(model="not-a-real-model")
    t.record(_usage(prompt=5_000, cached=0, output=500))

    assert t.last_prompt_tokens == 5_000
    assert t.total_input_billed == 5_000
    assert t.total_output == 500
    assert t.total_cost_usd == 0.0
    assert not t.has_pricing()
    assert t.context_window() is None


def test_record_handles_none_usage_safely():
    t = CostTracker(model="gemini-2.5-flash")
    t.record(None)
    assert t.last_prompt_tokens == 0
    assert t.total_cost_usd == 0.0


def test_record_handles_partially_populated_usage():
    """Some streaming responses leave fields as None — getattr fallbacks must hold."""
    t = CostTracker(model="gemini-2.5-flash")
    t.record(SimpleNamespace(prompt_token_count=1_000))  # only one field
    assert t.last_prompt_tokens == 1_000
    assert t.total_output == 0


def test_cached_minus_prompt_floored_at_zero():
    """Defensive: if Vertex ever reports cached > prompt, billed_input must
    not go negative."""
    t = CostTracker(model="gemini-2.5-flash")
    t.record(_usage(prompt=1_000, cached=5_000, output=100))
    assert t.total_input_billed == 0


# --- to_dict / from_dict round-trip ---

def test_to_dict_omits_model():
    """model lives in config, not in the persisted payload — on resume the
    live config wins."""
    t = CostTracker(model="gemini-2.5-pro", last_prompt_tokens=42)
    d = t.to_dict()
    assert "model" not in d
    assert d["last_prompt_tokens"] == 42


def test_from_dict_round_trip():
    original = CostTracker(model="gemini-2.5-flash")
    original.record(_usage(prompt=10_000, cached=2_000, output=500))
    original.record(_usage(prompt=12_500, cached=10_000, output=800))

    payload = original.to_dict()
    restored = CostTracker.from_dict("gemini-2.5-flash", payload)

    assert restored.model == "gemini-2.5-flash"
    assert restored.last_prompt_tokens == original.last_prompt_tokens
    assert restored.total_input_billed == original.total_input_billed
    assert restored.total_cached == original.total_cached
    assert restored.total_output == original.total_output
    assert restored.total_cost_usd == original.total_cost_usd


def test_from_dict_none_returns_fresh_tracker():
    t = CostTracker.from_dict("gemini-2.5-flash", None)
    assert t.last_prompt_tokens == 0
    assert t.total_cost_usd == 0.0


def test_from_dict_tolerates_missing_fields():
    t = CostTracker.from_dict("gemini-2.5-flash", {"last_prompt_tokens": 100})
    assert t.last_prompt_tokens == 100
    assert t.total_input_billed == 0


# --- formatting helpers ---

def test_format_tokens():
    assert _format_tokens(0) == "0"
    assert _format_tokens(950) == "950"
    assert _format_tokens(1_500) == "2k"  # rounds
    assert _format_tokens(12_345) == "12k"
    assert _format_tokens(1_048_576) == "1.0M"
    assert _format_tokens(1_500_000) == "1.5M"


def test_format_cost_segment_empty_when_no_tracker():
    assert _format_cost_segment(None) == ""


def test_format_cost_segment_empty_before_first_turn():
    t = CostTracker(model="gemini-2.5-flash")
    assert _format_cost_segment(t) == ""


def test_format_cost_segment_known_model_shows_ctx_pct_and_cost():
    t = CostTracker(model="gemini-2.5-flash")
    t.record(_usage(prompt=10_000, cached=0, output=1_000))
    seg = _format_cost_segment(t)
    assert "ctx 10k/1.0M" in seg
    assert "(1%)" in seg
    assert "$" in seg


def test_format_cost_segment_unknown_model_drops_pct_and_cost():
    t = CostTracker(model="not-a-real-model")
    t.record(_usage(prompt=10_000, cached=0, output=1_000))
    seg = _format_cost_segment(t)
    assert seg == "ctx 10k"


# --- context cap (cap_context_tokens) ---


def test_context_window_cap_smaller_than_model_window_wins():
    t = CostTracker(model="gemini-2.5-flash", cap_context_tokens=128_000)
    assert t.context_window() == 128_000  # min(1_048_576, 128_000)


def test_context_window_no_cap_returns_model_window():
    t = CostTracker(model="gemini-2.5-flash", cap_context_tokens=0)
    assert t.context_window() == 1_048_576


def test_context_window_cap_larger_than_model_window_caps_at_model():
    """A cap higher than the model's native window must not exceed the model's
    actual hard limit — the API will reject anything above it."""
    t = CostTracker(model="gemini-2.5-flash", cap_context_tokens=5_000_000)
    assert t.context_window() == 1_048_576


def test_context_window_unknown_model_with_cap_returns_cap():
    """When the model has no known window, the cap stands alone."""
    t = CostTracker(model="not-a-real-model", cap_context_tokens=128_000)
    assert t.context_window() == 128_000


def test_context_window_unknown_model_no_cap_returns_none():
    t = CostTracker(model="not-a-real-model", cap_context_tokens=0)
    assert t.context_window() is None


def test_cap_reached_false_before_first_turn():
    """A fresh session must always be allowed to send at least one turn."""
    t = CostTracker(model="gemini-2.5-flash", cap_context_tokens=128_000)
    assert not t.cap_reached()


def test_cap_reached_false_below_cap():
    t = CostTracker(
        model="gemini-2.5-flash",
        cap_context_tokens=128_000,
        last_prompt_tokens=127_999,
    )
    assert not t.cap_reached()


def test_cap_reached_true_at_exact_cap():
    """Boundary: hitting the cap exactly counts as reached."""
    t = CostTracker(
        model="gemini-2.5-flash",
        cap_context_tokens=128_000,
        last_prompt_tokens=128_000,
    )
    assert t.cap_reached()


def test_cap_reached_true_above_cap():
    t = CostTracker(
        model="gemini-2.5-flash",
        cap_context_tokens=128_000,
        last_prompt_tokens=200_000,
    )
    assert t.cap_reached()


def test_cap_reached_false_when_cap_zero():
    """A cap of 0 disables the cap entirely, regardless of token count."""
    t = CostTracker(
        model="gemini-2.5-flash",
        cap_context_tokens=0,
        last_prompt_tokens=999_999_999,
    )
    assert not t.cap_reached()


def test_cap_reached_false_when_cap_negative():
    t = CostTracker(
        model="gemini-2.5-flash",
        cap_context_tokens=-1,
        last_prompt_tokens=999_999_999,
    )
    assert not t.cap_reached()


def test_to_dict_omits_cap_context_tokens():
    """The cap is a config-time value, not a per-session pin — on resume the
    live config wins."""
    t = CostTracker(
        model="gemini-2.5-flash",
        cap_context_tokens=128_000,
        last_prompt_tokens=50_000,
    )
    d = t.to_dict()
    assert "cap_context_tokens" not in d
    assert d["last_prompt_tokens"] == 50_000


def test_from_dict_applies_fresh_cap_not_persisted():
    """Resuming a session under a smaller cap must immediately reflect the new
    cap, not whatever value (if any) was in the persisted snapshot."""
    payload = {"last_prompt_tokens": 100_000}
    restored = CostTracker.from_dict(
        "gemini-2.5-flash", payload, cap_context_tokens=50_000
    )
    assert restored.cap_context_tokens == 50_000
    assert restored.last_prompt_tokens == 100_000
    assert restored.cap_reached()  # 100_000 >= 50_000


def test_from_dict_none_with_cap_returns_fresh_capped_tracker():
    t = CostTracker.from_dict("gemini-2.5-flash", None, cap_context_tokens=128_000)
    assert t.cap_context_tokens == 128_000
    assert t.last_prompt_tokens == 0
    assert not t.cap_reached()


def test_format_cost_segment_with_cap_shows_capped_window():
    """When a cap is configured, the toolbar denominator must reflect it."""
    t = CostTracker(model="gemini-2.5-flash", cap_context_tokens=128_000)
    t.record(_usage(prompt=64_000, cached=0, output=1_000))
    seg = _format_cost_segment(t)
    assert "ctx 64k/128k" in seg
    assert "(50%)" in seg


# --- tiered pricing (Gemini 3 Pro family: 200k input threshold) ---


def test_default_model_registered_in_pricing_and_context_tables():
    """Guardrail: the current default model must always have pricing + context
    info registered, or the toolbar silently drops cost/percentage."""
    assert "gemini-3.1-pro-preview-customtools" in MODEL_PRICING
    assert "gemini-3.1-pro-preview-customtools" in MODEL_CONTEXT_WINDOW


def test_lookup_active_rates_below_threshold_returns_standard_rates():
    rates = lookup_active_rates("gemini-3.1-pro-preview-customtools", 100_000)
    assert rates == {"input": 2.00, "cached": 0.20, "output": 12.00}


def test_lookup_active_rates_above_threshold_returns_long_context_rates():
    rates = lookup_active_rates("gemini-3.1-pro-preview-customtools", 500_000)
    assert rates == {"input": 4.00, "cached": 0.40, "output": 18.00}


def test_lookup_active_rates_at_exact_threshold_stays_standard():
    """Per Vertex docs: 'longer than 200K' — exactly 200,000 stays in the standard tier."""
    rates = lookup_active_rates("gemini-3.1-pro-preview-customtools", 200_000)
    assert rates == {"input": 2.00, "cached": 0.20, "output": 12.00}


def test_lookup_active_rates_flat_model_ignores_prompt_size():
    """Flat-rate models return the same rates regardless of prompt size."""
    rates = lookup_active_rates("gemini-2.5-flash", 5_000_000)
    assert rates == {"input": 0.30, "cached": 0.075, "output": 2.50}


def test_lookup_active_rates_unknown_model_returns_none():
    assert lookup_active_rates("not-a-real-model", 1_000) is None


def test_record_tiered_below_threshold_uses_standard_rates():
    t = CostTracker(model="gemini-3.1-pro-preview-customtools")
    t.record(_usage(prompt=100_000, cached=0, output=1_000))
    expected = (100_000 * 2.00 + 1_000 * 12.00) / 1_000_000
    assert t.total_cost_usd == expected


def test_record_tiered_above_threshold_flips_input_cached_and_output():
    """The whole call is billed at long-context rates when prompt > 200k —
    not just the input portion. Verifies all three rates flip together."""
    t = CostTracker(model="gemini-3.1-pro-preview-customtools")
    t.record(_usage(prompt=300_000, cached=50_000, output=2_000))
    # billed_input = 250_000, cached = 50_000, output = 2_000
    expected = (
        250_000 * 4.00      # long-context input rate
        + 50_000 * 0.40     # long-context cached rate
        + 2_000 * 18.00     # long-context output rate
    ) / 1_000_000
    assert t.total_cost_usd == expected


def test_record_tiered_at_exact_threshold_uses_standard_rates():
    """Boundary check: prompt of exactly 200_000 stays at the standard tier."""
    t = CostTracker(model="gemini-3.1-pro-preview-customtools")
    t.record(_usage(prompt=200_000, cached=0, output=100))
    expected = (200_000 * 2.00 + 100 * 12.00) / 1_000_000
    assert t.total_cost_usd == expected


def test_record_tiered_just_above_threshold_flips():
    """Boundary check: prompt of 200_001 flips to long-context rates."""
    t = CostTracker(model="gemini-3.1-pro-preview-customtools")
    t.record(_usage(prompt=200_001, cached=0, output=100))
    expected = (200_001 * 4.00 + 100 * 18.00) / 1_000_000
    assert t.total_cost_usd == expected


def test_record_tiered_two_turns_apply_per_turn_tier():
    """Each turn picks its tier based on its own prompt size — totals don't
    promote earlier turns to long-context just because a later turn was big."""
    t = CostTracker(model="gemini-3.1-pro-preview-customtools")
    t.record(_usage(prompt=50_000, cached=0, output=500))   # standard
    t.record(_usage(prompt=400_000, cached=0, output=1_000))  # long-context
    turn1 = (50_000 * 2.00 + 500 * 12.00) / 1_000_000
    turn2 = (400_000 * 4.00 + 1_000 * 18.00) / 1_000_000
    assert t.total_cost_usd == turn1 + turn2
