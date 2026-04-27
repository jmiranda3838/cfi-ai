"""Tests for the LoadPayerRulesTool."""

import cfi_ai.tools as tools
from cfi_ai.prompts.payers import VALID_PAYERS
from cfi_ai.tools.load_payer_rules import LoadPayerRulesTool
from cfi_ai.workspace import Workspace


def test_tool_in_registry():
    """load_payer_rules is registered as a callable function declaration."""
    api_tools = tools.get_api_tools()
    names = {fd.name for fd in api_tools[0].function_declarations}
    assert "load_payer_rules" in names


def test_tool_is_non_mutating():
    """Loading payer rules is read-only — no auto-approval prompt should fire."""
    assert LoadPayerRulesTool.mutating is False


def test_tool_definition_enum_matches_valid_payers():
    defn = LoadPayerRulesTool().definition()
    enum_list = defn.input_schema["properties"]["payer"]["enum"]
    assert set(enum_list) == set(VALID_PAYERS)


def test_tool_definition_payer_is_required():
    defn = LoadPayerRulesTool().definition()
    assert defn.input_schema["required"] == ["payer"]


def test_execute_returns_optum_rules(tmp_path):
    ws = Workspace(str(tmp_path))
    result = LoadPayerRulesTool().execute(ws, payer="optum-eap")
    assert not result.startswith("Error:")
    assert "Optum" in result
    assert "G22E02" in result


def test_execute_returns_aetna_stub(tmp_path):
    ws = Workspace(str(tmp_path))
    result = LoadPayerRulesTool().execute(ws, payer="aetna")
    assert not result.startswith("Error:")
    assert "Aetna" in result


def test_execute_returns_evernorth_stub(tmp_path):
    ws = Workspace(str(tmp_path))
    result = LoadPayerRulesTool().execute(ws, payer="evernorth")
    assert not result.startswith("Error:")
    assert "Evernorth" in result


def test_execute_unknown_payer_returns_error(tmp_path):
    ws = Workspace(str(tmp_path))
    result = LoadPayerRulesTool().execute(ws, payer="bogus")
    assert result.startswith("Error:")
    assert "bogus" in result
    # Error message must enumerate every valid slug so the LLM can self-correct.
    for slug in VALID_PAYERS:
        assert slug in result


def test_execute_missing_payer_returns_error(tmp_path):
    """Missing payer arg lands in the error path (empty-string lookup misses)."""
    ws = Workspace(str(tmp_path))
    result = LoadPayerRulesTool().execute(ws)
    assert result.startswith("Error:")
