"""The /intake slash command — clinical intake workflow."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cfi_ai.clients import list_clients
from cfi_ai.commands import CommandResult, register
from cfi_ai.prompts.intake import (
    INTAKE_FILE_PLAN_PROMPT,
    INTAKE_FILE_WORKFLOW_PROMPT,
    INTAKE_WORKFLOW_PROMPT,
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


def _resolve_input(
    args: str | None, ui: UI, workspace: Workspace
) -> _TextInput | _FileReference | None:
    """Resolve input from args or interactive prompt.

    Returns _TextInput (pasted text), _FileReference (file path for LLM),
    or None if cancelled.
    """
    if args:
        return _FileReference(raw=args.strip())

    # No args — prompt for paste or file path
    ui.print_info(
        "Paste the session transcript below, or enter a file path "
        "(text or audio)."
    )
    text = ui.prompt_multiline("Transcript input:")
    if text is None:
        ui.print_info("Intake cancelled.")
        return None
    text = text.strip()
    if not text:
        ui.print_info("Intake cancelled — empty input.")
        return None

    # Multi-line input is always pasted text
    if "\n" in text:
        return _TextInput(text=text)

    # Single line — could be a file path or short text; let LLM figure it out
    return _FileReference(raw=text)


def _build_existing_clients_section(workspace: Workspace) -> str:
    """Build a section describing existing clients for the prompt."""
    clients = list_clients(workspace)
    if not clients:
        return "## Existing Clients\nNo existing clients found. This will be a new client."

    client_list = "\n".join(f"- `{cid}`" for cid in clients)
    return (
        "## Existing Clients\n\n"
        "The following client IDs already exist:\n"
        f"{client_list}\n\n"
        "If the session subject matches an existing client, use `attach_path` to load "
        "`clients/<client-id>/profile/current.md` and "
        "`clients/<client-id>/treatment-plan/current.md` for context before writing."
    )


@register("intake", description="Process a session transcript into intake documents")
def handle_intake(args: str | None, ui: UI, workspace: Workspace) -> CommandResult:
    resolved = _resolve_input(args, ui, workspace)
    if resolved is None:
        return CommandResult(handled=True)

    today = datetime.date.today().isoformat()
    existing_clients = _build_existing_clients_section(workspace)

    if isinstance(resolved, _FileReference):
        message = INTAKE_FILE_WORKFLOW_PROMPT.format(
            file_reference=resolved.raw,
            date=today,
            existing_clients=existing_clients,
        )
        plan_prompt = INTAKE_FILE_PLAN_PROMPT.format(
            file_reference=resolved.raw,
            date=today,
            existing_clients=existing_clients,
        )
        ui.print_info(f"Starting intake workflow for: {resolved.raw} ({today}).")
        return CommandResult(message=message, workflow_mode=True, plan_prompt=plan_prompt)

    # Text flow — transcript embedded directly
    message = INTAKE_WORKFLOW_PROMPT.format(
        transcript=resolved.text,
        date=today,
        existing_clients=existing_clients,
    )
    ui.print_info(
        f"Starting intake workflow ({len(resolved.text)} chars of transcript, "
        f"{today})."
    )
    return CommandResult(message=message, workflow_mode=True)
