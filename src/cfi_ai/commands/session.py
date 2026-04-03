"""The /session slash command — ongoing session progress notes."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import build_session_reminders, load_client_context
from cfi_ai.commands import CommandResult, build_skill_message, register
from cfi_ai.prompts.session import (
    PROGRESS_NOTE_GUIDANCE,
    PROGRESS_NOTE_PLAN_CRITERIA,
    SESSION_FILE_PLAN_PROMPT,
    SESSION_FILE_WORKFLOW_PROMPT,
)

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register("session", description="Generate an Optum-compliant progress note for a session")
def handle_session(args: str | None, ui: UI, workspace: "Workspace") -> CommandResult:
    # Fast path: first token is a valid client directory AND there's a remainder
    if args and args.strip():
        parts = args.strip().split(maxsplit=1)
        client_id = parts[0]
        remainder = parts[1] if len(parts) > 1 else None

        client_dir = workspace.root / "clients" / client_id
        if client_dir.is_dir() and remainder:
            # Valid client + file reference — pre-load context
            client_context = load_client_context(workspace, client_id)
            reminders = build_session_reminders(workspace, client_id)
            today = datetime.date.today().isoformat()
            note_guidance = PROGRESS_NOTE_GUIDANCE.format(date=today)

            message = SESSION_FILE_WORKFLOW_PROMPT.format(
                file_reference=remainder.strip(),
                date=today,
                client_id=client_id,
                client_context=client_context,
                progress_note_guidance=note_guidance,
            )
            if reminders:
                message = reminders + message
            plan_prompt = SESSION_FILE_PLAN_PROMPT.format(
                file_reference=remainder.strip(),
                date=today,
                client_id=client_id,
                client_context=client_context,
                progress_note_guidance=note_guidance,
                progress_note_plan_criteria=PROGRESS_NOTE_PLAN_CRITERIA,
            )
            ui.print_info(
                f"Processing session for `{client_id}`: {remainder.strip()} ({today})."
            )
            return CommandResult(
                message=message, workflow_mode=True, plan_prompt=plan_prompt
            )

    # Skill path: let the LLM resolve ambiguity
    return CommandResult(
        message=build_skill_message(
            workflow="session",
            description="generate an Optum-compliant progress note for a therapy session",
            user_input=args,
            workspace=workspace,
        ),
    )
