"""Tests for cache-expired error detection and recovery helpers."""

from unittest.mock import MagicMock as MM, patch

from google.genai import errors as genai_errors
from google.genai import types

from cfi_ai.agent import (
    _refresh_caches,
    _run_main_loop,
    _try_recover_cache_expiry,
)
from cfi_ai.client import CacheManager, is_cache_expired_error
from cfi_ai.cost_tracker import CostTracker
from cfi_ai.tools import END_TURN_TOOL_NAME, INTERVIEW_TOOL_NAME
from cfi_ai.ui import UserInput

_PATCH_CONFIG = patch("cfi_ai.client.types.CreateCachedContentConfig", MM)


def _make_client_error(status: str, message: str, code: int = 400) -> genai_errors.ClientError:
    """Construct a real ClientError via its public constructor."""
    return genai_errors.ClientError(
        code=code,
        response_json={
            "error": {
                "code": code,
                "status": status,
                "message": message,
            }
        },
    )


def test_detects_typed_client_error():
    err = _make_client_error("INVALID_ARGUMENT", "Cache content 4199075210449649664 is expired.")
    assert is_cache_expired_error(err)


def test_detects_wrapped_via_string_match():
    inner = RuntimeError("Cache content 123 is expired. INVALID_ARGUMENT")
    wrapper = RuntimeError("stream failed")
    wrapper.__cause__ = inner
    assert is_cache_expired_error(wrapper)


def test_walks_cause_chain_typed():
    inner = _make_client_error("INVALID_ARGUMENT", "Cache content 1 is expired.")
    outer = RuntimeError("stream wrapper")
    outer.__cause__ = inner
    assert is_cache_expired_error(outer)


def test_ignores_other_400_errors():
    err = _make_client_error("INVALID_ARGUMENT", "Some unrelated bad request")
    assert not is_cache_expired_error(err)


def test_ignores_unrelated_exception():
    assert not is_cache_expired_error(ValueError("nope"))


def test_detects_404_not_found_after_gc():
    """Once Vertex GCs the expired cache server-side, hitting it returns
    404 NOT_FOUND with a different message than the 400 'is expired' variant.
    Both must trigger the same recovery path."""
    err = _make_client_error(
        "NOT_FOUND",
        "Not found: cached content metadata for 2885853637886607360.",
        code=404,
    )
    assert is_cache_expired_error(err)


def test_detects_404_wrapped_in_cause_chain():
    """Stream-time 404s arrive wrapped — string fallback must catch them."""
    inner = _make_client_error(
        "NOT_FOUND",
        "Not found: cached content metadata for 12345.",
        code=404,
    )
    wrapper = RuntimeError("stream aborted")
    wrapper.__cause__ = inner
    assert is_cache_expired_error(wrapper)


def test_ignores_unrelated_404_errors():
    """A 404 for a different resource (e.g. model name) must not trigger
    cache recovery."""
    err = _make_client_error(
        "NOT_FOUND",
        "Model not found: gemini-x.",
        code=404,
    )
    assert not is_cache_expired_error(err)


def test_refresh_caches_rebuilds_normal():
    genai = MM()
    c1, c2 = MM(), MM()
    for i, c in enumerate([c1, c2], start=1):
        c.name = f"cache-{i}"
        c.usage_metadata.total_token_count = 100
    genai.caches.create.side_effect = [c1, c2]

    mgr = CacheManager(genai, model="m")
    with _PATCH_CONFIG:
        mgr.create_cache("normal", system="s", tools=MM())

    with _PATCH_CONFIG:
        _refresh_caches(mgr, "s", MM())

    assert mgr.get_cache_name("normal") == "cache-2"
    # The expired old cache was not server-side deleted (it's already gone)
    genai.caches.delete.assert_not_called()


def test_refresh_caches_survives_failure():
    genai = MM()
    genai.caches.create.side_effect = RuntimeError("transient")

    mgr = CacheManager(genai, model="m")
    with _PATCH_CONFIG:
        _refresh_caches(mgr, "s", MM())

    assert mgr.get_cache_name("normal") is None


def test_try_recover_cache_expiry_happy_path():
    """Cache-expired error + full state → refresh runs and helper returns True."""
    expired = _make_client_error("INVALID_ARGUMENT", "Cache content 42 is expired.")
    mock_ui = MM()
    mock_cache_manager = MM(spec=CacheManager)

    with patch("cfi_ai.agent._refresh_caches") as mock_refresh:
        result = _try_recover_cache_expiry(
            expired,
            mock_ui,
            mock_cache_manager,
            "sys",
            MM(),
            location="call",
        )

    assert result is True
    mock_refresh.assert_called_once()
    mock_ui.print_info.assert_called_once_with("Session cache expired, refreshing...")


def test_try_recover_cache_expiry_returns_false_for_unrelated_error():
    """An unrelated exception is left alone — no refresh, no UI noise."""
    mock_ui = MM()
    mock_cache_manager = MM(spec=CacheManager)

    with patch("cfi_ai.agent._refresh_caches") as mock_refresh:
        result = _try_recover_cache_expiry(
            ValueError("nope"),
            mock_ui,
            mock_cache_manager,
            "sys",
            MM(),
            location="call",
        )

    assert result is False
    mock_refresh.assert_not_called()
    mock_ui.print_info.assert_not_called()


def test_try_recover_cache_expiry_returns_false_when_state_missing():
    """Even on a real cache-expired error, missing state means no recovery."""
    expired = _make_client_error("INVALID_ARGUMENT", "Cache content 1 is expired.")
    mock_ui = MM()

    with patch("cfi_ai.agent._refresh_caches") as mock_refresh:
        result = _try_recover_cache_expiry(
            expired,
            mock_ui,
            None,  # cache_manager missing
            "sys",
            MM(),
            location="call",
        )

    assert result is False
    mock_refresh.assert_not_called()
    mock_ui.print_info.assert_not_called()


def test_run_main_loop_recovers_from_two_consecutive_expiries():
    """Gate-reset behavior for _run_main_loop: a second cache expiry within
    the same user-input cycle must also recover."""
    expired1 = _make_client_error("INVALID_ARGUMENT", "Cache content 1 is expired.")
    expired2 = _make_client_error("INVALID_ARGUMENT", "Cache content 2 is expired.")

    # First success: interview tool call (empty questions, no workspace/UI side
    # effects) so the inner loop iterates to a second stream_response call.
    interview_fc = MM()
    interview_fc.name = INTERVIEW_TOOL_NAME
    interview_fc.args = {"questions": []}
    success1 = MM()
    success1.text_chunks.return_value = iter([""])
    success1.parts = [
        types.Part.from_function_call(name=INTERVIEW_TOOL_NAME, args={"questions": []}),
    ]
    success1.function_calls = [interview_fc]
    success1.request_id = "rid1"
    success1.log_completion = MM()
    success1.usage_metadata = None  # CostTracker.record() skips None

    # Second success: end_turn alone, terminates the inner loop
    end_turn_fc = MM()
    end_turn_fc.name = END_TURN_TOOL_NAME
    success2 = MM()
    success2.text_chunks.return_value = iter(["done"])
    success2.parts = [
        types.Part.from_text(text="done"),
        types.Part.from_function_call(name=END_TURN_TOOL_NAME, args={}),
    ]
    success2.function_calls = [end_turn_fc]
    success2.request_id = "rid2"
    success2.log_completion = MM()
    success2.usage_metadata = None

    mock_client = MM()
    mock_client.stream_response.side_effect = [expired1, success1, expired2, success2]

    mock_ui = MM()
    # One real input, then None to exit the outer while loop
    mock_ui.get_input.side_effect = [UserInput(text="hi"), None]
    mock_ui.stream_markdown.side_effect = ["", "done"]

    mock_workspace = MM()
    mock_config = MM()
    mock_cache_manager = MM(spec=CacheManager)

    with patch("cfi_ai.agent._refresh_caches") as mock_refresh:
        _run_main_loop(
            client=mock_client,
            ui=mock_ui,
            workspace=mock_workspace,
            system_prompt="sys",
            config=mock_config,
            messages=[],
            api_tools=MM(),
            cache_manager=mock_cache_manager,
            session_store=MM(),
            cost_tracker=CostTracker(model="gemini-2.5-flash"),
        )

    # Refresh fired exactly twice (one per expiry, proving the gate was reset
    # after the first successful retry inside the same user-input cycle)
    assert mock_refresh.call_count == 2
    # stream_response was called four times (initial + retry + iterate + retry)
    assert mock_client.stream_response.call_count == 4


def test_try_recover_cache_expiry_walks_wrapped_exception():
    """Stream-time errors arrive wrapped — helper must walk the cause chain."""
    inner = _make_client_error("INVALID_ARGUMENT", "Cache content 99 is expired.")
    wrapper = RuntimeError("stream aborted")
    wrapper.__cause__ = inner
    mock_ui = MM()
    mock_cache_manager = MM(spec=CacheManager)

    with patch("cfi_ai.agent._refresh_caches") as mock_refresh:
        result = _try_recover_cache_expiry(
            wrapper,
            mock_ui,
            mock_cache_manager,
            "sys",
            MM(),
            location="stream",
        )

    assert result is True
    mock_refresh.assert_called_once()
