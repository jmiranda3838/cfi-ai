import datetime
from unittest.mock import MagicMock

from cfi_ai.commands.intake import (
    _FileReference,
    _TextInput,
    _resolve_input,
    handle_intake,
    _build_existing_clients_section,
)
from cfi_ai.workspace import Workspace


# --- _resolve_input tests ---

def test_resolve_input_file_reference_from_args(tmp_path):
    """Args are returned as _FileReference for LLM to resolve."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = _resolve_input("session.mp3", ui, ws)
    assert isinstance(result, _FileReference)
    assert result.raw == "session.mp3"


def test_resolve_input_file_reference_absolute(tmp_path):
    """Absolute path args are returned as _FileReference."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = _resolve_input("/Users/me/Downloads/recording.m4a", ui, ws)
    assert isinstance(result, _FileReference)
    assert result.raw == "/Users/me/Downloads/recording.m4a"


def test_resolve_input_file_reference_escaped(tmp_path):
    """Escaped paths are passed through as-is for LLM to interpret."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = _resolve_input("/Users/me/Downloads/Bristol\\ St\\ 4.m4a", ui, ws)
    assert isinstance(result, _FileReference)
    assert "Bristol\\ St\\ 4.m4a" in result.raw


def test_resolve_input_interactive_paste(tmp_path):
    ui = MagicMock()
    ui.prompt_multiline.return_value = "This is pasted transcript text.\nWith multiple lines."
    ws = Workspace(str(tmp_path))
    result = _resolve_input(None, ui, ws)
    assert isinstance(result, _TextInput)
    assert result.text == "This is pasted transcript text.\nWith multiple lines."


def test_resolve_input_interactive_single_line(tmp_path):
    """Single-line interactive input is treated as a file reference."""
    ui = MagicMock()
    ui.prompt_multiline.return_value = "recording.m4a"
    ws = Workspace(str(tmp_path))
    result = _resolve_input(None, ui, ws)
    assert isinstance(result, _FileReference)
    assert result.raw == "recording.m4a"


def test_resolve_input_cancelled(tmp_path):
    ui = MagicMock()
    ui.prompt_multiline.return_value = None
    ws = Workspace(str(tmp_path))
    result = _resolve_input(None, ui, ws)
    assert result is None
    ui.print_info.assert_called()


def test_resolve_input_empty_input(tmp_path):
    ui = MagicMock()
    ui.prompt_multiline.return_value = "   "
    ws = Workspace(str(tmp_path))
    result = _resolve_input(None, ui, ws)
    assert result is None


# --- _build_existing_clients_section tests ---

def test_existing_clients_none(tmp_path):
    ws = Workspace(str(tmp_path))
    section = _build_existing_clients_section(ws)
    assert "No existing clients" in section


def test_existing_clients_with_data(tmp_path):
    client_dir = tmp_path / "clients" / "jane-doe"
    (client_dir / "profile").mkdir(parents=True)
    (client_dir / "profile" / "current.md").write_text("# Jane Doe profile")
    ws = Workspace(str(tmp_path))
    section = _build_existing_clients_section(ws)
    assert "jane-doe" in section
    assert "Jane Doe profile" in section


# --- handle_intake integration tests ---

def test_handle_intake_file_reference(tmp_path):
    """File args produce a message with INTAKE_FILE_WORKFLOW_PROMPT."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.mp3", ui, ws)
    assert result.message is not None
    assert "session.mp3" in result.message
    assert "read_audio" in result.message
    assert result.parts is None


def test_handle_intake_text_paste(tmp_path):
    """Pasted multi-line text uses INTAKE_WORKFLOW_PROMPT with transcript embedded."""
    ui = MagicMock()
    ui.prompt_multiline.return_value = "Client discussed anxiety.\nTherapist responded."
    ws = Workspace(str(tmp_path))
    result = handle_intake(None, ui, ws)
    assert result.message is not None
    assert "Client discussed anxiety." in result.message
    assert "<transcript>" in result.message


def test_handle_intake_cancelled(tmp_path):
    ui = MagicMock()
    ui.prompt_multiline.return_value = None
    ws = Workspace(str(tmp_path))
    result = handle_intake(None, ui, ws)
    assert result.handled is True
    assert result.message is None
    assert result.parts is None


def test_handle_intake_message_contains_date(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("notes.txt", ui, ws)
    assert datetime.date.today().isoformat() in result.message


def test_handle_intake_message_contains_existing_clients(tmp_path):
    (tmp_path / "clients" / "existing-client" / "profile").mkdir(parents=True)
    (tmp_path / "clients" / "existing-client" / "profile" / "current.md").write_text("Profile data")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.txt", ui, ws)
    assert "existing-client" in result.message
