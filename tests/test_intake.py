import datetime
from unittest.mock import MagicMock

from cfi_ai.commands.intake import handle_intake, _build_existing_clients_section
from cfi_ai.workspace import Workspace


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
    # Should only list slugs, not load full profile content
    assert "Jane Doe profile" not in section


# --- handle_intake fast path tests ---

def test_handle_intake_file_reference(tmp_path):
    """File args produce a message with INTAKE_FILE_WORKFLOW_PROMPT."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.mp3", ui, ws)
    assert result.message is not None
    assert "session.mp3" in result.message
    assert "attach_path" in result.message
    assert result.parts is None
    assert result.error is None


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


def test_handle_intake_workflow_mode(tmp_path):
    """File intake sets workflow_mode=True."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.mp3", ui, ws)
    assert result.workflow_mode is True


def test_handle_intake_file_sets_plan_prompt(tmp_path):
    """File intake sets plan_prompt with file reference and 'Do NOT load'."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("recording.m4a", ui, ws)
    assert result.plan_prompt is not None
    assert "recording.m4a" in result.plan_prompt
    assert "Do NOT load" in result.plan_prompt


# --- handle_intake skill path tests ---

def test_handle_intake_no_args_skill_path(tmp_path):
    """No args → skill path message for the LLM, no error."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake(None, ui, ws)
    assert result.message is not None
    assert result.error is None
    assert "[SKILL: intake]" in result.message
    assert "activate_workflow" in result.message


def test_handle_intake_no_args_lists_clients(tmp_path):
    """Skill path includes available clients."""
    (tmp_path / "clients" / "bob-jones").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake(None, ui, ws)
    assert "bob-jones" in result.message


def test_handle_intake_empty_args_skill_path(tmp_path):
    """Empty/whitespace args → skill path."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("   ", ui, ws)
    assert result.error is None
    assert "[SKILL: intake]" in result.message
