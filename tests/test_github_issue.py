"""Tests for the /bugreport GitHub REST helper (``cfi_ai.github_issue``)."""

import json
import os
import subprocess
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from cfi_ai.github_issue import (
    _BODY_LIMIT,
    _truncate_body,
    create_issue,
    discover_token,
)


# ── discover_token ───────────────────────────────────────────────────


def test_discover_token_env_precedence():
    """GITHUB_TOKEN set → returned; subprocess must not be called."""
    with patch.dict(os.environ, {"GITHUB_TOKEN": "env-token"}, clear=True):
        with patch("cfi_ai.github_issue.subprocess.run") as mock_run:
            token = discover_token()
    assert token == "env-token"
    mock_run.assert_not_called()


def test_discover_token_gh_token_fallback():
    """GH_TOKEN used when GITHUB_TOKEN is missing; subprocess still not called."""
    with patch.dict(os.environ, {"GH_TOKEN": "gh-env-token"}, clear=True):
        with patch("cfi_ai.github_issue.subprocess.run") as mock_run:
            token = discover_token()
    assert token == "gh-env-token"
    mock_run.assert_not_called()


def test_discover_token_falls_back_to_gh_cli():
    """With no env tokens, falls back to ``gh auth token``."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("cfi_ai.github_issue.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="cli-token\n", stderr=""
            )
            token = discover_token()
    assert token == "cli-token"
    mock_run.assert_called_once()


def test_discover_token_returns_none_when_gh_missing():
    """No env tokens and no ``gh`` binary → returns None."""
    with patch.dict(os.environ, {}, clear=True):
        with patch(
            "cfi_ai.github_issue.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            assert discover_token() is None


def test_discover_token_returns_none_when_gh_fails():
    """``gh auth token`` returns non-zero → None."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("cfi_ai.github_issue.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="not logged in"
            )
            assert discover_token() is None


# ── _truncate_body ───────────────────────────────────────────────────


def test_truncate_body_under_limit():
    """Body under the limit is returned verbatim."""
    body = "x" * 100
    assert _truncate_body(body) == body


def test_truncate_body_exactly_at_limit():
    """Body exactly at the limit is returned verbatim (boundary case)."""
    body = "x" * _BODY_LIMIT
    assert _truncate_body(body) == body


def test_truncate_body_over_limit():
    """Body over the limit is truncated and ends with a marker; total ≤ limit."""
    body = "x" * (_BODY_LIMIT + 500)
    truncated = _truncate_body(body)
    assert len(truncated) <= _BODY_LIMIT
    assert truncated.endswith("chars]")
    assert "truncated" in truncated


# ── create_issue ─────────────────────────────────────────────────────


def _make_urlopen_response(body: dict, status: int = 201):
    """Build a context-manager-compatible mock for urllib.request.urlopen."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = json.dumps(body).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = False
    return cm


def test_create_issue_success():
    """Happy path: returns html_url; verifies POST URL, headers, and body."""
    with patch("cfi_ai.github_issue.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _make_urlopen_response(
            {"html_url": "https://github.com/o/r/issues/42"}
        )
        url = create_issue(
            repo="o/r",
            title="T",
            body="B",
            labels=["bug"],
            token="tok",
        )
    assert url == "https://github.com/o/r/issues/42"
    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://api.github.com/repos/o/r/issues"
    assert req.get_method() == "POST"
    assert req.headers["Authorization"] == "Bearer tok"
    assert req.headers["X-github-api-version"] == "2022-11-28"
    assert req.headers["Content-type"] == "application/json"
    payload = json.loads(req.data)
    assert payload == {"title": "T", "body": "B", "labels": ["bug"]}


def test_create_issue_http_error_includes_github_message():
    """HTTPError whose body contains a GitHub ``message`` surfaces it in the
    RuntimeError text."""
    err = urllib.error.HTTPError(
        url="https://api.github.com/repos/o/r/issues",
        code=422,
        msg="Unprocessable Entity",
        hdrs=None,
        fp=None,
    )
    err.read = MagicMock(return_value=b'{"message":"Invalid labels"}')
    with patch("cfi_ai.github_issue.urllib.request.urlopen", side_effect=err):
        with pytest.raises(RuntimeError) as excinfo:
            create_issue("o/r", "T", "B", ["bug"], token="tok")
    msg = str(excinfo.value)
    assert "HTTP 422" in msg
    assert "Invalid labels" in msg


def test_create_issue_network_error():
    """URLError surfaces as a user-friendly network-error RuntimeError."""
    err = urllib.error.URLError("refused")
    with patch("cfi_ai.github_issue.urllib.request.urlopen", side_effect=err):
        with pytest.raises(RuntimeError) as excinfo:
            create_issue("o/r", "T", "B", ["bug"], token="tok")
    assert "Network error" in str(excinfo.value)


def test_create_issue_missing_token_raises():
    """No env, no gh CLI, no explicit token → RuntimeError about auth."""
    with patch.dict(os.environ, {}, clear=True):
        with patch(
            "cfi_ai.github_issue.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(RuntimeError) as excinfo:
                create_issue("o/r", "T", "B", ["bug"])
    assert "GitHub token" in str(excinfo.value)
