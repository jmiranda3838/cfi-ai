"""Slash map framework for cfi-ai."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from google.genai import types

    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace

@dataclass
class MapResult:
    """Result of a slash map execution.

    - message set -> replaces user input, sent to LLM
    - parts set -> multipart content (e.g. text + audio), sent to LLM directly
    - handled=True + no message/parts -> map printed output, skip to next prompt
    - error set -> display error, skip to next prompt
    - loaded_messages set -> replace in-memory conversation with these (used by /resume)
    - clear_conversation=True -> drop in-memory history and reset cost tracker (used by /clear)
    """

    message: str | None = None
    parts: list[types.Part] | None = None
    handled: bool = False
    error: str | None = None
    map_mode: bool = False
    loaded_messages: list[types.Content] | None = None
    clear_conversation: bool = False


MapHandler = Callable[["str | None", "UI", "Workspace", "SessionStore"], MapResult]

MAPS: dict[str, MapHandler] = {}

_MAP_DESCRIPTIONS: dict[str, str] = {}


def register_map(name: str, description: str = "") -> Callable[[MapHandler], MapHandler]:
    """Decorator to register a slash map handler."""

    def decorator(fn: MapHandler) -> MapHandler:
        MAPS[name] = fn
        if description:
            _MAP_DESCRIPTIONS[name] = description
        return fn

    return decorator


def parse_map_invocation(user_input: str) -> tuple[str, str | None] | None:
    """Parse slash map input. Returns (name, args) or None if not a map."""
    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return None
    parts = stripped.split(maxsplit=1)
    name = parts[0][1:]  # remove leading /
    if not name:
        return None
    if "/" in name:
        # Looks like an absolute path (e.g. "/var/folders/..."), not a map.
        # Forward to the LLM as ordinary input so it can attach_path.
        return None
    args = parts[1] if len(parts) > 1 else None
    return (name, args)


def dispatch_map(
    name: str,
    args: str | None,
    ui: UI,
    workspace: Workspace,
    session_store: SessionStore,
) -> MapResult:
    """Dispatch a parsed map. Returns MapResult."""
    handler = MAPS.get(name)
    if handler is None:
        available = ", ".join(f"/{n}" for n in sorted(MAPS))
        return MapResult(error=f"Unknown map: /{name}. Available: {available}")
    return handler(args, ui, workspace, session_store)


def get_map_descriptions() -> dict[str, str]:
    """Return mapping of map name -> description."""
    return dict(_MAP_DESCRIPTIONS)


def invocation_preface(map_name: str, args: str | None) -> str:
    """Build the 'User invoked /<map>' preface prepended to a dispatched map message."""
    if args and args.strip():
        return f"User invoked /{map_name} with input: {args.strip()!r}\n\n"
    return f"User invoked /{map_name} with no arguments.\n\n"


# Import map modules to trigger registration
from cfi_ai.maps import bugreport as _bugreport_map  # noqa: F401, E402
from cfi_ai.maps import clear as _clear_map  # noqa: F401, E402
from cfi_ai.maps import compliance as _compliance_map  # noqa: F401, E402
from cfi_ai.maps import help as _help_map  # noqa: F401, E402
from cfi_ai.maps import intake as _intake_map  # noqa: F401, E402
from cfi_ai.maps import resume as _resume_map  # noqa: F401, E402
from cfi_ai.maps import session as _session_map  # noqa: F401, E402
from cfi_ai.maps import tp_review as _tp_review_map  # noqa: F401, E402
