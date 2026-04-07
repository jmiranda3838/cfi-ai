"""The /session slash map — ongoing session progress notes."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, build_map_message, register_map
from cfi_ai.prompts.session import (
    PROGRESS_NOTE_GUIDANCE,
    PROGRESS_NOTE_PLAN_CRITERIA,
    SESSION_FILE_PLAN_PROMPT,
    SESSION_FILE_MAP_PROMPT,
)

if TYPE_CHECKING:
    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map("session", description="Generate an Optum-compliant progress note for a session")
def handle_session(
    args: str | None,
    ui: UI,
    workspace: "Workspace",
    session_store: "SessionStore",
) -> MapResult:
    # Fast path: first token is a valid client directory AND there's a remainder
    if args and args.strip():
        parts = args.strip().split(maxsplit=1)
        client_id = parts[0]
        remainder = parts[1] if len(parts) > 1 else None

        client_dir = workspace.root / "clients" / client_id
        if client_dir.is_dir() and remainder:
            today = datetime.date.today().isoformat()
            note_guidance = PROGRESS_NOTE_GUIDANCE.format(date=today)

            message = SESSION_FILE_MAP_PROMPT.format(
                file_reference=remainder.strip(),
                date=today,
                client_id=client_id,
                progress_note_guidance=note_guidance,
            )
            plan_prompt = SESSION_FILE_PLAN_PROMPT.format(
                file_reference=remainder.strip(),
                date=today,
                client_id=client_id,
                progress_note_guidance=note_guidance,
                progress_note_plan_criteria=PROGRESS_NOTE_PLAN_CRITERIA,
            )
            ui.print_info(
                f"Processing session for `{client_id}`: {remainder.strip()} ({today})."
            )
            return MapResult(
                message=message, map_mode=True, plan_prompt=plan_prompt
            )

    # Map path: let the LLM resolve ambiguity
    return MapResult(
        message=build_map_message(
            map_name="session",
            description="generate an Optum-compliant progress note for a therapy session",
            user_input=args,
            workspace=workspace,
        ),
    )
