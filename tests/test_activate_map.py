"""Tests for the activate_map tool."""

import datetime
from pathlib import Path

import cfi_ai.tools as tools
from cfi_ai.tools.activate_map import ActivateMapTool, get_map_plan_prompt
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


def test_tool_in_readonly_set():
    readonly = tools.get_readonly_api_tools()
    names = {fd.name for fd in readonly[0].function_declarations}
    assert "activate_map" in names


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
    assert "Progress Note Guidance" in result
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


def test_wa_prompt(tmp_path):
    ws = _make_workspace(tmp_path)
    result = _execute_map(ws, map="wellness-assessment")
    assert not result.startswith("Error:")
    assert "run_command ls clients/" in result
    assert "initial" in result.lower()


def test_no_current_md_in_prompts(tmp_path):
    """No prompt output should contain current.md references."""
    ws = _make_workspace(tmp_path)
    for map_name in ("intake", "session", "compliance", "tp-review", "wellness-assessment"):
        result = _execute_map(ws, map=map_name)
        assert "current.md" not in result, f"{map_name} prompt contains current.md"


def test_activate_map_description_no_client_context():
    """Tool description should say 'instructions' not 'client context'."""
    tool = ActivateMapTool()
    defn = tool.definition()
    assert "client context" not in defn.description
    assert "instructions" in defn.description


# --- Plan prompts: only intake and session have them ---

def test_get_map_plan_prompt_intake():
    result = get_map_plan_prompt("intake", date="2025-06-01")
    assert result is not None
    assert "Intake Map" in result
    assert "2025-06-01" in result


def test_get_map_plan_prompt_session():
    result = get_map_plan_prompt("session", date="2025-06-01")
    assert result is not None
    assert "Session Map" in result
    assert "2025-06-01" in result


def test_get_map_plan_prompt_returns_none_for_others():
    assert get_map_plan_prompt("compliance") is None
    assert get_map_plan_prompt("tp-review") is None
    assert get_map_plan_prompt("wellness-assessment") is None
