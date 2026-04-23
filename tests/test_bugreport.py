"""Tests for the /bugreport map (``cfi_ai.maps.bugreport``).

Patch targets: everything external is imported into ``cfi_ai.maps.bugreport``
by name (``from cfi_ai.github_issue import create_issue, discover_token``,
``from google import genai``, ``from cfi_ai.config import Config``), so tests
patch ``cfi_ai.maps.bugreport.<name>`` — patching the origin module does NOT
intercept the handler's calls.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from cfi_ai import sessions as sessions_mod
from cfi_ai.config import Config
from cfi_ai.maps.bugreport import (
    _SUMMARY_TIMEOUT_MS,
    _build_issue_body,
    _call_summarizer,
    _confirm_post,
    _edit_in_editor,
    _normalize_finish_reason,
    _resolve_editor_command,
    handle_bugreport,
)
from cfi_ai.sessions import SessionStore
from cfi_ai.workspace import Workspace


# ── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    fake = tmp_path / "sessions"
    monkeypatch.setattr(sessions_mod, "SESSIONS_DIR", fake)
    return fake


@pytest.fixture
def workspace(tmp_path):
    ws_root = tmp_path / "ws"
    ws_root.mkdir()
    return Workspace(str(ws_root))


@pytest.fixture
def populated_store(sessions_dir, workspace):
    """A SessionStore whose on-disk JSON file already exists with one message."""
    store = SessionStore(workspace)
    msg = types.Content(
        role="user", parts=[types.Part.from_text(text="hello world")]
    )
    store.save([msg])
    return store


def _make_config(**overrides) -> Config:
    defaults = dict(
        project="test-proj",
        location="global",
        model="gemini-3-flash-preview",
        max_tokens=8192,
        bugreport_enabled=True,
        bugreport_repo="jmiranda3838/cfi-ai",
        bugreport_dry_run=False,
    )
    defaults.update(overrides)
    return Config(**defaults)


def _mock_genai_response(
    finish_reason=None, text: str = "a bug summary", has_candidates: bool = True
):
    """Build a mock ``generate_content`` response object."""
    response = MagicMock()
    response.text = text
    if has_candidates:
        cand = MagicMock()
        cand.finish_reason = finish_reason
        response.candidates = [cand]
    else:
        response.candidates = []
    return response


def _patch_genai_client(response):
    """Return a patch context manager that makes ``genai.Client().models
    .generate_content(...)`` return ``response``. Yields the mock client."""
    mock_models = MagicMock()
    mock_models.generate_content.return_value = response
    mock_client = MagicMock()
    mock_client.models = mock_models
    return patch(
        "cfi_ai.maps.bugreport.genai.Client", return_value=mock_client
    ), mock_client, mock_models


# ── _normalize_finish_reason ─────────────────────────────────────────


def test_normalize_finish_reason_handles_none():
    assert _normalize_finish_reason(None) == ""


def test_normalize_finish_reason_handles_string():
    assert _normalize_finish_reason("STOP") == "STOP"
    assert _normalize_finish_reason("stop") == "STOP"
    assert _normalize_finish_reason("MAX_TOKENS") == "MAX_TOKENS"


def test_normalize_finish_reason_strips_enum_dotted_str():
    class _FakeEnumStr:
        def __str__(self):
            return "FinishReason.STOP"

        # no .name attribute — force the str() path

    assert _normalize_finish_reason(_FakeEnumStr()) == "STOP"


def test_normalize_finish_reason_uses_enum_name():
    fake_enum = MagicMock(spec=["name"])
    fake_enum.name = "MAX_TOKENS"
    assert _normalize_finish_reason(fake_enum) == "MAX_TOKENS"


# ── _call_summarizer ─────────────────────────────────────────────────


def test_call_summarizer_returns_text_on_stop():
    response = _mock_genai_response(finish_reason="STOP", text="bug summary text")
    patcher, _client, _models = _patch_genai_client(response)
    with patcher:
        out = _call_summarizer(_make_config(), "transcript")
    assert out == "bug summary text"


def test_call_summarizer_accepts_string_stop():
    response = _mock_genai_response(finish_reason="STOP", text="x")
    patcher, *_ = _patch_genai_client(response)
    with patcher:
        assert _call_summarizer(_make_config(), "t") == "x"


def test_call_summarizer_accepts_none_finish_reason():
    """Some SDK paths leave finish_reason unset on a successful response."""
    response = _mock_genai_response(finish_reason=None, text="x")
    patcher, *_ = _patch_genai_client(response)
    with patcher:
        assert _call_summarizer(_make_config(), "t") == "x"


def test_call_summarizer_accepts_enum_stop():
    """types.FinishReason.STOP (the real enum) normalizes to STOP and passes."""
    stop_enum = getattr(types, "FinishReason", None)
    if stop_enum is None or not hasattr(stop_enum, "STOP"):
        pytest.skip("types.FinishReason.STOP not available in this SDK version")
    response = _mock_genai_response(finish_reason=stop_enum.STOP, text="x")
    patcher, *_ = _patch_genai_client(response)
    with patcher:
        assert _call_summarizer(_make_config(), "t") == "x"


def test_call_summarizer_aborts_on_max_tokens():
    response = _mock_genai_response(finish_reason="MAX_TOKENS", text="partial")
    patcher, *_ = _patch_genai_client(response)
    with patcher, pytest.raises(RuntimeError) as excinfo:
        _call_summarizer(_make_config(), "t")
    assert "MAX_TOKENS" in str(excinfo.value)


def test_call_summarizer_handles_enum_max_tokens():
    """finish_reason returned as an enum-like object with .name == MAX_TOKENS."""
    fake_enum = MagicMock(spec=["name"])
    fake_enum.name = "MAX_TOKENS"
    response = _mock_genai_response(finish_reason=fake_enum, text="partial")
    patcher, *_ = _patch_genai_client(response)
    with patcher, pytest.raises(RuntimeError) as excinfo:
        _call_summarizer(_make_config(), "t")
    assert "MAX_TOKENS" in str(excinfo.value)


def test_call_summarizer_fails_closed_on_safety():
    response = _mock_genai_response(finish_reason="SAFETY", text="partial")
    patcher, *_ = _patch_genai_client(response)
    with patcher, pytest.raises(RuntimeError) as excinfo:
        _call_summarizer(_make_config(), "t")
    assert "non-success finish reason" in str(excinfo.value)
    assert "SAFETY" in str(excinfo.value)


def test_call_summarizer_handles_empty_candidates():
    response = _mock_genai_response(text="", has_candidates=False)
    patcher, *_ = _patch_genai_client(response)
    with patcher, pytest.raises(RuntimeError) as excinfo:
        _call_summarizer(_make_config(), "t")
    assert "empty" in str(excinfo.value).lower()


def test_call_summarizer_raises_on_empty_text_with_stop():
    response = _mock_genai_response(finish_reason="STOP", text="   ")
    patcher, *_ = _patch_genai_client(response)
    with patcher, pytest.raises(RuntimeError) as excinfo:
        _call_summarizer(_make_config(), "t")
    assert "empty" in str(excinfo.value).lower()


def test_call_summarizer_passes_http_options_timeout():
    response = _mock_genai_response(finish_reason="STOP", text="x")
    patcher, _client, mock_models = _patch_genai_client(response)
    with patcher:
        _call_summarizer(_make_config(), "t")
    call = mock_models.generate_content.call_args
    config_arg = call.kwargs["config"]
    assert config_arg.http_options is not None
    assert config_arg.http_options.timeout == _SUMMARY_TIMEOUT_MS


# ── _confirm_post ────────────────────────────────────────────────────


def _ui_mock_with_input(answer):
    ui = MagicMock()
    ui.console.input.return_value = answer
    return ui


def test_confirm_post_accepts_exact_POST():
    ui = _ui_mock_with_input("POST")
    assert _confirm_post(ui, "org/repo") is True


def test_confirm_post_rejects_lowercase():
    ui = _ui_mock_with_input("post")
    assert _confirm_post(ui, "org/repo") is False


@pytest.mark.parametrize("answer", ["", " ", "POSTT", "yes", "y"])
def test_confirm_post_rejects_empty_and_typo(answer):
    ui = _ui_mock_with_input(answer)
    assert _confirm_post(ui, "org/repo") is False


def test_confirm_post_handles_ctrl_c():
    ui = MagicMock()
    ui.console.input.side_effect = KeyboardInterrupt
    assert _confirm_post(ui, "org/repo") is False


def test_confirm_post_handles_eof():
    ui = MagicMock()
    ui.console.input.side_effect = EOFError
    assert _confirm_post(ui, "org/repo") is False


# ── _resolve_editor_command ──────────────────────────────────────────


def _which_map(available: dict[str, str]):
    """Return a fake ``shutil.which`` that resolves only the given names."""

    def _fake(name):
        return available.get(name)

    return _fake


def test_resolve_editor_defaults_to_vscode_when_available():
    with patch(
        "cfi_ai.maps.bugreport.shutil.which",
        side_effect=_which_map({"code": "/usr/local/bin/code"}),
    ):
        assert _resolve_editor_command() == ["code", "--wait"]


def test_resolve_editor_falls_back_to_nano():
    with patch(
        "cfi_ai.maps.bugreport.shutil.which",
        side_effect=_which_map({"nano": "/usr/bin/nano"}),
    ):
        assert _resolve_editor_command() == ["nano"]


def test_resolve_editor_falls_back_to_vi():
    with patch(
        "cfi_ai.maps.bugreport.shutil.which",
        side_effect=_which_map({"vi": "/usr/bin/vi"}),
    ):
        assert _resolve_editor_command() == ["vi"]


def test_resolve_editor_returns_none_when_nothing_available():
    with patch(
        "cfi_ai.maps.bugreport.shutil.which", side_effect=_which_map({})
    ):
        assert _resolve_editor_command() is None


# ── _edit_in_editor ──────────────────────────────────────────────────


def test_edit_in_editor_returns_none_on_unchanged_mtime():
    """Editor exits 0 but the temp file was never saved (e.g. vim :q!) → None."""
    with patch(
        "cfi_ai.maps.bugreport._resolve_editor_command", return_value=["vi"]
    ), patch("cfi_ai.maps.bugreport.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0
        )
        assert _edit_in_editor("seed") is None


def test_edit_in_editor_returns_edited_content_on_save():
    """Side-effect closure writes new content to the temp file, mtime advances."""

    def _run_side_effect(args, *rest, **kwargs):
        # args is the argv list: [*editor_cmd, tmp_path] — tmp_path is last.
        tmp_path = args[-1]
        import os as _os
        import time as _time

        _time.sleep(0.01)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write("edited content")
        now = _time.time()
        _os.utime(tmp_path, (now, now))
        return subprocess.CompletedProcess(args=args, returncode=0)

    with patch(
        "cfi_ai.maps.bugreport._resolve_editor_command", return_value=["vi"]
    ), patch(
        "cfi_ai.maps.bugreport.subprocess.run", side_effect=_run_side_effect
    ):
        result = _edit_in_editor("seed")
    assert result == "edited content"


def test_edit_in_editor_returns_none_on_nonzero_exit():
    with patch(
        "cfi_ai.maps.bugreport._resolve_editor_command", return_value=["vi"]
    ), patch("cfi_ai.maps.bugreport.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1
        )
        assert _edit_in_editor("seed") is None


def test_edit_in_editor_returns_none_when_editor_missing():
    with patch(
        "cfi_ai.maps.bugreport._resolve_editor_command", return_value=["vi"]
    ), patch(
        "cfi_ai.maps.bugreport.subprocess.run", side_effect=FileNotFoundError
    ):
        assert _edit_in_editor("seed") is None


def test_edit_in_editor_returns_none_when_no_editor_resolved():
    with patch(
        "cfi_ai.maps.bugreport._resolve_editor_command", return_value=None
    ), patch("cfi_ai.maps.bugreport.subprocess.run") as mock_run:
        assert _edit_in_editor("seed") is None
        mock_run.assert_not_called()


# ── _build_issue_body ────────────────────────────────────────────────


def test_build_issue_body_has_three_sections():
    body = _build_issue_body(
        user_description="the save button hung",
        bug_summary="## What went wrong\nThe tool crashed.",
        session_id="sess-1",
        usage=None,
    )
    assert "## Description" in body
    assert "## Bug summary" in body
    assert "## Environment" in body
    # No legacy sections:
    assert "## Redaction summary" not in body
    assert "## Scrubbed conversation" not in body
    # Description surfaces the user input; bug summary passes through.
    assert "the save button hung" in body
    assert "## What went wrong" in body


def test_build_issue_body_uses_placeholder_when_no_description():
    body = _build_issue_body(
        user_description="",
        bug_summary="summary",
        session_id="sess-1",
        usage=None,
    )
    assert "(no description provided)" in body


# ── handler: gating ──────────────────────────────────────────────────


def test_handle_bugreport_bugreport_disabled(populated_store, workspace):
    config = _make_config(bugreport_enabled=False)
    with patch("cfi_ai.maps.bugreport.Config.load", return_value=config):
        result = handle_bugreport(
            args=None, ui=MagicMock(), workspace=workspace, session_store=populated_store
        )
    assert result.error is not None
    assert "disabled" in result.error.lower()


def test_handle_bugreport_missing_session_file(sessions_dir, workspace):
    """Session store with no on-disk file yet → refuses to run."""
    store = SessionStore(workspace)  # no .save() → no file
    with patch("cfi_ai.maps.bugreport.Config.load", return_value=_make_config()):
        result = handle_bugreport(
            args=None, ui=MagicMock(), workspace=workspace, session_store=store
        )
    assert result.error is not None
    assert "no saved conversation" in result.error.lower()


# ── handler: action paths ────────────────────────────────────────────


def test_handle_bugreport_missing_token_on_post(populated_store, workspace):
    """User presses p, confirms POST, but no token is available → error."""
    ui = MagicMock()
    with patch("cfi_ai.maps.bugreport.Config.load", return_value=_make_config()), patch(
        "cfi_ai.maps.bugreport._call_summarizer", return_value="summary"
    ), patch(
        "cfi_ai.maps.bugreport._prompt_action", return_value="p"
    ), patch(
        "cfi_ai.maps.bugreport._confirm_post", return_value=True
    ), patch(
        "cfi_ai.maps.bugreport.discover_token", return_value=None
    ), patch(
        "cfi_ai.maps.bugreport.create_issue"
    ) as mock_create:
        result = handle_bugreport(
            args=None, ui=ui, workspace=workspace, session_store=populated_store
        )
    assert result.handled is True
    mock_create.assert_not_called()
    # The token error surfaces via ui.print_error.
    assert any(
        "github token" in str(call.args[0]).lower()
        for call in ui.print_error.call_args_list
    )


def test_handle_bugreport_dry_run_works_without_token(
    populated_store, workspace, tmp_path
):
    """Dry-run must not call discover_token or create_issue, and must write a
    bugreport-dryrun-*.md file under workspace.root."""
    ui = MagicMock()
    mock_discover = MagicMock(return_value=None)
    config = _make_config(bugreport_dry_run=True)
    with patch("cfi_ai.maps.bugreport.Config.load", return_value=config), patch(
        "cfi_ai.maps.bugreport._call_summarizer", return_value="summary"
    ), patch(
        "cfi_ai.maps.bugreport._prompt_action", return_value="p"
    ), patch(
        "cfi_ai.maps.bugreport._confirm_post", return_value=True
    ), patch(
        "cfi_ai.maps.bugreport.discover_token", mock_discover
    ), patch(
        "cfi_ai.maps.bugreport.create_issue"
    ) as mock_create:
        result = handle_bugreport(
            args=None, ui=ui, workspace=workspace, session_store=populated_store
        )
    assert result.handled is True
    mock_create.assert_not_called()
    mock_discover.assert_not_called()
    dryrun_files = list(Path(workspace.root).glob("bugreport-dryrun-*.md"))
    assert len(dryrun_files) == 1


def test_handle_bugreport_save_action_works_without_token(
    populated_store, workspace
):
    """Pressing 's' writes a bugreport-*.md and never triggers auth discovery."""
    ui = MagicMock()
    mock_discover = MagicMock(return_value=None)
    with patch("cfi_ai.maps.bugreport.Config.load", return_value=_make_config()), patch(
        "cfi_ai.maps.bugreport._call_summarizer", return_value="summary"
    ), patch(
        "cfi_ai.maps.bugreport._prompt_action", return_value="s"
    ), patch(
        "cfi_ai.maps.bugreport.discover_token", mock_discover
    ), patch(
        "cfi_ai.maps.bugreport.create_issue"
    ) as mock_create:
        result = handle_bugreport(
            args=None, ui=ui, workspace=workspace, session_store=populated_store
        )
    assert result.handled is True
    mock_create.assert_not_called()
    mock_discover.assert_not_called()
    saved = list(Path(workspace.root).glob("bugreport-*.md"))
    # Exclude any dryrun file that shouldn't be there, but the glob catches both.
    saved = [p for p in saved if "dryrun" not in p.name]
    assert len(saved) == 1


def test_handle_bugreport_post_cancelled_loops_back_to_action_menu(
    populated_store, workspace
):
    """First _confirm_post → False cancels; loop re-enters and asks again.
    Second _confirm_post → True proceeds to POST (verified via create_issue)."""
    ui = MagicMock()
    confirm_returns = iter([False, True])
    action_returns = iter(["p", "p"])
    mock_prompt_action = MagicMock(side_effect=lambda ui_arg: next(action_returns))
    mock_confirm_post = MagicMock(side_effect=lambda *_args: next(confirm_returns))
    with patch("cfi_ai.maps.bugreport.Config.load", return_value=_make_config()), patch(
        "cfi_ai.maps.bugreport._call_summarizer", return_value="summary"
    ), patch(
        "cfi_ai.maps.bugreport._prompt_action", mock_prompt_action
    ), patch(
        "cfi_ai.maps.bugreport._confirm_post", mock_confirm_post
    ), patch(
        "cfi_ai.maps.bugreport.discover_token", return_value="tok"
    ), patch(
        "cfi_ai.maps.bugreport.create_issue",
        return_value="https://github.com/o/r/issues/1",
    ) as mock_create:
        result = handle_bugreport(
            args=None, ui=ui, workspace=workspace, session_store=populated_store
        )
    assert result.handled is True
    # create_issue only on the second (confirmed) attempt.
    mock_create.assert_called_once()
    assert mock_prompt_action.call_count == 2
    assert mock_confirm_post.call_count == 2


def test_handle_bugreport_token_passthrough_calls_discover_once(
    populated_store, workspace
):
    """discover_token runs exactly once and its result is passed to create_issue
    via the token= kwarg, so create_issue doesn't re-discover."""
    ui = MagicMock()
    mock_discover = MagicMock(return_value="tok")
    mock_create = MagicMock(return_value="https://github.com/o/r/issues/2")
    with patch("cfi_ai.maps.bugreport.Config.load", return_value=_make_config()), patch(
        "cfi_ai.maps.bugreport._call_summarizer", return_value="summary"
    ), patch(
        "cfi_ai.maps.bugreport._prompt_action", return_value="p"
    ), patch(
        "cfi_ai.maps.bugreport._confirm_post", return_value=True
    ), patch(
        "cfi_ai.maps.bugreport.discover_token", mock_discover
    ), patch(
        "cfi_ai.maps.bugreport.create_issue", mock_create
    ):
        result = handle_bugreport(
            args=None, ui=ui, workspace=workspace, session_store=populated_store
        )
    assert result.handled is True
    assert mock_discover.call_count == 1
    assert mock_create.call_args.kwargs["token"] == "tok"
    assert mock_create.call_args.kwargs["labels"] == ["bug", "auto-reported"]


def test_handle_bugreport_quit_returns_handled(populated_store, workspace):
    ui = MagicMock()
    with patch("cfi_ai.maps.bugreport.Config.load", return_value=_make_config()), patch(
        "cfi_ai.maps.bugreport._call_summarizer", return_value="summary"
    ), patch("cfi_ai.maps.bugreport._prompt_action", return_value="q"):
        result = handle_bugreport(
            args=None, ui=ui, workspace=workspace, session_store=populated_store
        )
    assert result.handled is True
