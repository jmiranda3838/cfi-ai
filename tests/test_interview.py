"""Tests for the interview tool and its UI/agent integration."""

import pytest
from unittest.mock import patch, MagicMock

from google.genai import types

from cfi_ai.tools.interview import InterviewTool
from cfi_ai.workspace import Workspace
import cfi_ai.tools as tools


# --- Tool definition and registry tests ---


def test_interview_tool_definition():
    """InterviewTool schema has the expected properties."""
    defn = InterviewTool().definition()
    assert defn.name == "interview"
    schema = defn.input_schema
    assert schema["required"] == ["questions"]
    item_props = schema["properties"]["questions"]["items"]["properties"]
    assert "id" in item_props
    assert "text" in item_props
    assert "options" in item_props
    assert "multiline" in item_props
    assert "default" in item_props
    item_required = schema["properties"]["questions"]["items"]["required"]
    assert "id" in item_required
    assert "text" in item_required


def test_interview_tool_execute_returns_error():
    """execute() returns an error string (never called normally)."""
    ws = Workspace("/tmp")
    result = InterviewTool().execute(ws)
    assert "Error" in result
    assert "agent loop" in result


def test_interview_not_mutating():
    """interview should not be classified as mutating."""
    assert tools.classify_mutation("interview", {}) is False
    assert "interview" not in tools.MUTATING_TOOLS


def test_interview_in_all_tools():
    """interview is in the full tool set."""
    all_tools = tools.get_api_tools()
    names = {fd.name for fd in all_tools[0].function_declarations}
    assert "interview" in names


# --- _handle_interview tests ---


def _make_ui(tmp_path):
    """Create a UI instance with mocked session."""
    with patch("cfi_ai.ui.Path.home", return_value=tmp_path), \
         patch("cfi_ai.ui.PromptSession") as mock_session_cls:
        from cfi_ai.ui import UI
        ui = UI()
    return ui, mock_session_cls.return_value


def test_handle_interview_empty_questions(tmp_path):
    """Empty questions list returns a 'no questions' response."""
    from cfi_ai.agent import _handle_interview
    ui, _ = _make_ui(tmp_path)
    part = _handle_interview(ui, "interview", {"questions": []})
    resp = part.function_response.response
    assert resp["answers"] == []
    assert "No questions" in resp["note"]


def test_handle_interview_cancelled(tmp_path):
    """When run_interview returns None, returns error response."""
    from cfi_ai.agent import _handle_interview
    ui, _ = _make_ui(tmp_path)
    ui.run_interview = MagicMock(return_value=None)
    part = _handle_interview(ui, "interview", {
        "questions": [{"id": "q1", "text": "Test?"}]
    })
    resp = part.function_response.response
    assert "error" in resp
    assert "cancelled" in resp["error"].lower()


def test_handle_interview_success(tmp_path):
    """Successful interview returns answers."""
    from cfi_ai.agent import _handle_interview
    ui, _ = _make_ui(tmp_path)
    ui.run_interview = MagicMock(return_value=[
        {"id": "name", "answer": "jane-doe"},
        {"id": "date", "answer": "2026-04-07"},
    ])
    part = _handle_interview(ui, "interview", {
        "questions": [
            {"id": "name", "text": "Client name?"},
            {"id": "date", "text": "Date?"},
        ]
    })
    resp = part.function_response.response
    assert len(resp["answers"]) == 2
    assert resp["answers"][0]["id"] == "name"
    assert resp["answers"][0]["answer"] == "jane-doe"
    assert resp["answers"][1]["id"] == "date"
    assert resp["answers"][1]["answer"] == "2026-04-07"


# --- UI.run_interview tests ---


def test_run_interview_basic_flow(tmp_path):
    """Basic Q&A flow returns answers."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.side_effect = ["jane-doe", "2026-04-07"]
    questions = [
        {"id": "name", "text": "Client name?"},
        {"id": "date", "text": "Date?"},
    ]
    answers = ui.run_interview(questions)
    assert answers is not None
    assert len(answers) == 2
    assert answers[0] == {"id": "name", "answer": "jane-doe"}
    assert answers[1] == {"id": "date", "answer": "2026-04-07"}


def test_run_interview_option_selection(tmp_path):
    """Typing a number selects the corresponding option."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.return_value = "2"
    questions = [
        {"id": "client", "text": "Which client?", "options": ["alice", "bob", "carol"]},
    ]
    answers = ui.run_interview(questions)
    assert answers is not None
    assert answers[0]["answer"] == "bob"


def test_run_interview_custom_over_options(tmp_path):
    """Non-numeric input is used as custom answer even when options exist."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.return_value = "dave"
    questions = [
        {"id": "client", "text": "Which client?", "options": ["alice", "bob"]},
    ]
    answers = ui.run_interview(questions)
    assert answers is not None
    assert answers[0]["answer"] == "dave"


def test_run_interview_default_value(tmp_path):
    """Empty input uses the default value."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.return_value = ""
    questions = [
        {"id": "date", "text": "Intake date?", "default": "2026-04-01"},
    ]
    answers = ui.run_interview(questions)
    assert answers is not None
    assert answers[0]["answer"] == "2026-04-01"


def test_run_interview_cancel(tmp_path):
    """EOFError (Escape) cancels the interview."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.side_effect = EOFError
    questions = [{"id": "q1", "text": "Question?"}]
    result = ui.run_interview(questions)
    assert result is None


def test_run_interview_keyboard_interrupt_propagates(tmp_path):
    """KeyboardInterrupt is not caught — propagates up."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.side_effect = KeyboardInterrupt
    questions = [{"id": "q1", "text": "Question?"}]
    with pytest.raises(KeyboardInterrupt):
        ui.run_interview(questions)


def test_run_interview_empty_no_default_reprompts(tmp_path):
    """Empty input with no default re-prompts instead of cancelling."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.side_effect = ["", "actual-answer"]
    questions = [{"id": "q1", "text": "Question?"}]
    result = ui.run_interview(questions)
    assert result is not None
    assert result == [{"id": "q1", "answer": "actual-answer"}]
    assert mock_session.prompt.call_count == 2


def test_run_interview_option_out_of_range(tmp_path):
    """Number outside option range is treated as custom text."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.return_value = "99"
    questions = [
        {"id": "q1", "text": "Pick?", "options": ["a", "b"]},
    ]
    answers = ui.run_interview(questions)
    assert answers is not None
    assert answers[0]["answer"] == "99"


def test_run_interview_empty_preserves_previous_answers(tmp_path):
    """Empty input on question 2 re-prompts without losing question 1's answer."""
    ui, mock_session = _make_ui(tmp_path)
    # Q1: "alice", Q2: "" (re-prompt), Q2 retry: "2026-04-01"
    mock_session.prompt.side_effect = ["alice", "", "2026-04-01"]
    questions = [
        {"id": "name", "text": "Client name?"},
        {"id": "date", "text": "Date?"},
    ]
    answers = ui.run_interview(questions)
    assert answers is not None
    assert len(answers) == 2
    assert answers[0] == {"id": "name", "answer": "alice"}
    assert answers[1] == {"id": "date", "answer": "2026-04-01"}


def test_run_interview_empty_then_escape_cancels(tmp_path):
    """Empty input followed by Escape still cancels."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.side_effect = ["", EOFError]
    questions = [{"id": "q1", "text": "Question?"}]
    result = ui.run_interview(questions)
    assert result is None


def test_run_interview_whitespace_only_reprompts(tmp_path):
    """Whitespace-only input is treated as empty and re-prompts."""
    ui, mock_session = _make_ui(tmp_path)
    mock_session.prompt.side_effect = ["   ", "real"]
    questions = [{"id": "q1", "text": "Question?"}]
    answers = ui.run_interview(questions)
    assert answers is not None
    assert answers[0]["answer"] == "real"


def test_run_interview_single_line_passes_multiline_false(tmp_path):
    """Single-line questions must explicitly pass multiline=False so a prior
    multiline question (which leaves session.multiline=True permanently) cannot
    pollute the next single-line question's Enter handling."""
    ui, mock_session = _make_ui(tmp_path)
    # Simulate session state polluted by a prior multiline call
    mock_session.multiline = True
    mock_session.prompt.return_value = "answer"

    questions = [{"id": "q1", "text": "Single-line question?"}]
    answers = ui.run_interview(questions)
    assert answers == [{"id": "q1", "answer": "answer"}]

    _, kwargs = mock_session.prompt.call_args
    assert kwargs.get("multiline") is False
