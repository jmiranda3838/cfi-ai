from google.genai import types

from cfi_ai.tools.base import ToolDefinition
from cfi_ai.tools.activate_map import ActivateMapTool
from cfi_ai.tools.apply_patch import ApplyPatchTool
from cfi_ai.tools.attach_path import AttachPathTool
from cfi_ai.tools.end_turn import EndTurnTool
from cfi_ai.tools.extract_document import ExtractDocumentTool
from cfi_ai.tools.interview import InterviewTool
from cfi_ai.tools.load_payer_rules import LoadPayerRulesTool
from cfi_ai.tools.run_command import RunCommandTool, is_command_mutating
from cfi_ai.tools.write_file import WriteFileTool

MUTATING_TOOLS: set[str] = set()
INTERVIEW_TOOL_NAME = "interview"
ACTIVATE_MAP_TOOL_NAME = "activate_map"
END_TURN_TOOL_NAME = "end_turn"

_ALL_TOOLS: list[type] = [
    ActivateMapTool, ApplyPatchTool, AttachPathTool, EndTurnTool,
    ExtractDocumentTool, InterviewTool, LoadPayerRulesTool, RunCommandTool,
    WriteFileTool,
]
_REGISTRY: dict[str, type] = {}


def _build_registry() -> None:
    for cls in _ALL_TOOLS:
        instance = cls()
        _REGISTRY[instance.name] = cls
        if instance.mutating:
            MUTATING_TOOLS.add(instance.name)


_build_registry()


def get_api_tools(enable_grounding: bool = True) -> list[types.Tool]:
    """Return tool definitions formatted for the Google Gen AI API. When
    enable_grounding is True (default), append a Google Search grounding tool
    so the model can issue web searches alongside function calls."""
    declarations = [cls().definition().to_function_declaration() for cls in _REGISTRY.values()]
    result: list[types.Tool] = [types.Tool(function_declarations=declarations)]
    if enable_grounding:
        result.append(types.Tool(google_search=types.GoogleSearch()))
    return result


def execute(name: str, workspace, client=None, **kwargs) -> str | tuple[str, list]:
    """Execute a tool by name. Returns a string or (string, [Part]) tuple."""
    cls = _REGISTRY.get(name)
    if cls is None:
        return f"Error: unknown tool '{name}'"
    try:
        return cls().execute(workspace, client, **kwargs)
    except Exception as e:
        return f"Error: {e}"


def classify_mutation(name: str, args: dict) -> bool:
    """Check if a tool call is mutating, handling dynamic classification for run_command."""
    if name == "run_command":
        return is_command_mutating(args.get("command", ""))
    return name in MUTATING_TOOLS


__all__ = [
    "ToolDefinition",
    "get_api_tools",
    "execute",
    "classify_mutation",
    "MUTATING_TOOLS",
    "INTERVIEW_TOOL_NAME",
    "ACTIVATE_MAP_TOOL_NAME",
    "END_TURN_TOOL_NAME",
]
