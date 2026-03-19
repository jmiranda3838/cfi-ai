"""The /compliance slash command — Optum audit compliance check."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import list_clients, load_compliance_context
from cfi_ai.commands import CommandResult, register
from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register("compliance", description="Run Optum compliance check on a client's records")
def handle_compliance(args: str | None, ui: UI, workspace: "Workspace") -> CommandResult:
    if not args or not args.strip():
        return CommandResult(
            error="Usage: /compliance <client-id>\n"
            "Run an Optum Treatment Record Audit compliance check on a client's records."
        )

    client_id = args.strip().split()[0]

    # Validate client exists
    client_dir = workspace.root / "clients" / client_id
    if not client_dir.is_dir():
        available = list_clients(workspace)
        if available:
            return CommandResult(
                error=f"Client `{client_id}` not found. "
                f"Available: {', '.join(available)}"
            )
        return CommandResult(
            error=f"Client `{client_id}` not found. No clients directory exists yet."
        )

    # Load all clinical files
    compliance_context = load_compliance_context(workspace, client_id)
    if not compliance_context:
        return CommandResult(
            error=f"No clinical files found for client `{client_id}`. "
            "Nothing to check — run /intake first."
        )

    today = datetime.date.today().isoformat()
    message = COMPLIANCE_PROMPT.format(
        date=today,
        client_id=client_id,
        compliance_context=compliance_context,
    )

    ui.print_info(f"Running Optum compliance check for `{client_id}` ({today}).")
    return CommandResult(message=message, workflow_mode=False)
