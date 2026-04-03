from unittest.mock import MagicMock

from cfi_ai.commands import parse_command, dispatch, CommandResult, build_skill_message
from cfi_ai.prompts.intake import INTAKE_FILE_WORKFLOW_PROMPT
from cfi_ai.tools.activate_workflow import ActivateWorkflowTool
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
    assert result.workflow_mode is False
    assert result.plan_prompt is None


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


# --- build_skill_message tests ---

def test_build_skill_message_basic(tmp_path):
    ws = Workspace(str(tmp_path))
    msg = build_skill_message("compliance", "run a compliance check", None, ws)
    assert "[SKILL: compliance]" in msg
    assert "run a compliance check" in msg
    assert "activate_workflow" in msg
    assert "interview" in msg


def test_build_skill_message_with_user_input(tmp_path):
    ws = Workspace(str(tmp_path))
    msg = build_skill_message("compliance", "run a check", "check jane's records", ws)
    assert "check jane's records" in msg


def test_build_skill_message_lists_clients(tmp_path):
    (tmp_path / "clients" / "alice").mkdir(parents=True)
    (tmp_path / "clients" / "bob").mkdir(parents=True)
    ws = Workspace(str(tmp_path))
    msg = build_skill_message("session", "generate a note", None, ws)
    assert "alice" in msg
    assert "bob" in msg


def test_build_skill_message_no_clients(tmp_path):
    ws = Workspace(str(tmp_path))
    msg = build_skill_message("intake", "process intake", None, ws)
    assert "No clients exist" in msg


# --- /compliance fast path and skill path ---

def test_compliance_fast_path(tmp_path):
    """Valid single-token client-id → fast path with formatted prompt."""
    (tmp_path / "clients" / "jane-doe" / "intake").mkdir(parents=True)
    (tmp_path / "clients" / "jane-doe" / "intake" / "2025-01-01-initial-assessment.md").write_text("# Assessment")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("compliance", "jane-doe", ui, ws)
    assert result.error is None
    assert result.message is not None
    assert "jane-doe" in result.message
    assert result.workflow_mode is False
    # Fast path uses COMPLIANCE_PROMPT, not skill message
    assert "[SKILL:" not in result.message


def test_compliance_no_args_skill_path(tmp_path):
    """No args → skill path, no error."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("compliance", None, ui, ws)
    assert result.error is None
    assert "[SKILL: compliance]" in result.message


def test_compliance_invalid_client_skill_path(tmp_path):
    """Invalid client → skill path, no error."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("compliance", "nonexistent", ui, ws)
    assert result.error is None
    assert "[SKILL: compliance]" in result.message


def test_compliance_empty_context_falls_to_skill_path(tmp_path):
    """Client dir exists but has no clinical files → skill path."""
    (tmp_path / "clients" / "jane-doe").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("compliance", "jane-doe", ui, ws)
    assert result.error is None
    assert "[SKILL: compliance]" in result.message


def test_compliance_natural_language_skill_path(tmp_path):
    """Multi-word args → skill path with user input preserved."""
    (tmp_path / "clients" / "jane-doe").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("compliance", "check jane's records", ui, ws)
    assert result.error is None
    assert "[SKILL: compliance]" in result.message
    assert "check jane's records" in result.message
    assert "jane-doe" in result.message  # available clients listed


# --- /tp-review fast path and skill path ---

def test_tp_review_fast_path(tmp_path):
    """Valid client with TP + progress note → fast path."""
    (tmp_path / "clients" / "bob" / "treatment-plan").mkdir(parents=True)
    (tmp_path / "clients" / "bob" / "treatment-plan" / "current.md").write_text("# TP")
    (tmp_path / "clients" / "bob" / "sessions").mkdir(parents=True)
    (tmp_path / "clients" / "bob" / "sessions" / "2025-01-15-progress-note.md").write_text("# Note")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("tp-review", "bob", ui, ws)
    assert result.error is None
    assert result.workflow_mode is True
    assert "[SKILL:" not in result.message


def test_tp_review_no_tp_falls_to_skill_path(tmp_path):
    """Client exists with sessions but no treatment plan → skill path."""
    (tmp_path / "clients" / "bob" / "sessions").mkdir(parents=True)
    (tmp_path / "clients" / "bob" / "sessions" / "2025-01-15-progress-note.md").write_text("# Note")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("tp-review", "bob", ui, ws)
    assert result.error is None
    assert "[SKILL: tp-review]" in result.message


def test_tp_review_no_notes_falls_to_skill_path(tmp_path):
    """Client exists with treatment plan but no progress notes → skill path."""
    (tmp_path / "clients" / "bob" / "treatment-plan").mkdir(parents=True)
    (tmp_path / "clients" / "bob" / "treatment-plan" / "current.md").write_text("# TP")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("tp-review", "bob", ui, ws)
    assert result.error is None
    assert "[SKILL: tp-review]" in result.message


def test_tp_review_no_args_skill_path(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("tp-review", None, ui, ws)
    assert result.error is None
    assert "[SKILL: tp-review]" in result.message


# --- /session fast path and skill path ---

def test_session_fast_path(tmp_path):
    """Valid client + file remainder → fast path with plan_prompt."""
    (tmp_path / "clients" / "alice" / "profile").mkdir(parents=True)
    (tmp_path / "clients" / "alice" / "profile" / "current.md").write_text("# Profile")
    (tmp_path / "clients" / "alice" / "treatment-plan").mkdir(parents=True)
    (tmp_path / "clients" / "alice" / "treatment-plan" / "current.md").write_text("# TP")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("session", "alice recording.m4a", ui, ws)
    assert result.error is None
    assert result.workflow_mode is True
    assert result.plan_prompt is not None
    assert "recording.m4a" in result.message
    assert "recording.m4a" in result.plan_prompt
    assert "[SKILL:" not in result.message


def test_session_fast_path_includes_reminders(tmp_path):
    """Fast path preserves clinical reminders in the execution prompt."""
    (tmp_path / "clients" / "alice" / "profile").mkdir(parents=True)
    (tmp_path / "clients" / "alice" / "profile" / "current.md").write_text("# Profile")
    (tmp_path / "clients" / "alice" / "treatment-plan").mkdir(parents=True)
    (tmp_path / "clients" / "alice" / "treatment-plan" / "current.md").write_text(
        "# TP\n**Initiation Date** — 2024-01-01"
    )
    ui = MagicMock()
    ws = Workspace(str(tmp_path))

    result = dispatch("session", "alice recording.m4a", ui, ws)

    assert "## Clinical Reminders" in result.message
    assert "No Wellness Assessment" in result.message
    assert "Treatment Plan review is past due" in result.message
    assert "recording.m4a" in result.message
    assert "recording.m4a" in result.plan_prompt


def test_session_fast_path_matches_activate_workflow_prompt(tmp_path):
    """Slash-command fast path and activate_workflow share the same execution prompt."""
    (tmp_path / "clients" / "alice" / "profile").mkdir(parents=True)
    (tmp_path / "clients" / "alice" / "profile" / "current.md").write_text("# Profile")
    (tmp_path / "clients" / "alice" / "treatment-plan").mkdir(parents=True)
    (tmp_path / "clients" / "alice" / "treatment-plan" / "current.md").write_text(
        "# TP\n**Initiation Date** — 2024-01-01"
    )
    ui = MagicMock()
    ws = Workspace(str(tmp_path))

    command_result = dispatch("session", "alice recording.m4a", ui, ws)
    tool_result = ActivateWorkflowTool().execute(
        ws, workflow="session", client_id="alice", file_reference="recording.m4a"
    )

    assert command_result.message == tool_result


def test_session_no_args_skill_path(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("session", None, ui, ws)
    assert result.error is None
    assert "[SKILL: session]" in result.message


def test_session_client_only_skill_path(tmp_path):
    """Client-id but no remainder → skill path."""
    (tmp_path / "clients" / "alice").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("session", "alice", ui, ws)
    assert result.error is None
    assert "[SKILL: session]" in result.message


# --- /wellness-assessment fast path and skill path ---

def test_wa_fast_path(tmp_path):
    """Valid client + file remainder → fast path."""
    (tmp_path / "clients" / "carol" / "profile").mkdir(parents=True)
    (tmp_path / "clients" / "carol" / "profile" / "current.md").write_text("# Profile")
    (tmp_path / "clients" / "carol" / "treatment-plan").mkdir(parents=True)
    (tmp_path / "clients" / "carol" / "treatment-plan" / "current.md").write_text("# TP")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("wellness-assessment", "carol wa-scan.pdf", ui, ws)
    assert result.error is None
    assert result.workflow_mode is True
    assert "wa-scan.pdf" in result.message
    assert "[SKILL:" not in result.message


def test_wa_no_args_skill_path(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch("wellness-assessment", None, ui, ws)
    assert result.error is None
    assert "[SKILL: wellness-assessment]" in result.message
