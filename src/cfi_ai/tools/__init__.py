from google.genai import types

from cfi_ai.tools.base import ToolDefinition
from cfi_ai.tools.edit_file import EditFileTool
from cfi_ai.tools.list_files import ListFilesTool
from cfi_ai.tools.read_file import ReadFileTool
from cfi_ai.tools.search_files import SearchFilesTool
from cfi_ai.tools.write_file import WriteFileTool

MUTATING_TOOLS: set[str] = set()

_ALL_TOOLS: list[type] = [
    EditFileTool, ListFilesTool, ReadFileTool, SearchFilesTool, WriteFileTool,
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


def execute(name: str, workspace, **kwargs) -> str:
    """Execute a tool by name and return its result as a string."""
    cls = _REGISTRY.get(name)
    if cls is None:
        return f"Error: unknown tool '{name}'"
    try:
        return cls().execute(workspace, **kwargs)
    except Exception as e:
        return f"Error: {e}"


def is_mutating(name: str) -> bool:
    return name in MUTATING_TOOLS


__all__ = [
    "ToolDefinition",
    "get_api_tools",
    "execute",
    "is_mutating",
    "MUTATING_TOOLS",
]
