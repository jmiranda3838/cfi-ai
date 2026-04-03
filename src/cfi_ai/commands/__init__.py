"""Slash command framework for cfi-ai."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from google.genai import types

    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace

from cfi_ai.clients import list_clients


@dataclass
class CommandResult:
    """Result of a slash command execution.

    - message set -> replaces user input, sent to LLM
    - parts set -> multipart content (e.g. text + audio), sent to LLM directly
    - handled=True + no message/parts -> command printed output, skip to next prompt
    - error set -> display error, skip to next prompt
    """

    message: str | None = None
    parts: list[types.Part] | None = None
    handled: bool = False
    error: str | None = None
    workflow_mode: bool = False
    plan_prompt: str | None = None


CommandHandler = Callable[["str | None", "UI", "Workspace"], CommandResult]

COMMANDS: dict[str, CommandHandler] = {}

_COMMAND_DESCRIPTIONS: dict[str, str] = {}


def register(name: str, description: str = "") -> Callable[[CommandHandler], CommandHandler]:
    """Decorator to register a slash command handler."""

    def decorator(fn: CommandHandler) -> CommandHandler:
        COMMANDS[name] = fn
        if description:
            _COMMAND_DESCRIPTIONS[name] = description
        return fn

    return decorator


def parse_command(user_input: str) -> tuple[str, str | None] | None:
    """Parse slash command input. Returns (name, args) or None if not a command."""
    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return None
    parts = stripped.split(maxsplit=1)
    name = parts[0][1:]  # remove leading /
    if not name:
        return None
    args = parts[1] if len(parts) > 1 else None
    return (name, args)


def dispatch(name: str, args: str | None, ui: UI, workspace: Workspace) -> CommandResult:
    """Dispatch a parsed command. Returns CommandResult."""
    handler = COMMANDS.get(name)
    if handler is None:
        available = ", ".join(f"/{n}" for n in sorted(COMMANDS))
        return CommandResult(error=f"Unknown command: /{name}. Available: {available}")
    return handler(args, ui, workspace)


def get_command_descriptions() -> dict[str, str]:
    """Return mapping of command name -> description."""
    return dict(_COMMAND_DESCRIPTIONS)


def build_skill_message(
    workflow: str,
    description: str,
    user_input: str | None,
    workspace: Workspace,
) -> str:
    """Build an LLM-facing intent message for the skill path.

    Instead of hard-erroring when args are missing/ambiguous, slash commands
    return this message so the LLM can resolve ambiguity via interview and
    activate_workflow.
    """
    parts = [f"[SKILL: {workflow}]", f"The user wants to {description}."]

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
        "ask them first. Then call `activate_workflow` with the resolved parameters."
    )

    return "\n".join(parts)


# Import command modules to trigger registration
from cfi_ai.commands import help as _help_cmd  # noqa: F401, E402
from cfi_ai.commands import intake as _intake_cmd  # noqa: F401, E402
from cfi_ai.commands import session as _session_cmd  # noqa: F401, E402
from cfi_ai.commands import compliance as _compliance_cmd  # noqa: F401, E402
from cfi_ai.commands import tp_review as _tp_review_cmd  # noqa: F401, E402
from cfi_ai.commands import wellness_assessment as _wa_cmd  # noqa: F401, E402
