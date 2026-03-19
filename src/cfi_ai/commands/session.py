"""The /session slash command — ongoing session progress notes."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cfi_ai.clients import list_clients, load_client_context, count_wa_files, count_session_notes, get_tp_review_date
from cfi_ai.commands import CommandResult, register
from cfi_ai.prompts.session import (
    PROGRESS_NOTE_GUIDANCE,
    PROGRESS_NOTE_PLAN_CRITERIA,
    SESSION_FILE_PLAN_PROMPT,
    SESSION_FILE_WORKFLOW_PROMPT,
    SESSION_WORKFLOW_PROMPT,
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
    """Parse '/session <client-id> [file paths]'.

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
    """Resolve session input from remainder args or interactive prompt.

    Returns _TextInput (pasted text), _FileReference (file path for LLM),
    or None if cancelled.
    """
    if remainder:
        return _FileReference(raw=remainder.strip())

    # No file reference — prompt for paste or file path
    ui.print_info(
        "Paste the session transcript below, or enter a file path "
        "(audio recording, notes, etc.)."
    )
    text = ui.prompt_multiline("Session input:")
    if text is None:
        ui.print_info("Session cancelled.")
        return None
    text = text.strip()
    if not text:
        ui.print_info("Session cancelled — empty input.")
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
        ui.print_info("Session cancelled — no client ID provided.")
        return None
    return client_id.strip()


def _validate_client(client_id: str, workspace: "Workspace") -> bool:
    """Check that the client directory exists."""
    return (workspace.root / "clients" / client_id).is_dir()


@register("session", description="Generate an Optum-compliant progress note for a session")
def handle_session(args: str | None, ui: UI, workspace: "Workspace") -> CommandResult:
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

    # Load client context (profile + treatment plan)
    client_context = load_client_context(workspace, client_id)
    if not client_context:
        ui.print_info(
            f"Warning: No profile or treatment plan found for `{client_id}`. "
            "The note will be generated without treatment plan linkage."
        )

    # Check if wellness assessment re-administration is due
    wa_count = count_wa_files(workspace, client_id)
    note_count = count_session_notes(workspace, client_id)

    if wa_count == 0:
        ui.print_info(
            "Note: No Wellness Assessment on file. "
            "Consider administering G22E02 before or during this session."
        )
    elif wa_count == 1 and 3 <= note_count + 1 <= 5:
        # 2nd WA due at visits 3-5 (note_count + 1 = the session being generated now)
        ui.print_info(
            f"Wellness Assessment re-administration may be due "
            f"(visit ~{note_count + 1}; 2nd WA recommended at visits 3-5). "
            "Run /wellness-assessment after this session."
        )
    elif wa_count >= 2:
        # ~every 6 sessions after 2nd WA
        wa_dir = workspace.root / "clients" / client_id / "wellness-assessments"
        last_wa_date = sorted(wa_dir.glob("*-wellness-assessment.md"))[-1].name[:10]
        sessions_dir = workspace.root / "clients" / client_id / "sessions"
        notes_since = len([
            f for f in sessions_dir.glob("*-progress-note.md")
            if f.name[:10] > last_wa_date
        ]) if sessions_dir.is_dir() else 0
        if notes_since >= 5:
            ui.print_info(
                f"Wellness Assessment may be due for re-administration "
                f"({notes_since} sessions since last WA). "
                "Run /wellness-assessment after this session."
            )

    # Check if treatment plan review is approaching or overdue
    review_date = get_tp_review_date(workspace, client_id)
    if review_date:
        days_until = (review_date - datetime.date.today()).days
        if days_until < 0:
            ui.print_info(
                f"Treatment Plan review is past due "
                f"(was due {review_date.isoformat()}). "
                "Run /tp-review."
            )
        elif days_until <= 14:
            ui.print_info(
                f"Treatment Plan review approaching "
                f"(due {review_date.isoformat()}, {days_until} days away). "
                "Run /tp-review after this session."
            )

    # Resolve session input
    resolved = _resolve_input(remainder, ui)
    if resolved is None:
        return CommandResult(handled=True)

    today = datetime.date.today().isoformat()
    note_guidance = PROGRESS_NOTE_GUIDANCE.format(date=today)

    if isinstance(resolved, _FileReference):
        message = SESSION_FILE_WORKFLOW_PROMPT.format(
            file_reference=resolved.raw,
            date=today,
            client_id=client_id,
            client_context=client_context,
            progress_note_guidance=note_guidance,
        )
        plan_prompt = SESSION_FILE_PLAN_PROMPT.format(
            file_reference=resolved.raw,
            date=today,
            client_id=client_id,
            client_context=client_context,
            progress_note_guidance=note_guidance,
            progress_note_plan_criteria=PROGRESS_NOTE_PLAN_CRITERIA,
        )
        ui.print_info(
            f"Processing session for `{client_id}`: {resolved.raw} ({today})."
        )
        return CommandResult(
            message=message, workflow_mode=True, plan_prompt=plan_prompt
        )

    # Text flow — transcript embedded directly
    message = SESSION_WORKFLOW_PROMPT.format(
        transcript=resolved.text,
        date=today,
        client_id=client_id,
        client_context=client_context,
        progress_note_guidance=note_guidance,
    )
    ui.print_info(
        f"Processing session for `{client_id}` "
        f"({len(resolved.text)} chars, {today})."
    )
    return CommandResult(message=message, workflow_mode=True)
