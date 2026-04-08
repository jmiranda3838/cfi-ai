import datetime
from unittest.mock import MagicMock

from cfi_ai.maps.intake import handle_intake
from cfi_ai.workspace import Workspace


# --- handle_intake fast path tests ---

def test_handle_intake_file_reference(tmp_path):
    """File args produce a message with file processing instructions."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.mp3", ui, ws, MagicMock())
    assert result.message is not None
    assert "session.mp3" in result.message
    assert "attach_path" in result.message
    assert result.parts is None
    assert result.error is None


def test_handle_intake_message_contains_date(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("notes.txt", ui, ws, MagicMock())
    assert datetime.date.today().isoformat() in result.message


def test_handle_intake_message_has_client_discovery(tmp_path):
    """Prompt tells LLM to discover existing clients via tools."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.txt", ui, ws, MagicMock())
    assert "run_command ls clients/" in result.message


def test_handle_intake_map_mode(tmp_path):
    """File intake sets map_mode=True."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.mp3", ui, ws, MagicMock())
    assert result.map_mode is True


def test_handle_intake_file_sets_plan_prompt(tmp_path):
    """File intake sets plan_prompt with file reference and 'Do NOT load'."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("recording.m4a", ui, ws, MagicMock())
    assert result.plan_prompt is not None
    assert "recording.m4a" in result.plan_prompt
    assert "Do NOT load" in result.plan_prompt


# --- handle_intake skill path tests ---

def test_handle_intake_no_args_direct_prompt(tmp_path):
    """No args -> full intake prompt with interview instruction, map_mode=True."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake(None, ui, ws, MagicMock())
    assert result.message is not None
    assert result.error is None
    assert result.map_mode is True
    assert result.plan_prompt is not None
    assert "interview" in result.message
    assert "Diagnostic Impressions" in result.message


def test_handle_intake_empty_args_direct_prompt(tmp_path):
    """Empty/whitespace args -> full intake prompt with interview instruction."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("   ", ui, ws, MagicMock())
    assert result.error is None
    assert result.map_mode is True
    assert "interview" in result.message


def test_handle_intake_no_current_md_in_prompt(tmp_path):
    """Prompt should not contain current.md references."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.mp3", ui, ws, MagicMock())
    assert "current.md" not in result.message
