"""The /intake slash command — clinical intake workflow."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import list_clients
from cfi_ai.commands import CommandResult, build_skill_message, register
from cfi_ai.prompts.intake import (
    INTAKE_FILE_PLAN_PROMPT,
    INTAKE_FILE_WORKFLOW_PROMPT,
)

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


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


@register("intake", description="Process intake materials into TheraNest-ready clinical documents")
def handle_intake(args: str | None, ui: UI, workspace: Workspace) -> CommandResult:
    # Fast path: any non-empty args → treat as file reference
    if args and args.strip():
        file_reference = args.strip()
        today = datetime.date.today().isoformat()
        existing_clients = _build_existing_clients_section(workspace)

        message = INTAKE_FILE_WORKFLOW_PROMPT.format(
            file_reference=file_reference,
            date=today,
            existing_clients=existing_clients,
        )
        plan_prompt = INTAKE_FILE_PLAN_PROMPT.format(
            file_reference=file_reference,
            date=today,
            existing_clients=existing_clients,
        )
        ui.print_info(f"Processing intake materials into TheraNest-ready documents: {file_reference} ({today}).")
        return CommandResult(message=message, workflow_mode=True, plan_prompt=plan_prompt)

    # Skill path: no args — let the LLM ask for input
    return CommandResult(
        message=build_skill_message(
            workflow="intake",
            description="process intake materials (recordings, transcripts, questionnaire PDFs) into TheraNest-ready clinical documents",
            user_input=args,
            workspace=workspace,
        ),
    )
