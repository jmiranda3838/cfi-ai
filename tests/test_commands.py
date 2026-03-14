from unittest.mock import MagicMock

from cfi_ai.commands import parse_command, dispatch, CommandResult
from cfi_ai.prompts.intake import INTAKE_FILE_WORKFLOW_PROMPT
from cfi_ai.workspace import Workspace


# --- parse_command tests ---

def test_parse_command_not_a_command():
    assert parse_command("hello world") is None


def test_parse_command_empty():
    assert parse_command("") is None


def test_parse_command_slash_only():
    assert parse_command("/") is None


def test_parse_command_simple():
    assert parse_command("/help") == ("help", None)


def test_parse_command_with_args():
    assert parse_command("/intake transcript.txt") == ("intake", "transcript.txt")


def test_parse_command_with_spaces():
    assert parse_command("  /help  ") == ("help", None)


def test_parse_command_multi_word_args():
    assert parse_command("/intake some file path.txt") == ("intake", "some file path.txt")


# --- dispatch tests ---

def test_dispatch_unknown_command():
    ui = MagicMock()
    ws = Workspace("/tmp")
    result = dispatch("nonexistent", None, ui, ws)
    assert result.error is not None
    assert "Unknown command" in result.error


def test_dispatch_help():
    ui = MagicMock()
    ws = Workspace("/tmp")
    result = dispatch("help", None, ui, ws)
    assert result.handled is True
    assert result.message is None
    assert result.error is None
    ui.render_markdown.assert_called_once()


def test_dispatch_help_lists_commands():
    ui = MagicMock()
    ws = Workspace("/tmp")
    dispatch("help", None, ui, ws)
    rendered = ui.render_markdown.call_args[0][0]
    assert "/help" in rendered
    assert "/intake" in rendered


# --- CommandResult tests ---

def test_command_result_parts_default():
    result = CommandResult()
    assert result.parts is None
    assert result.message is None
    assert result.handled is False
    assert result.error is None


# --- File workflow prompt tests ---

def test_file_prompt_has_placeholders():
    """INTAKE_FILE_WORKFLOW_PROMPT formats without error."""
    formatted = INTAKE_FILE_WORKFLOW_PROMPT.format(
        date="2026-03-13",
        existing_clients="## Existing Clients\nNone.",
        file_reference="session.mp3",
    )
    assert "2026-03-13" in formatted
    assert "session.mp3" in formatted
    assert "{file_reference}" not in formatted
    assert "{date}" not in formatted
    assert "{existing_clients}" not in formatted
