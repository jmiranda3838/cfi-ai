"""Tests for the on-disk chat session store."""

import json
import time
from pathlib import Path

import pytest
from google.genai import types

from cfi_ai import sessions as sessions_mod
from cfi_ai.sessions import SessionStore
from cfi_ai.workspace import Workspace


@pytest.fixture
def sessions_dir(tmp_path, monkeypatch):
    """Redirect SESSIONS_DIR at the module level so tests never touch real config."""
    fake = tmp_path / "sessions"
    monkeypatch.setattr(sessions_mod, "SESSIONS_DIR", fake)
    return fake


@pytest.fixture
def workspace(tmp_path):
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    return Workspace(str(ws_root))


def _text_content(role: str, text: str) -> types.Content:
    return types.Content(role=role, parts=[types.Part.from_text(text=text)])


def _fc_response(name: str, result: str) -> types.Content:
    return types.Content(
        role="user",
        parts=[types.Part.from_function_response(name=name, response={"result": result})],
    )


# --- save / load round-trip ---

def test_save_load_roundtrip_text_only(sessions_dir, workspace):
    store = SessionStore(workspace)
    original = [
        _text_content("user", "hello"),
        _text_content("model", "hi there"),
    ]
    store.save(original)

    loaded = SessionStore.load(store._path)
    assert len(loaded) == 2
    assert loaded[0].role == "user"
    assert loaded[0].parts[0].text == "hello"
    assert loaded[1].role == "model"
    assert loaded[1].parts[0].text == "hi there"


def test_save_load_roundtrip_function_call(sessions_dir, workspace):
    """A model turn containing a function_call Part must survive round-trip."""
    store = SessionStore(workspace)
    # Build via model_validate so we don't depend on a specific builder API
    fc_dict = {
        "role": "model",
        "parts": [{"function_call": {"name": "run_command", "args": {"command": "ls"}}}],
    }
    original = [
        _text_content("user", "list files"),
        types.Content.model_validate(fc_dict),
    ]
    store.save(original)

    loaded = SessionStore.load(store._path)
    assert len(loaded) == 2
    assert loaded[1].role == "model"
    fc = loaded[1].parts[0].function_call
    assert fc is not None
    assert fc.name == "run_command"


def test_save_load_roundtrip_function_response(sessions_dir, workspace):
    store = SessionStore(workspace)
    original = [
        _text_content("user", "go"),
        _fc_response("run_command", "file1.txt\nfile2.txt\n"),
    ]
    store.save(original)

    loaded = SessionStore.load(store._path)
    assert len(loaded) == 2
    resp_part = loaded[1].parts[0]
    assert resp_part.function_response is not None
    assert resp_part.function_response.name == "run_command"


def test_save_empty_messages_is_noop(sessions_dir, workspace):
    store = SessionStore(workspace)
    store.save([])
    assert not store._path.exists()


def test_save_captures_first_user_message_preview(sessions_dir, workspace):
    store = SessionStore(workspace)
    store.save([_text_content("user", "  first prompt  "), _text_content("model", "ok")])
    data = json.loads(store._path.read_text())
    assert data["first_user_message"] == "first prompt"


# --- list_for_workspace ---

def test_list_for_workspace_filters_by_workspace(sessions_dir, tmp_path):
    ws_a = Workspace(str(tmp_path / "a"))
    (tmp_path / "a").mkdir()
    ws_b = Workspace(str(tmp_path / "b"))
    (tmp_path / "b").mkdir()

    store_a = SessionStore(ws_a)
    store_a.save([_text_content("user", "in a")])
    store_b = SessionStore(ws_b)
    store_b.save([_text_content("user", "in b")])

    results_a = SessionStore.list_for_workspace(ws_a)
    results_b = SessionStore.list_for_workspace(ws_b)

    assert len(results_a) == 1
    assert len(results_b) == 1
    assert results_a[0].first_user_message == "in a"
    assert results_b[0].first_user_message == "in b"


def test_list_for_workspace_sorted_newest_first(sessions_dir, workspace):
    # Save two sessions with distinct updated_at timestamps.
    s1 = SessionStore(workspace)
    s1.save([_text_content("user", "older")])
    time.sleep(0.01)
    s2 = SessionStore(workspace)
    s2.save([_text_content("user", "newer")])

    results = SessionStore.list_for_workspace(workspace)
    assert len(results) == 2
    assert results[0].first_user_message == "newer"
    assert results[1].first_user_message == "older"


def test_list_for_workspace_handles_corrupt_file(sessions_dir, workspace):
    store = SessionStore(workspace)
    store.save([_text_content("user", "valid")])
    # Drop a garbage file into the sessions dir
    (sessions_dir / "corrupt.json").write_text("{not valid json")
    # Empty but present file
    (sessions_dir / "empty.json").write_text("")

    results = SessionStore.list_for_workspace(workspace)
    assert len(results) == 1
    assert results[0].first_user_message == "valid"


def test_list_for_workspace_returns_empty_when_dir_missing(sessions_dir, workspace):
    # Never wrote anything, so the dir is missing.
    assert not sessions_dir.exists()
    assert SessionStore.list_for_workspace(workspace) == []


# --- prune_expired ---

def _write_session_with_timestamp(sessions_dir: Path, session_id: str, updated_at: float, workspace_root: str) -> Path:
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f"{session_id}.json"
    path.write_text(json.dumps({
        "id": session_id,
        "workspace": workspace_root,
        "created_at": updated_at,
        "updated_at": updated_at,
        "first_user_message": "",
        "messages": [],
    }))
    return path


def test_prune_expired_deletes_old(sessions_dir, tmp_path):
    old_path = _write_session_with_timestamp(
        sessions_dir, "old", time.time() - 31 * 86400, str(tmp_path)
    )
    assert old_path.exists()

    count = SessionStore.prune_expired()
    assert count == 1
    assert not old_path.exists()


def test_prune_expired_keeps_fresh(sessions_dir, tmp_path):
    fresh_path = _write_session_with_timestamp(
        sessions_dir, "fresh", time.time() - 60, str(tmp_path)
    )
    count = SessionStore.prune_expired()
    assert count == 0
    assert fresh_path.exists()


def test_prune_expired_boundary(sessions_dir, tmp_path):
    """Files right at the 30-day edge get the treatment (< cutoff → pruned)."""
    old_path = _write_session_with_timestamp(
        sessions_dir, "edge", time.time() - 30 * 86400 - 1, str(tmp_path)
    )
    fresh_path = _write_session_with_timestamp(
        sessions_dir, "just_in", time.time() - 30 * 86400 + 60, str(tmp_path)
    )
    count = SessionStore.prune_expired()
    assert count == 1
    assert not old_path.exists()
    assert fresh_path.exists()


def test_prune_expired_handles_corrupt_file(sessions_dir, tmp_path):
    fresh_path = _write_session_with_timestamp(
        sessions_dir, "fresh", time.time() - 60, str(tmp_path)
    )
    corrupt = sessions_dir / "corrupt.json"
    corrupt.write_text("{not valid json")

    # Must not raise, must not delete the corrupt file, must not touch fresh.
    count = SessionStore.prune_expired()
    assert count == 0
    assert fresh_path.exists()
    assert corrupt.exists()


def test_prune_expired_no_directory(sessions_dir):
    assert not sessions_dir.exists()
    # Must not raise.
    assert SessionStore.prune_expired() == 0


def test_prune_expired_custom_age(sessions_dir, tmp_path):
    path = _write_session_with_timestamp(
        sessions_dir, "one_hour_old", time.time() - 3600, str(tmp_path)
    )
    # 0-day cutoff means every file is expired.
    assert SessionStore.prune_expired(max_age_days=0) == 1
    assert not path.exists()


def test_list_for_workspace_calls_prune(sessions_dir, workspace):
    """list_for_workspace must prune before returning, so expired sessions disappear."""
    # Write one expired session for this workspace
    old = _write_session_with_timestamp(
        sessions_dir,
        "expired",
        time.time() - 31 * 86400,
        str(workspace.root),
    )
    # And one fresh one via the real path.
    store = SessionStore(workspace)
    store.save([_text_content("user", "fresh")])

    results = SessionStore.list_for_workspace(workspace)
    assert len(results) == 1
    assert results[0].first_user_message == "fresh"
    assert not old.exists()


# --- adopt ---

def test_adopt_repoints_store(sessions_dir, workspace):
    # First session
    s1 = SessionStore(workspace)
    s1.save([_text_content("user", "first")])
    first_path = s1._path
    first_id = s1.session_id

    # Fresh store, then adopt the first file
    s2 = SessionStore(workspace)
    new_path = s2._path  # would-be path if we didn't adopt
    s2.adopt(first_id, first_path)

    assert s2.session_id == first_id
    assert s2._path == first_path

    # Saving again should overwrite the adopted file, not create a new one
    s2.save([_text_content("user", "first"), _text_content("model", "continuation")])
    assert first_path.exists()
    # Reload to confirm persistence of the new state
    loaded = SessionStore.load(first_path)
    assert len(loaded) == 2
    assert loaded[1].parts[0].text == "continuation"
    # And the "fresh" path s2 was originally going to write to must not exist
    assert not new_path.exists()


def test_adopt_handles_corrupt_file(sessions_dir, workspace):
    """adopt() must tolerate a corrupt file without raising."""
    bad_path = sessions_dir / "bad.json"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("{not valid")

    store = SessionStore(workspace)
    # Must not raise
    store.adopt("bad", bad_path)
    assert store.session_id == "bad"
    assert store._path == bad_path


def test_session_store_path_property(sessions_dir, workspace):
    """The public ``path`` property exposes the same Path as the private
    ``_path`` backing attribute, and matches the session-id-based filename
    under ``SESSIONS_DIR``."""
    store = SessionStore(workspace)
    assert store.path == store._path
    assert store.path == sessions_dir / f"{store.session_id}.json"
