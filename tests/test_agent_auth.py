"""Tests for auto-reauth on expired Google Cloud credentials."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from google.auth import exceptions as auth_exceptions

from cfi_ai.agent import _is_auth_error, _rebuild_client_after_reauth, _run_reauth
from cfi_ai.main import _check_adc


# --- _check_adc (startup credential validation) ---


def test_check_adc_valid_credentials():
    """Valid credentials that refresh successfully — no subprocess spawned."""
    mock_creds = MagicMock()
    mock_creds.refresh.return_value = None
    with patch("google.auth.default", return_value=(mock_creds, "project")):
        _check_adc()  # should not raise
    mock_creds.refresh.assert_called_once()


def test_check_adc_expired_credentials_reauth_success():
    """Expired credentials trigger reauth; successful reauth continues normally."""
    mock_creds = MagicMock()
    mock_creds.refresh.side_effect = auth_exceptions.RefreshError("Token expired")
    with (
        patch("google.auth.default", return_value=(mock_creds, "project")),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        _check_adc()  # should not raise
    mock_run.assert_called_once_with(
        ["gcloud", "auth", "application-default", "login"],
    )


def test_check_adc_expired_credentials_reauth_failure():
    """Expired credentials + failed reauth → sys.exit(1)."""
    mock_creds = MagicMock()
    mock_creds.refresh.side_effect = auth_exceptions.RefreshError("Token expired")
    with (
        patch("google.auth.default", return_value=(mock_creds, "project")),
        patch("subprocess.run") as mock_run,
        pytest.raises(SystemExit) as exc_info,
    ):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1)
        _check_adc()
    assert exc_info.value.code == 1


def test_check_adc_expired_credentials_gcloud_missing():
    """Expired credentials + gcloud not installed → sys.exit(1)."""
    mock_creds = MagicMock()
    mock_creds.refresh.side_effect = auth_exceptions.RefreshError("Token expired")
    with (
        patch("google.auth.default", return_value=(mock_creds, "project")),
        patch("subprocess.run", side_effect=FileNotFoundError),
        pytest.raises(SystemExit) as exc_info,
    ):
        _check_adc()
    assert exc_info.value.code == 1


def test_check_adc_no_credentials():
    """Missing credentials → sys.exit(1) with helpful message."""
    with (
        patch(
            "google.auth.default",
            side_effect=auth_exceptions.DefaultCredentialsError("not found"),
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        _check_adc()
    assert exc_info.value.code == 1


# --- _is_auth_error ---


def test_direct_refresh_error():
    exc = auth_exceptions.RefreshError("Token has been revoked")
    assert _is_auth_error(exc) is True


def test_wrapped_refresh_error():
    cause = auth_exceptions.RefreshError("Token expired")
    exc = RuntimeError("stream failed")
    exc.__cause__ = cause
    assert _is_auth_error(exc) is True


def test_deeply_chained_refresh_error():
    root = auth_exceptions.RefreshError("expired")
    mid = ValueError("inner")
    mid.__cause__ = root
    outer = RuntimeError("outer")
    outer.__cause__ = mid
    assert _is_auth_error(outer) is True


def test_reauthentication_message_fallback():
    exc = Exception("Reauthentication is needed")
    assert _is_auth_error(exc) is True


def test_unrelated_error():
    exc = ValueError("something else")
    assert _is_auth_error(exc) is False


def test_context_chain():
    cause = auth_exceptions.RefreshError("expired")
    exc = RuntimeError("wrapper")
    exc.__context__ = cause
    assert _is_auth_error(exc) is True


# --- _run_reauth ---


def test_reauth_success():
    ui = MagicMock()
    with patch("cfi_ai.agent.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        assert _run_reauth(ui) is True
    mock_run.assert_called_once_with(
        ["gcloud", "auth", "application-default", "login"],
    )
    ui.print_info.assert_any_call(
        "Google Cloud credentials have expired. Launching reauthentication..."
    )


def test_reauth_failure():
    ui = MagicMock()
    with patch("cfi_ai.agent.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1)
        assert _run_reauth(ui) is False
    ui.print_error.assert_called_once()


def test_reauth_gcloud_not_found():
    ui = MagicMock()
    with patch("cfi_ai.agent.subprocess.run", side_effect=FileNotFoundError):
        assert _run_reauth(ui) is False
    ui.print_error.assert_called_once()
    assert "gcloud CLI not found" in ui.print_error.call_args[0][0]


# --- _rebuild_client_after_reauth ---


def test_rebuild_preserves_mid_session_model_swap():
    """A /model swap before reauth must survive the rebuild.

    Config is frozen, so Client(config) reverts to the original model.
    The helper must re-apply the live client's swapped model onto the
    rebuilt client; otherwise the next API call silently uses the wrong
    model and the cache_manager (still bound to the swapped model) ends
    up paired with a client that points at a different model.
    """
    config = MagicMock()
    config.model = "gemini-3-flash-preview"

    fresh_client = MagicMock()
    fresh_client.model = "gemini-3-flash-preview"
    fresh_client.genai_client = MagicMock()

    current_client = MagicMock()
    current_client.model = "gemini-3-pro-preview"  # post-/model swap

    with patch("cfi_ai.agent.Client", return_value=fresh_client) as ctor:
        result = _rebuild_client_after_reauth(
            config, current_client, None, "system", []
        )

    ctor.assert_called_once_with(config)
    fresh_client.set_model.assert_called_once_with("gemini-3-pro-preview")
    assert result is fresh_client


def test_rebuild_skips_set_model_when_no_swap():
    """Without a /model swap, the rebuilt client already has the right
    model — don't call set_model needlessly (it would drop the cache
    manager ref before we re-attach it)."""
    config = MagicMock()
    config.model = "gemini-3-flash-preview"

    fresh_client = MagicMock()
    fresh_client.model = "gemini-3-flash-preview"
    fresh_client.genai_client = MagicMock()

    current_client = MagicMock()
    current_client.model = "gemini-3-flash-preview"  # no swap

    with patch("cfi_ai.agent.Client", return_value=fresh_client):
        _rebuild_client_after_reauth(
            config, current_client, None, "system", []
        )

    fresh_client.set_model.assert_not_called()


def test_rebuild_resets_caches_with_swapped_model_client():
    """Reauth path with active caches: cache_manager.reset() must be called
    with the rebuilt client's genai_client, and _create_session_caches must
    fire so the new caches are bound to the swapped model.
    """
    config = MagicMock()
    config.model = "gemini-3-flash-preview"

    fresh_client = MagicMock()
    fresh_client.model = "gemini-3-flash-preview"
    fresh_client.genai_client = MagicMock()

    current_client = MagicMock()
    current_client.model = "gemini-3.1-pro-preview"  # post-/model swap

    cache_manager = MagicMock()

    with patch("cfi_ai.agent.Client", return_value=fresh_client), \
         patch("cfi_ai.agent._create_session_caches") as mock_create:
        result = _rebuild_client_after_reauth(
            config, current_client, cache_manager, "system", []
        )

    fresh_client.set_model.assert_called_once_with("gemini-3.1-pro-preview")
    cache_manager.reset.assert_called_once_with(fresh_client.genai_client)
    mock_create.assert_called_once_with(cache_manager, "system", [])
    fresh_client.set_cache_manager.assert_called_once_with(cache_manager)
    assert result is fresh_client
