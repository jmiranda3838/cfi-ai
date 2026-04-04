from unittest.mock import MagicMock

from cfi_ai.maps import MapResult, build_map_message, dispatch_map, parse_map_invocation
from cfi_ai.prompts.intake import INTAKE_PROMPT
from cfi_ai.tools.activate_map import ActivateMapTool
from cfi_ai.workspace import Workspace


# --- parse_map_invocation tests ---

def test_parse_map_invocation_not_a_map():
    assert parse_map_invocation("hello world") is None


def test_parse_map_invocation_empty():
    assert parse_map_invocation("") is None


def test_parse_map_invocation_slash_only():
    assert parse_map_invocation("/") is None


def test_parse_map_invocation_simple():
    assert parse_map_invocation("/help") == ("help", None)


def test_parse_map_invocation_with_args():
    assert parse_map_invocation("/intake transcript.txt") == ("intake", "transcript.txt")


def test_parse_map_invocation_with_spaces():
    assert parse_map_invocation("  /help  ") == ("help", None)


def test_parse_map_invocation_multi_word_args():
    assert parse_map_invocation("/intake some file path.txt") == ("intake", "some file path.txt")


# --- dispatch_map tests ---

def test_dispatch_unknown_map():
    ui = MagicMock()
    ws = Workspace("/tmp")
    result = dispatch_map("nonexistent", None, ui, ws)
    assert result.error is not None
    assert "Unknown map" in result.error


def test_dispatch_help():
    ui = MagicMock()
    ws = Workspace("/tmp")
    result = dispatch_map("help", None, ui, ws)
    assert result.handled is True
    assert result.message is None
    assert result.error is None
    ui.render_markdown.assert_called_once()


def test_dispatch_help_lists_maps():
    ui = MagicMock()
    ws = Workspace("/tmp")
    dispatch_map("help", None, ui, ws)
    rendered = ui.render_markdown.call_args[0][0]
    assert "/help" in rendered
    assert "/intake" in rendered


def test_dispatch_help_shows_missing_record_contracts():
    ui = MagicMock()
    ws = Workspace("/tmp")
    dispatch_map("help", None, ui, ws)
    rendered = ui.render_markdown.call_args[0][0]
    assert "missing records may be surfaced as findings" in rendered
    assert "requires an existing treatment plan and progress notes to generate updates" in rendered


# --- MapResult tests ---

def test_map_result_parts_default():
    result = MapResult()
    assert result.parts is None
    assert result.message is None
    assert result.handled is False
    assert result.error is None
    assert result.map_mode is False
    assert result.plan_prompt is None


# --- File map prompt tests ---

def test_intake_prompt_has_placeholders():
    """INTAKE_PROMPT formats without error."""
    formatted = INTAKE_PROMPT.format(
        date="2026-03-13",
        intake_input="The user wants to process: `session.mp3`",
    )
    assert "2026-03-13" in formatted
    assert "session.mp3" in formatted
    assert "{intake_input}" not in formatted
    assert "{date}" not in formatted


# --- build_map_message tests ---

def test_build_map_message_basic(tmp_path):
    ws = Workspace(str(tmp_path))
    msg = build_map_message("compliance", "run a compliance check", None, ws)
    assert "[MAP: compliance]" in msg
    assert "run a compliance check" in msg
    assert "activate_map" in msg
    assert 'source="slash"' in msg
    assert "interview" in msg


def test_build_map_message_with_user_input(tmp_path):
    ws = Workspace(str(tmp_path))
    msg = build_map_message("compliance", "run a check", "check jane's records", ws)
    assert "check jane's records" in msg


def test_build_map_message_lists_clients(tmp_path):
    (tmp_path / "clients" / "alice").mkdir(parents=True)
    (tmp_path / "clients" / "bob").mkdir(parents=True)
    ws = Workspace(str(tmp_path))
    msg = build_map_message("session", "generate a note", None, ws)
    assert "alice" in msg
    assert "bob" in msg


def test_build_map_message_no_clients(tmp_path):
    ws = Workspace(str(tmp_path))
    msg = build_map_message("compliance", "run a compliance check", None, ws)
    assert "No clients exist" in msg


# --- /compliance fast path and map path ---

def test_compliance_fast_path(tmp_path):
    """Valid single-token client-id -> fast path with formatted prompt, map_mode=True."""
    (tmp_path / "clients" / "jane-doe").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("compliance", "jane-doe", ui, ws)
    assert result.error is None
    assert result.message is not None
    assert "jane-doe" in result.message
    assert result.map_mode is True
    assert "[MAP:" not in result.message


def test_compliance_no_args_map_path(tmp_path):
    """No args -> map path, no error."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("compliance", None, ui, ws)
    assert result.error is None
    assert "[MAP: compliance]" in result.message


def test_compliance_invalid_client_map_path(tmp_path):
    """Invalid client -> map path, no error."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("compliance", "nonexistent", ui, ws)
    assert result.error is None
    assert "[MAP: compliance]" in result.message


def test_compliance_natural_language_map_path(tmp_path):
    """Multi-word args -> map path with user input preserved."""
    (tmp_path / "clients" / "jane-doe").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("compliance", "check jane's records", ui, ws)
    assert result.error is None
    assert "[MAP: compliance]" in result.message
    assert "check jane's records" in result.message
    assert "jane-doe" in result.message  # available clients listed


# --- /tp-review fast path and map path ---

def test_tp_review_fast_path(tmp_path):
    """Valid client -> fast path with prompt, map_mode=True."""
    (tmp_path / "clients" / "bob").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("tp-review", "bob", ui, ws)
    assert result.error is None
    assert result.map_mode is True
    assert "[MAP:" not in result.message
    assert "bob" in result.message


def test_tp_review_no_args_map_path(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("tp-review", None, ui, ws)
    assert result.error is None
    assert "[MAP: tp-review]" in result.message


# --- /session fast path and map path ---

def test_session_fast_path(tmp_path):
    """Valid client + file remainder -> fast path with plan_prompt."""
    (tmp_path / "clients" / "alice").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("session", "alice recording.m4a", ui, ws)
    assert result.error is None
    assert result.map_mode is True
    assert result.plan_prompt is not None
    assert "recording.m4a" in result.message
    assert "recording.m4a" in result.plan_prompt
    assert "[MAP:" not in result.message


def test_session_fast_path_has_tool_discovery(tmp_path):
    """Fast path tells LLM to load client context via tools."""
    (tmp_path / "clients" / "alice").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("session", "alice recording.m4a", ui, ws)
    assert "run_command ls" in result.message


def test_session_fast_path_matches_activate_map_prompt(tmp_path):
    """Slash-map fast path and activate_map share the same execution prompt."""
    (tmp_path / "clients" / "alice").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))

    command_result = dispatch_map("session", "alice recording.m4a", ui, ws)
    tool_result = ActivateMapTool().execute(
        ws, map="session", source="slash", client_id="alice", file_reference="recording.m4a"
    )

    assert command_result.message == tool_result


def test_session_no_args_map_path(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("session", None, ui, ws)
    assert result.error is None
    assert "[MAP: session]" in result.message


def test_session_client_only_map_path(tmp_path):
    """Client-id but no remainder -> map path."""
    (tmp_path / "clients" / "alice").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("session", "alice", ui, ws)
    assert result.error is None
    assert "[MAP: session]" in result.message


# --- /wellness-assessment fast path and map path ---

def test_wa_fast_path(tmp_path):
    """Valid client + file remainder -> fast path."""
    (tmp_path / "clients" / "carol").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("wellness-assessment", "carol wa-scan.pdf", ui, ws)
    assert result.error is None
    assert result.map_mode is True
    assert "wa-scan.pdf" in result.message
    assert "[MAP:" not in result.message


def test_wa_no_args_map_path(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("wellness-assessment", None, ui, ws)
    assert result.error is None
    assert "[MAP: wellness-assessment]" in result.message
