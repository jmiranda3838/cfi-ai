from cfi_ai.clients import list_clients, sanitize_client_id
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


def test_sanitize_client_id_basic():
    assert sanitize_client_id("Jane Doe") == "jane-doe"


def test_sanitize_client_id_special_chars():
    assert sanitize_client_id("O'Brien, Mary-Jane") == "o-brien-mary-jane"


def test_sanitize_client_id_extra_spaces():
    assert sanitize_client_id("  John   Smith  ") == "john-smith"


def test_sanitize_client_id_already_slug():
    assert sanitize_client_id("jane-doe") == "jane-doe"
