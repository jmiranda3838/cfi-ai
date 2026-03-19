"""The /wellness-assessment slash command — process G22E02 and calculate GD score."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cfi_ai.clients import list_clients, load_client_context, load_wa_history, count_wa_files
from cfi_ai.commands import CommandResult, register
from cfi_ai.prompts.wellness_assessment import (
    WA_FILE_WORKFLOW_PROMPT,
    WA_WORKFLOW_PROMPT,
)

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@dataclass
class _TextInput:
    text: str


@dataclass
class _FileReference:
    raw: str


def _parse_args(args: str | None) -> tuple[str | None, str | None]:
    """Parse '/wellness-assessment <client-id> [file paths]'.

    Returns (client_id, remainder) where remainder may be file paths or None.
    """
    if not args:
        return None, None
    parts = args.strip().split(maxsplit=1)
    client_id = parts[0]
    remainder = parts[1] if len(parts) > 1 else None
    return client_id, remainder


def _resolve_input(
    remainder: str | None, ui: UI
) -> _TextInput | _FileReference | None:
    """Resolve WA input from remainder args or interactive prompt.

    Returns _TextInput (pasted text), _FileReference (file path for LLM),
    or None if cancelled.
    """
    if remainder:
        return _FileReference(raw=remainder.strip())

    # No file reference — prompt for paste or file path
    ui.print_info(
        "Paste wellness assessment responses below, or enter a file path "
        "(PDF scan, image, etc.)."
    )
    text = ui.prompt_multiline("WA input:")
    if text is None:
        ui.print_info("Wellness assessment cancelled.")
        return None
    text = text.strip()
    if not text:
        ui.print_info("Wellness assessment cancelled — empty input.")
        return None

    # Multi-line input is always pasted text
    if "\n" in text:
        return _TextInput(text=text)

    # Single line — could be a file path or short text
    return _FileReference(raw=text)


def _prompt_for_client_id(ui: UI, workspace: "Workspace") -> str | None:
    """Interactively prompt for a client ID."""
    clients = list_clients(workspace)
    if clients:
        ui.print_info("Existing clients: " + ", ".join(f"`{c}`" for c in clients))
    ui.print_info("Enter the client ID:")
    client_id = ui.prompt("Client ID:")
    if client_id is None or not client_id.strip():
        ui.print_info("Wellness assessment cancelled — no client ID provided.")
        return None
    return client_id.strip()


def _validate_client(client_id: str, workspace: "Workspace") -> bool:
    """Check that the client directory exists."""
    return (workspace.root / "clients" / client_id).is_dir()


@register("wellness-assessment", description="Process a Wellness Assessment (G22E02) and calculate GD score")
def handle_wellness_assessment(args: str | None, ui: UI, workspace: "Workspace") -> CommandResult:
    client_id, remainder = _parse_args(args)

    # If no client ID provided, prompt for it
    if not client_id:
        client_id = _prompt_for_client_id(ui, workspace)
        if not client_id:
            return CommandResult(handled=True)

    # Validate client exists
    if not _validate_client(client_id, workspace):
        available = list_clients(workspace)
        if available:
            return CommandResult(
                error=f"Client `{client_id}` not found. "
                f"Available: {', '.join(available)}"
            )
        return CommandResult(
            error=f"Client `{client_id}` not found. No clients directory exists yet. "
            "Use /intake to process a new client first."
        )

    # Determine administration type
    wa_count = count_wa_files(workspace, client_id)
    admin_type = "initial" if wa_count == 0 else "re-administration"
    admin_number = wa_count + 1

    # Load context
    client_context = load_client_context(workspace, client_id)
    wa_history = load_wa_history(workspace, client_id)

    # Resolve input
    resolved = _resolve_input(remainder, ui)
    if resolved is None:
        return CommandResult(handled=True)

    today = datetime.date.today().isoformat()

    if isinstance(resolved, _FileReference):
        message = WA_FILE_WORKFLOW_PROMPT.format(
            date=today,
            client_id=client_id,
            client_context=client_context,
            wa_history=wa_history,
            admin_type=admin_type,
            admin_number=admin_number,
            file_reference=resolved.raw,
        )
        ui.print_info(
            f"Processing wellness assessment for `{client_id}`: "
            f"{resolved.raw} ({admin_type} #{admin_number}, {today})."
        )
        return CommandResult(message=message, workflow_mode=True)

    # Text flow — responses pasted directly
    message = WA_WORKFLOW_PROMPT.format(
        date=today,
        client_id=client_id,
        client_context=client_context,
        wa_history=wa_history,
        admin_type=admin_type,
        admin_number=admin_number,
        wa_input=resolved.text,
    )
    ui.print_info(
        f"Processing wellness assessment for `{client_id}` "
        f"({len(resolved.text)} chars, {admin_type} #{admin_number}, {today})."
    )
    return CommandResult(message=message, workflow_mode=True)
