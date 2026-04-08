"""Tests for the /clear slash map handler and SessionStore.reset()."""

from unittest.mock import MagicMock

from cfi_ai.maps.clear import handle_clear
from cfi_ai.sessions import SessionStore
from cfi_ai.workspace import Workspace


def test_clear_returns_clear_conversation_flag(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    store = MagicMock()

    result = handle_clear(None, ui, ws, store)

    assert result.handled is True
    assert result.clear_conversation is True
    assert result.error is None
    assert result.loaded_messages is None
    ui.print_info.assert_called_once()


def test_clear_is_registered_in_maps_registry():
    """Importing maps must register /clear so the dispatcher can find it."""
    from cfi_ai.maps import MAPS, get_map_descriptions

    assert "clear" in MAPS
    assert "clear" in get_map_descriptions()


def test_session_store_reset_creates_new_session_file(tmp_path):
    """SessionStore.reset() must re-point the store at a fresh session file
    so post-/clear turns don't overwrite the prior session's JSON."""
    ws = Workspace(str(tmp_path))
    store = SessionStore(ws)
    original_id = store.session_id
    original_path = store._path

    store.reset(ws)

    assert store.session_id != original_id
    assert store._path != original_path
    assert store.usage is None
