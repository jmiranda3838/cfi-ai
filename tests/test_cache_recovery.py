"""Tests for cache-expired error detection and recovery helpers."""

from unittest.mock import MagicMock as MM, patch

from google.genai import errors as genai_errors
from google.genai import types

from cfi_ai.agent import (
    _refresh_caches,
    _run_main_loop,
    _run_plan_mode,
    _try_recover_cache_expiry,
)
from cfi_ai.client import CacheManager, is_cache_expired_error
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


def test_refresh_caches_rebuilds_both():
    genai = MM()
    c1, c2, c3, c4 = MM(), MM(), MM(), MM()
    for i, c in enumerate([c1, c2, c3, c4], start=1):
        c.name = f"cache-{i}"
        c.usage_metadata.total_token_count = 100
    genai.caches.create.side_effect = [c1, c2, c3, c4]

    mgr = CacheManager(genai, model="m")
    with _PATCH_CONFIG:
        mgr.create_cache("normal", system="s", tools=MM())
        mgr.create_cache("plan", system="s2", tools=MM())

    with _PATCH_CONFIG:
        _refresh_caches(mgr, "s", MM(), "s2", MM())

    assert mgr.get_cache_name("normal") == "cache-3"
    assert mgr.get_cache_name("plan") == "cache-4"
    # The expired old caches were not server-side deleted (they're already gone)
    genai.caches.delete.assert_not_called()


def test_refresh_caches_survives_partial_failure():
    genai = MM()
    c1 = MM()
    c1.name = "cache-1"
    c1.usage_metadata.total_token_count = 100
    genai.caches.create.side_effect = [RuntimeError("transient"), c1]

    mgr = CacheManager(genai, model="m")
    with _PATCH_CONFIG:
        _refresh_caches(mgr, "s", MM(), "s2", MM())

    assert mgr.get_cache_name("normal") is None
    assert mgr.get_cache_name("plan") == "cache-1"


def test_run_plan_mode_retries_after_cache_expiry():
    """Loop-level: _run_plan_mode catches a cache-expired error at call time,
    calls _refresh_caches, and retries the request once."""
    expired = _make_client_error("INVALID_ARGUMENT", "Cache content 1 is expired.")

    # Build a successful StreamResult-like mock for the retry call.
    # Include an end_turn function call so the plan-mode loop terminates cleanly
    # on the first successful iteration.
    end_turn_fc = MM()
    end_turn_fc.name = END_TURN_TOOL_NAME
    success_stream = MM()
    success_stream.text_chunks.return_value = iter(["Here is the plan."])
    success_stream.parts = [
        types.Part.from_text(text="Here is the plan."),
        types.Part.from_function_call(name=END_TURN_TOOL_NAME, args={}),
    ]
    success_stream.function_calls = [end_turn_fc]
    success_stream.request_id = "rid"
    success_stream.log_completion = MM()

    mock_client = MM()
    # First call raises (call-time path is the simplest to mock — same retry plumbing
    # is exercised either way).
    mock_client.stream_response.side_effect = [expired, success_stream]

    mock_ui = MM()
    mock_ui.stream_markdown.return_value = "Here is the plan."

    mock_workspace = MM()
    mock_cache_manager = MM(spec=CacheManager)

    with patch("cfi_ai.agent._refresh_caches") as mock_refresh:
        result = _run_plan_mode(
            client=mock_client,
            ui=mock_ui,
            workspace=mock_workspace,
            plan_system_prompt="plan_sys",
            readonly_tools=MM(),
            messages=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])],
            cache_manager=mock_cache_manager,
            system_prompt="sys",
            api_tools=MM(),
        )

    # Refresh fired exactly once
    mock_refresh.assert_called_once()
    # stream_response was called twice (initial + retry)
    assert mock_client.stream_response.call_count == 2
    # User saw the recovery message
    mock_ui.print_info.assert_any_call("Session cache expired, refreshing...")
    # And the result is populated from the successful retry
    assert result.plan_text is not None


def test_run_plan_mode_no_retry_when_cache_manager_missing():
    """Without cache_manager, the recovery branch is skipped and the error surfaces."""
    expired = _make_client_error("INVALID_ARGUMENT", "Cache content 1 is expired.")

    mock_client = MM()
    mock_client.stream_response.side_effect = expired

    mock_ui = MM()
    mock_workspace = MM()

    with patch("cfi_ai.agent._refresh_caches") as mock_refresh:
        result = _run_plan_mode(
            client=mock_client,
            ui=mock_ui,
            workspace=mock_workspace,
            plan_system_prompt="plan_sys",
            readonly_tools=MM(),
            messages=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])],
        )

    mock_refresh.assert_not_called()
    assert mock_client.stream_response.call_count == 1
    assert result.plan_text is None


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
            "plan_sys",
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
            "plan_sys",
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
            "plan_sys",
            MM(),
            location="call",
        )

    assert result is False
    mock_refresh.assert_not_called()
    mock_ui.print_info.assert_not_called()


def test_run_plan_mode_recovers_from_two_consecutive_expiries():
    """The cache-retry gate must reset after a successful retry, so a second
    expiry within the same _run_plan_mode call can also be recovered."""
    expired1 = _make_client_error("INVALID_ARGUMENT", "Cache content 1 is expired.")
    expired2 = _make_client_error("INVALID_ARGUMENT", "Cache content 2 is expired.")

    # First success: returns an interview tool call so the loop iterates again.
    # Empty questions list means _handle_interview returns immediately without
    # touching ui.run_interview or workspace.
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

    # Second success: end_turn so the loop terminates cleanly
    end_turn_fc = MM()
    end_turn_fc.name = END_TURN_TOOL_NAME
    success2 = MM()
    success2.text_chunks.return_value = iter(["Here is the plan."])
    success2.parts = [
        types.Part.from_text(text="Here is the plan."),
        types.Part.from_function_call(name=END_TURN_TOOL_NAME, args={}),
    ]
    success2.function_calls = [end_turn_fc]
    success2.request_id = "rid2"
    success2.log_completion = MM()

    mock_client = MM()
    mock_client.stream_response.side_effect = [expired1, success1, expired2, success2]

    mock_ui = MM()
    mock_ui.stream_markdown.side_effect = ["", "Here is the plan."]
    mock_workspace = MM()
    mock_cache_manager = MM(spec=CacheManager)

    with patch("cfi_ai.agent._refresh_caches") as mock_refresh:
        result = _run_plan_mode(
            client=mock_client,
            ui=mock_ui,
            workspace=mock_workspace,
            plan_system_prompt="plan_sys",
            readonly_tools=MM(),
            messages=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])],
            cache_manager=mock_cache_manager,
            system_prompt="sys",
            api_tools=MM(),
        )

    # Refresh fired exactly twice (once per expiry, proving gate was reset)
    assert mock_refresh.call_count == 2
    # stream_response was called four times (initial + retry + retry + retry)
    assert mock_client.stream_response.call_count == 4
    # Final result populated from the last successful retry
    assert result.plan_text is not None


def test_run_main_loop_recovers_from_two_consecutive_expiries():
    """Same gate-reset behavior for _run_main_loop: a second cache expiry
    within the same user-input cycle must also recover."""
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

    mock_client = MM()
    mock_client.stream_response.side_effect = [expired1, success1, expired2, success2]

    mock_ui = MM()
    # One real input, then None to exit the outer while loop
    mock_ui.get_input.side_effect = [UserInput(text="hi", plan_mode=False), None]
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
            readonly_api_tools=MM(),
            plan_system_prompt="plan_sys",
            cache_manager=mock_cache_manager,
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
            "plan_sys",
            MM(),
            location="stream",
        )

    assert result is True
    mock_refresh.assert_called_once()
