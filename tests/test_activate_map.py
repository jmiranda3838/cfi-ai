"""Tests for the activate_map tool."""

import datetime
from pathlib import Path

import cfi_ai.tools as tools
from cfi_ai.tools.activate_map import ActivateMapTool
from cfi_ai.workspace import Workspace


def _make_workspace(tmp_path: Path) -> Workspace:
    return Workspace(str(tmp_path))


def _execute_map(ws: Workspace, **kwargs) -> str:
    return ActivateMapTool().execute(ws, **kwargs)


def test_tool_in_registry():
    assert "activate_map" in {
        fd.name for fd in tools.get_api_tools()[0].function_declarations
    }


def test_tool_not_mutating():
    tool = ActivateMapTool()
    assert tool.mutating is False


def test_tool_schema_only_has_map_param():
    defn = ActivateMapTool().definition()
    props = defn.input_schema["properties"]
    assert set(props.keys()) == {"map"}
    assert defn.input_schema["required"] == ["map"]


def test_unknown_map(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="bogus")
    assert result.startswith("Error:")
    assert "bogus" in result


# --- Prompt rendering: each map returns its execution prompt with date substituted ---

def test_intake_prompt(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="intake")
    assert not result.startswith("Error:")
    today = datetime.date.today().isoformat()
    assert today in result
    assert "Processing Intake Inputs" in result
    # LLM is responsible for client discovery
    assert "run_command ls clients/" in result


def test_session_prompt(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="session")
    assert not result.startswith("Error:")
    today = datetime.date.today().isoformat()
    assert today in result
    assert "TheraNest Form: Progress Note" in result
    assert "run_command ls clients/" in result


def test_compliance_prompt(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="compliance")
    assert not result.startswith("Error:")
    assert "Compliance Report" in result
    assert "run_command ls clients/" in result
    assert "Missing documentation is a valid audit finding" in result


def test_tp_review_prompt(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="tp-review")
    assert not result.startswith("Error:")
    assert "Treatment Plan Review Summary" in result
    assert "run_command ls clients/" in result
    assert "You must have the latest treatment plan." in result


def test_no_current_md_in_prompts(tmp_path):
    """No prompt output should contain current.md references."""
    ws = _make_workspace(tmp_path)
    for map_name in ("intake", "session", "compliance", "tp-review"):
        result = _execute_map(ws, map=map_name)
        assert "current.md" not in result, f"{map_name} prompt contains current.md"


def test_activate_map_description_no_client_context():
    """Tool description should say 'instructions' not 'client context'."""
    tool = ActivateMapTool()
    defn = tool.definition()
    assert "client context" not in defn.description
    assert "instructions" in defn.description
