"""Slash map framework for cfi-ai."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from google.genai import types

    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace

from cfi_ai.clients import list_clients


@dataclass
class MapResult:
    """Result of a slash map execution.

    - message set -> replaces user input, sent to LLM
    - parts set -> multipart content (e.g. text + audio), sent to LLM directly
    - handled=True + no message/parts -> map printed output, skip to next prompt
    - error set -> display error, skip to next prompt
    """

    message: str | None = None
    parts: list[types.Part] | None = None
    handled: bool = False
    error: str | None = None
    map_mode: bool = False
    plan_prompt: str | None = None


MapHandler = Callable[["str | None", "UI", "Workspace"], MapResult]

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
    args = parts[1] if len(parts) > 1 else None
    return (name, args)


def dispatch_map(name: str, args: str | None, ui: UI, workspace: Workspace) -> MapResult:
    """Dispatch a parsed map. Returns MapResult."""
    handler = MAPS.get(name)
    if handler is None:
        available = ", ".join(f"/{n}" for n in sorted(MAPS))
        return MapResult(error=f"Unknown map: /{name}. Available: {available}")
    return handler(args, ui, workspace)


def get_map_descriptions() -> dict[str, str]:
    """Return mapping of map name -> description."""
    return dict(_MAP_DESCRIPTIONS)


def build_map_message(
    map_name: str,
    description: str,
    user_input: str | None,
    workspace: Workspace,
) -> str:
    """Build an LLM-facing intent message for the slash-map path.

    Instead of hard-erroring when args are missing/ambiguous, slash maps
    return this message so the LLM can resolve ambiguity via interview and
    activate_map.
    """
    parts = [f"[MAP: {map_name}]", f"The user wants to {description}."]

    if user_input and user_input.strip():
        parts.append(f'\nUser input: "{user_input.strip()}"')

    clients = list_clients(workspace)
    if clients:
        parts.append(f"\nAvailable clients: {', '.join(clients)}")
    else:
        parts.append("\nNo clients exist yet.")

    parts.append(
        "\nIf the user hasn't provided the information you need "
        "(client ID, session transcript, file path, etc.), use `interview` to "
        "ask them first. Then call `activate_map` with "
        f'`map="{map_name}"`, `source="slash"`, and the resolved parameters.'
    )

    return "\n".join(parts)


# Import map modules to trigger registration
from cfi_ai.maps import compliance as _compliance_map  # noqa: F401, E402
from cfi_ai.maps import help as _help_map  # noqa: F401, E402
from cfi_ai.maps import intake as _intake_map  # noqa: F401, E402
from cfi_ai.maps import session as _session_map  # noqa: F401, E402
from cfi_ai.maps import tp_review as _tp_review_map  # noqa: F401, E402
from cfi_ai.maps import wellness_assessment as _wa_map  # noqa: F401, E402
