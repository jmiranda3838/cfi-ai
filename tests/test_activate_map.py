"""Tests for the activate_map tool."""

import datetime
from pathlib import Path

import cfi_ai.tools as tools
from cfi_ai.tools.activate_map import ActivateMapTool, get_map_plan_prompt
from cfi_ai.workspace import Workspace


def _make_workspace(tmp_path: Path) -> Workspace:
    return Workspace(str(tmp_path))


def _execute_map(ws: Workspace, **kwargs) -> str:
    kwargs.setdefault("source", "implicit")
    return ActivateMapTool().execute(ws, **kwargs)


def _make_client(tmp_path: Path, client_id: str) -> None:
    """Create a minimal client directory structure."""
    base = tmp_path / "clients" / client_id
    base.mkdir(parents=True)


def test_tool_in_registry():
    assert "activate_map" in {
        fd.name for fd in tools.get_api_tools()[0].function_declarations
    }


def test_tool_not_mutating():
    tool = ActivateMapTool()
    assert tool.mutating is False


def test_tool_in_readonly_set():
    readonly = tools.get_readonly_api_tools()
    names = {fd.name for fd in readonly[0].function_declarations}
    assert "activate_map" in names


def test_unknown_map(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="bogus")
    assert result.startswith("Error:")
    assert "bogus" in result


def test_missing_client_id_for_session(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="session")
    assert result.startswith("Error:")
    assert "client_id" in result


def test_missing_client_id_for_compliance(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="compliance")
    assert result.startswith("Error:")
    assert "client_id" in result


def test_missing_client_id_for_tp_review(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="tp-review")
    assert result.startswith("Error:")


def test_missing_client_id_for_wa(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="wellness-assessment")
    assert result.startswith("Error:")


def test_nonexistent_client(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="session", client_id="nobody")
    assert result.startswith("Error:")
    assert "nobody" in result
    assert "not found" in result


def test_missing_client_lists_available(tmp_path):
    _make_client(tmp_path, "alice")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="session", client_id="nobody")
    assert "alice" in result


def test_intake_no_files(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="intake")
    assert not result.startswith("Error:")
    assert "intake" in result.lower() or "assessment" in result.lower()
    assert "conversation above" in result


def test_intake_with_file_reference(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="intake", file_reference="recording.m4a")
    assert not result.startswith("Error:")
    assert "recording.m4a" in result


def test_intake_no_client_id_needed(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="intake")
    assert not result.startswith("Error:")


def test_intake_has_client_discovery(tmp_path):
    """Intake prompt tells LLM to discover clients via tools."""
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="intake")
    assert "run_command ls clients/" in result


def test_session_with_file(tmp_path):
    _make_client(tmp_path, "bob")
    ws = _make_workspace(tmp_path)
    result = _execute_map(
        ws, map="session", client_id="bob", file_reference="session.m4a"
    )
    assert not result.startswith("Error:")
    assert "session.m4a" in result
    assert "bob" in result


def test_session_without_file(tmp_path):
    _make_client(tmp_path, "bob")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="session", client_id="bob")
    assert not result.startswith("Error:")
    assert "conversation above" in result


def test_session_has_tool_discovery(tmp_path):
    """Session prompt tells LLM to load client context via tools."""
    _make_client(tmp_path, "bob")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="session", client_id="bob")
    assert "run_command ls" in result


def test_session_includes_progress_note_guidance(tmp_path):
    _make_client(tmp_path, "bob")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="session", client_id="bob")
    today = datetime.date.today().isoformat()
    assert today in result


def test_compliance_happy_path(tmp_path):
    _make_client(tmp_path, "alice")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="compliance", client_id="alice")
    assert not result.startswith("Error:")
    assert "alice" in result
    assert "run_command ls" in result  # tool discovery instructions


def test_compliance_minimal_client(tmp_path):
    """Empty client dir still returns prompt (LLM discovers missing files)."""
    _make_client(tmp_path, "empty")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="compliance", client_id="empty")
    assert not result.startswith("Error:")
    assert "empty" in result


def test_compliance_prompt_mentions_missing_records_as_findings(tmp_path):
    _make_client(tmp_path, "alice")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="compliance", client_id="alice")
    assert "Missing documentation is a valid audit finding" in result
    assert "Do NOT invent cross-document comparisons" in result


def test_tp_review_happy_path(tmp_path):
    _make_client(tmp_path, "alice")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="tp-review", client_id="alice")
    assert not result.startswith("Error:")
    assert "alice" in result
    assert "run_command ls" in result  # tool discovery instructions


def test_tp_review_minimal_client(tmp_path):
    """Client with no files still returns prompt (LLM discovers prerequisites)."""
    _make_client(tmp_path, "new-client")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="tp-review", client_id="new-client")
    assert not result.startswith("Error:")
    assert "new-client" in result


def test_tp_review_prompt_mentions_missing_prereq_stop(tmp_path):
    _make_client(tmp_path, "alice")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="tp-review", client_id="alice")
    assert "You must have the latest treatment plan." in result
    assert "do not call `write_file`" in result


def test_wa_with_file(tmp_path):
    _make_client(tmp_path, "carol")
    ws = _make_workspace(tmp_path)
    result = _execute_map(
        ws,
        map="wellness-assessment",
        client_id="carol",
        file_reference="wa-scan.pdf",
    )
    assert not result.startswith("Error:")
    assert "wa-scan.pdf" in result


def test_wa_without_file(tmp_path):
    _make_client(tmp_path, "carol")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="wellness-assessment", client_id="carol")
    assert not result.startswith("Error:")
    assert "conversation above" in result


def test_wa_has_tool_discovery(tmp_path):
    """WA prompt tells LLM to discover admin type via tools."""
    _make_client(tmp_path, "carol")
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="wellness-assessment", client_id="carol")
    assert "run_command ls" in result
    assert "initial" in result  # prompt mentions initial/re-administration logic


def test_get_map_plan_prompt_intake_with_file(tmp_path):
    ws = _make_workspace(tmp_path)
    result = get_map_plan_prompt(
        "intake", ws, file_reference="recording.m4a", date="2025-06-01"
    )
    assert result is not None
    assert "recording.m4a" in result


def test_get_map_plan_prompt_session_with_file(tmp_path):
    _make_client(tmp_path, "bob")
    ws = _make_workspace(tmp_path)
    result = get_map_plan_prompt(
        "session", ws, file_reference="session.m4a", client_id="bob", date="2025-06-01"
    )
    assert result is not None
    assert "bob" in result
    assert "session.m4a" in result


def test_get_map_plan_prompt_intake_always_returns(tmp_path):
    """Intake always returns a plan prompt, even without file_reference."""
    ws = _make_workspace(tmp_path)
    result = get_map_plan_prompt("intake", ws)
    assert result is not None
    assert "Intake Map" in result


def test_get_map_plan_prompt_returns_none_for_others(tmp_path):
    ws = _make_workspace(tmp_path)
    assert get_map_plan_prompt("session", ws, client_id="bob") is None
    assert get_map_plan_prompt("compliance", ws, client_id="bob") is None


def test_no_current_md_in_prompts(tmp_path):
    """No prompt output should contain current.md references."""
    _make_client(tmp_path, "test")
    ws = _make_workspace(tmp_path)
    for map_name, kwargs in [
        ("intake", {}),
        ("session", {"client_id": "test"}),
        ("compliance", {"client_id": "test"}),
        ("tp-review", {"client_id": "test"}),
        ("wellness-assessment", {"client_id": "test"}),
    ]:
        result = _execute_map(ws, map=map_name, **kwargs)
        assert "current.md" not in result, f"{map_name} prompt contains current.md"


def test_activate_map_description_no_client_context():
    """Tool description should say 'instructions' not 'client context'."""
    tool = ActivateMapTool()
    defn = tool.definition()
    assert "client context" not in defn.description
    assert "instructions" in defn.description
