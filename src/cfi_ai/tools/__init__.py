from google.genai import types

from cfi_ai.tools.base import ToolDefinition
from cfi_ai.tools.activate_workflow import ActivateWorkflowTool
from cfi_ai.tools.apply_patch import ApplyPatchTool
from cfi_ai.tools.attach_path import AttachPathTool
from cfi_ai.tools.extract_document import ExtractDocumentTool
from cfi_ai.tools.interview import InterviewTool
from cfi_ai.tools.run_command import RunCommandTool, is_command_mutating
from cfi_ai.tools.transcribe_audio import TranscribeAudioTool
from cfi_ai.tools.write_file import WriteFileTool

MUTATING_TOOLS: set[str] = set()
INTERVIEW_TOOL_NAME = "interview"
ACTIVATE_WORKFLOW_TOOL_NAME = "activate_workflow"

_ALL_TOOLS: list[type] = [
    ActivateWorkflowTool, ApplyPatchTool, AttachPathTool, ExtractDocumentTool,
    InterviewTool, RunCommandTool, TranscribeAudioTool, WriteFileTool,
]
_REGISTRY: dict[str, type] = {}


def _build_registry() -> None:
    for cls in _ALL_TOOLS:
        instance = cls()
        _REGISTRY[instance.name] = cls
        if instance.mutating:
            MUTATING_TOOLS.add(instance.name)


_build_registry()


def get_api_tools() -> types.Tool:
    """Return tool definitions formatted for the Google Gen AI API."""
    declarations = [cls().definition().to_function_declaration() for cls in _REGISTRY.values()]
    return types.Tool(function_declarations=declarations)


_READONLY_TOOL_NAMES = {"run_command", "attach_path", "interview"}


def get_readonly_api_tools() -> types.Tool:
    """Return only read-only tool declarations (for plan mode)."""
    declarations = [
        cls().definition().to_function_declaration()
        for name, cls in _REGISTRY.items()
        if name in _READONLY_TOOL_NAMES
    ]
    return types.Tool(function_declarations=declarations)


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
    "get_readonly_api_tools",
    "execute",
    "classify_mutation",
    "MUTATING_TOOLS",
    "INTERVIEW_TOOL_NAME",
    "ACTIVATE_WORKFLOW_TOOL_NAME",
]
