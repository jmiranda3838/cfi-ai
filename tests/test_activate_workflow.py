"""Tests for the activate_workflow tool."""

import datetime
from pathlib import Path

import pytest

from cfi_ai.workspace import Workspace
from cfi_ai.tools.activate_workflow import ActivateWorkflowTool, NON_WORKFLOW_MODE
import cfi_ai.tools as tools


def _make_workspace(tmp_path: Path) -> Workspace:
    return Workspace(str(tmp_path))


def _make_client(tmp_path: Path, client_id: str) -> None:
    """Create a minimal client directory structure."""
    base = tmp_path / "clients" / client_id
    base.mkdir(parents=True)


def _make_client_with_profile(tmp_path: Path, client_id: str) -> None:
    """Create a client with profile and treatment plan."""
    base = tmp_path / "clients" / client_id
    (base / "profile").mkdir(parents=True)
    (base / "profile" / "current.md").write_text("# Profile\nTest client profile")
    (base / "treatment-plan").mkdir(parents=True)
    (base / "treatment-plan" / "current.md").write_text(
        "# Treatment Plan\n**Initiation Date** — 2025-01-01"
    )


def _make_client_full(tmp_path: Path, client_id: str) -> None:
    """Create a client with all clinical files for compliance/tp-review."""
    _make_client_with_profile(tmp_path, client_id)
    base = tmp_path / "clients" / client_id

    (base / "intake").mkdir(parents=True)
    (base / "intake" / "2025-01-01-initial-assessment.md").write_text("# Assessment")

    (base / "sessions").mkdir(parents=True)
    (base / "sessions" / "2025-01-15-progress-note.md").write_text("# Note 1")
    (base / "sessions" / "2025-02-01-progress-note.md").write_text("# Note 2")


def _make_client_with_wa(tmp_path: Path, client_id: str, wa_count: int = 1) -> None:
    """Create a client with wellness assessment files."""
    _make_client_with_profile(tmp_path, client_id)
    base = tmp_path / "clients" / client_id
    (base / "wellness-assessments").mkdir(parents=True)
    for i in range(wa_count):
        date = f"2025-0{i + 1}-01"
        (base / "wellness-assessments" / f"{date}-wellness-assessment.md").write_text(
            f"# WA {i + 1}"
        )


# --- Tool registration ---

def test_tool_in_registry():
    assert "activate_workflow" in {
        fd.name for fd in tools.get_api_tools().function_declarations
    }


def test_tool_not_mutating():
    tool = ActivateWorkflowTool()
    assert tool.mutating is False


def test_tool_not_in_readonly_set():
    readonly = tools.get_readonly_api_tools()
    names = {fd.name for fd in readonly.function_declarations}
    assert "activate_workflow" not in names


# --- Invalid input ---

def test_unknown_workflow(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(ws, workflow="bogus")
    assert result.startswith("Error:")
    assert "bogus" in result


def test_missing_client_id_for_session(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(ws, workflow="session")
    assert result.startswith("Error:")
    assert "client_id" in result


def test_missing_client_id_for_compliance(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(ws, workflow="compliance")
    assert result.startswith("Error:")
    assert "client_id" in result


def test_missing_client_id_for_tp_review(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(ws, workflow="tp-review")
    assert result.startswith("Error:")


def test_missing_client_id_for_wa(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(ws, workflow="wellness-assessment")
    assert result.startswith("Error:")


def test_nonexistent_client(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="session", client_id="nobody"
    )
    assert result.startswith("Error:")
    assert "nobody" in result
    assert "not found" in result


def test_missing_client_lists_available(tmp_path):
    _make_client(tmp_path, "alice")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="session", client_id="nobody"
    )
    assert "alice" in result


# --- Intake workflow ---

def test_intake_no_files(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(ws, workflow="intake")
    assert not result.startswith("Error:")
    assert "intake" in result.lower() or "assessment" in result.lower()
    # Should use text-variant placeholder
    assert "conversation above" in result


def test_intake_with_file_reference(tmp_path):
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="intake", file_reference="recording.m4a"
    )
    assert not result.startswith("Error:")
    assert "recording.m4a" in result


def test_intake_shows_existing_clients(tmp_path):
    _make_client(tmp_path, "jane-doe")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(ws, workflow="intake")
    assert "jane-doe" in result


def test_intake_no_client_id_needed(tmp_path):
    """Intake should work without client_id."""
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(ws, workflow="intake")
    assert not result.startswith("Error:")


# --- Session workflow ---

def test_session_with_file(tmp_path):
    _make_client_with_profile(tmp_path, "bob")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="session", client_id="bob", file_reference="session.m4a"
    )
    assert not result.startswith("Error:")
    assert "session.m4a" in result
    assert "bob" in result


def test_session_without_file(tmp_path):
    _make_client_with_profile(tmp_path, "bob")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="session", client_id="bob"
    )
    assert not result.startswith("Error:")
    assert "conversation above" in result


def test_session_includes_client_context(tmp_path):
    _make_client_with_profile(tmp_path, "bob")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="session", client_id="bob"
    )
    assert "Test client profile" in result


def test_session_includes_progress_note_guidance(tmp_path):
    _make_client_with_profile(tmp_path, "bob")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="session", client_id="bob"
    )
    today = datetime.date.today().isoformat()
    assert today in result


# --- Compliance workflow ---

def test_compliance_happy_path(tmp_path):
    _make_client_full(tmp_path, "alice")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="compliance", client_id="alice"
    )
    assert not result.startswith("Error:")
    assert "alice" in result


def test_compliance_minimal_client(tmp_path):
    """Compliance still works with minimal data (LLM will note sparse records)."""
    _make_client(tmp_path, "empty")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="compliance", client_id="empty"
    )
    # load_compliance_context always returns at least the WA count line
    assert not result.startswith("Error:")
    assert "empty" in result


def test_compliance_in_non_workflow_mode():
    assert "compliance" in NON_WORKFLOW_MODE


# --- TP Review workflow ---

def test_tp_review_happy_path(tmp_path):
    _make_client_full(tmp_path, "alice")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="tp-review", client_id="alice"
    )
    assert not result.startswith("Error:")
    assert "alice" in result


def test_tp_review_no_treatment_plan(tmp_path):
    _make_client(tmp_path, "new-client")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="tp-review", client_id="new-client"
    )
    assert result.startswith("Error:")
    assert "No treatment plan" in result


def test_tp_review_no_progress_notes(tmp_path):
    _make_client_with_profile(tmp_path, "no-notes")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="tp-review", client_id="no-notes"
    )
    assert result.startswith("Error:")
    assert "No progress notes" in result


# --- Wellness Assessment workflow ---

def test_wa_initial(tmp_path):
    _make_client_with_profile(tmp_path, "carol")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="wellness-assessment", client_id="carol"
    )
    assert not result.startswith("Error:")
    assert "initial" in result


def test_wa_readministration(tmp_path):
    _make_client_with_wa(tmp_path, "carol", wa_count=2)
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="wellness-assessment", client_id="carol"
    )
    assert not result.startswith("Error:")
    assert "re-administration" in result
    assert "#3" in result  # admin_number = 2 + 1


def test_wa_with_file(tmp_path):
    _make_client_with_profile(tmp_path, "carol")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="wellness-assessment", client_id="carol",
        file_reference="wa-scan.pdf"
    )
    assert not result.startswith("Error:")
    assert "wa-scan.pdf" in result


def test_wa_without_file(tmp_path):
    _make_client_with_profile(tmp_path, "carol")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="wellness-assessment", client_id="carol"
    )
    assert not result.startswith("Error:")
    assert "conversation above" in result


def test_wa_includes_history(tmp_path):
    _make_client_with_wa(tmp_path, "carol", wa_count=1)
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="wellness-assessment", client_id="carol"
    )
    assert "WA 1" in result


# --- Session reminders ---

def test_session_reminders_no_wa(tmp_path):
    _make_client_with_profile(tmp_path, "dana")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="session", client_id="dana"
    )
    assert "No Wellness Assessment" in result


def test_session_reminders_tp_review_overdue(tmp_path):
    _make_client_with_profile(tmp_path, "eve")
    # Set initiation date far enough back that review is overdue
    tp = tmp_path / "clients" / "eve" / "treatment-plan" / "current.md"
    tp.write_text("# TP\n**Initiation Date** — 2024-01-01")
    ws = _make_workspace(tmp_path)
    result = ActivateWorkflowTool().execute(
        ws, workflow="session", client_id="eve"
    )
    assert "past due" in result
