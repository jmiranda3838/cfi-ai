"""Tests for the /resume slash map handler."""

from pathlib import Path
from unittest.mock import MagicMock

from cfi_ai.maps.resume import handle_resume
from cfi_ai.sessions import SessionMeta, SessionStore
from cfi_ai.workspace import Workspace


def _meta(path: Path, session_id: str = "s1") -> SessionMeta:
    return SessionMeta(
        id=session_id,
        path=path,
        updated_at=1000.0,
        first_user_message="hi",
        message_count=2,
    )


def test_resume_no_sessions_prints_info(tmp_path, monkeypatch):
    monkeypatch.setattr(SessionStore, "list_for_workspace", staticmethod(lambda ws: []))
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    store = MagicMock()

    result = handle_resume(None, ui, ws, store)

    assert result.handled is True
    assert result.loaded_messages is None
    assert result.error is None
    ui.print_info.assert_called_once()
    # store should not be mutated when there's nothing to resume
    store.adopt.assert_not_called()


def test_resume_menu_cancelled(tmp_path, monkeypatch):
    fake_session = _meta(tmp_path / "fake.json")
    monkeypatch.setattr(SessionStore, "list_for_workspace", staticmethod(lambda ws: [fake_session]))
    ui = MagicMock()
    ui.prompt_session_select.return_value = None  # user hit Escape
    ws = Workspace(str(tmp_path))
    store = MagicMock()

    result = handle_resume(None, ui, ws, store)

    assert result.handled is True
    assert result.loaded_messages is None
    assert result.error is None
    ui.prompt_session_select.assert_called_once_with([fake_session])
    store.adopt.assert_not_called()


def test_resume_successful_load_returns_messages_and_adopts(tmp_path, monkeypatch):
    fake_session = _meta(tmp_path / "session.json", session_id="abc123")
    fake_messages = [MagicMock(), MagicMock(), MagicMock()]
    monkeypatch.setattr(SessionStore, "list_for_workspace", staticmethod(lambda ws: [fake_session]))
    monkeypatch.setattr(SessionStore, "load", staticmethod(lambda path: fake_messages))
    ui = MagicMock()
    ui.prompt_session_select.return_value = fake_session
    ws = Workspace(str(tmp_path))
    store = MagicMock()

    result = handle_resume(None, ui, ws, store)

    assert result.handled is True
    assert result.error is None
    assert result.loaded_messages == fake_messages
    store.adopt.assert_called_once_with("abc123", fake_session.path)
    ui.print_info.assert_called_once()


def test_resume_load_failure_returns_error(tmp_path, monkeypatch):
    fake_session = _meta(tmp_path / "bad.json")

    def _boom(path):
        raise ValueError("bad json")

    monkeypatch.setattr(SessionStore, "list_for_workspace", staticmethod(lambda ws: [fake_session]))
    monkeypatch.setattr(SessionStore, "load", staticmethod(_boom))
    ui = MagicMock()
    ui.prompt_session_select.return_value = fake_session
    ws = Workspace(str(tmp_path))
    store = MagicMock()

    result = handle_resume(None, ui, ws, store)

    assert result.error is not None
    assert "bad json" in result.error
    assert result.loaded_messages is None
    store.adopt.assert_not_called()
