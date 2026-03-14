import os

from cfi_ai.clients import list_clients, load_client_context, sanitize_client_id
from cfi_ai.workspace import Workspace


def test_list_clients_no_dir(tmp_path):
    ws = Workspace(str(tmp_path))
    assert list_clients(ws) == []


def test_list_clients_with_dirs(tmp_path):
    clients = tmp_path / "clients"
    (clients / "alice-smith").mkdir(parents=True)
    (clients / "bob-jones").mkdir(parents=True)
    (clients / ".hidden").mkdir()
    ws = Workspace(str(tmp_path))
    assert list_clients(ws) == ["alice-smith", "bob-jones"]


def test_list_clients_empty_dir(tmp_path):
    (tmp_path / "clients").mkdir()
    ws = Workspace(str(tmp_path))
    assert list_clients(ws) == []


def test_load_client_context_missing(tmp_path):
    (tmp_path / "clients" / "jane-doe").mkdir(parents=True)
    ws = Workspace(str(tmp_path))
    assert load_client_context(ws, "jane-doe") == ""


def test_load_client_context_with_profile(tmp_path):
    client_dir = tmp_path / "clients" / "jane-doe"
    profile_dir = client_dir / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "current.md").write_text("# Jane Doe\nAge: 35")
    ws = Workspace(str(tmp_path))
    ctx = load_client_context(ws, "jane-doe")
    assert "Jane Doe" in ctx
    assert "### Profile" in ctx


def test_load_client_context_with_both(tmp_path):
    client_dir = tmp_path / "clients" / "jane-doe"
    (client_dir / "profile").mkdir(parents=True)
    (client_dir / "profile" / "current.md").write_text("Profile content")
    (client_dir / "treatment-plan").mkdir(parents=True)
    (client_dir / "treatment-plan" / "current.md").write_text("Treatment plan content")
    ws = Workspace(str(tmp_path))
    ctx = load_client_context(ws, "jane-doe")
    assert "### Profile" in ctx
    assert "### Treatment Plan" in ctx
    assert "Profile content" in ctx
    assert "Treatment plan content" in ctx


def test_sanitize_client_id_basic():
    assert sanitize_client_id("Jane Doe") == "jane-doe"


def test_sanitize_client_id_special_chars():
    assert sanitize_client_id("O'Brien, Mary-Jane") == "o-brien-mary-jane"


def test_sanitize_client_id_extra_spaces():
    assert sanitize_client_id("  John   Smith  ") == "john-smith"


def test_sanitize_client_id_already_slug():
    assert sanitize_client_id("jane-doe") == "jane-doe"
