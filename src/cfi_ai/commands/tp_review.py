"""The /tp-review slash command — treatment plan review and update."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import list_clients, load_compliance_context
from cfi_ai.commands import CommandResult, register
from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register("tp-review", description="Review and update a client's treatment plan based on progress notes")
def handle_tp_review(args: str | None, ui: UI, workspace: "Workspace") -> CommandResult:
    if not args or not args.strip():
        return CommandResult(
            error="Usage: /tp-review <client-id>\n"
            "Review and update a client's treatment plan based on progress notes."
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

    # Validate treatment plan exists
    tp_file = client_dir / "treatment-plan" / "current.md"
    if not tp_file.is_file():
        return CommandResult(
            error=f"No treatment plan found for client `{client_id}`. "
            "Run /intake first to create the initial treatment plan."
        )

    # Validate at least one progress note exists
    sessions_dir = client_dir / "sessions"
    has_notes = sessions_dir.is_dir() and any(
        sessions_dir.glob("*-progress-note.md")
    )
    if not has_notes:
        return CommandResult(
            error=f"No progress notes found for client `{client_id}`. "
            "At least one session is needed before a treatment plan review."
        )

    # Load all clinical files
    review_context = load_compliance_context(workspace, client_id)

    today = datetime.date.today().isoformat()
    message = TP_REVIEW_PROMPT.format(
        date=today,
        client_id=client_id,
        review_context=review_context,
    )

    ui.print_info(f"Running treatment plan review for `{client_id}` ({today}).")
    return CommandResult(message=message, workflow_mode=True)
