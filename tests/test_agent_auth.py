"""Tests for auto-reauth on expired Google Cloud credentials."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from google.auth import exceptions as auth_exceptions

from cfi_ai.agent import _is_auth_error, _run_reauth
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
