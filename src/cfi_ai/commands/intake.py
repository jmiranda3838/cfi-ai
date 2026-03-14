"""The /intake slash command — clinical intake workflow."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from google.genai import types

from cfi_ai.clients import list_clients, load_client_context
from cfi_ai.commands import CommandResult, register
from cfi_ai.prompts.intake import INTAKE_AUDIO_WORKFLOW_PROMPT, INTAKE_WORKFLOW_PROMPT

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace

AUDIO_EXTENSIONS: dict[str, str] = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aiff": "audio/aiff",
    ".webm": "audio/webm",
}

_LARGE_FILE_THRESHOLD = 20 * 1024 * 1024  # 20 MB


@dataclass
class _TextInput:
    text: str


@dataclass
class _AudioInput:
    data: bytes
    mime_type: str
    filename: str


def _get_audio_mime_type(path: Path) -> str | None:
    """Return the MIME type if path has an audio extension, else None."""
    return AUDIO_EXTENSIONS.get(path.suffix.lower())


def _resolve_file_path(
    raw_path: str, ui: UI, workspace: Workspace
) -> Path | None:
    """Validate and resolve a file path within the workspace.

    Returns the resolved Path, or None if invalid/missing.
    """
    try:
        path = workspace.validate_path(raw_path.strip())
    except ValueError as e:
        ui.print_error(str(e))
        return None
    if not path.is_file():
        ui.print_error(f"File not found: {raw_path.strip()}")
        return None
    return path


def _load_file(
    path: Path, ui: UI
) -> _TextInput | _AudioInput | None:
    """Load a file as text or audio based on its extension."""
    mime_type = _get_audio_mime_type(path)
    if mime_type is not None:
        data = path.read_bytes()
        if len(data) > _LARGE_FILE_THRESHOLD:
            size_mb = len(data) / (1024 * 1024)
            ui.print_info(
                f"Large audio file ({size_mb:.1f} MB). "
                "The API may reject files over 20 MB."
            )
        return _AudioInput(data=data, mime_type=mime_type, filename=path.name)
    return _TextInput(text=path.read_text())


def _resolve_input(
    args: str | None, ui: UI, workspace: Workspace
) -> _TextInput | _AudioInput | None:
    """Resolve input from args (file path) or interactive prompt.

    Returns _TextInput, _AudioInput, or None if cancelled.
    """
    if args:
        path = _resolve_file_path(args, ui, workspace)
        if path is None:
            return None
        return _load_file(path, ui)

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

    # Check if the input looks like a file path (single line)
    if "\n" not in text:
        try:
            path = workspace.validate_path(text)
            if path.is_file():
                return _load_file(path, ui)
        except ValueError:
            pass  # Not a valid path, treat as transcript text

    return _TextInput(text=text)


def _build_existing_clients_section(workspace: Workspace) -> str:
    """Build a section describing existing clients for the prompt."""
    clients = list_clients(workspace)
    if not clients:
        return "## Existing Clients\nNo existing clients found."

    lines = ["## Existing Clients\n", "The following clients already exist:\n"]
    for client_id in clients:
        context = load_client_context(workspace, client_id)
        if context:
            lines.append(f"### {client_id}\n{context}\n")
        else:
            lines.append(f"- **{client_id}** (no profile/treatment plan yet)\n")
    return "\n".join(lines)


@register("intake", description="Process a session transcript into intake documents")
def handle_intake(args: str | None, ui: UI, workspace: Workspace) -> CommandResult:
    resolved = _resolve_input(args, ui, workspace)
    if resolved is None:
        return CommandResult(handled=True)

    today = datetime.date.today().isoformat()
    existing_clients = _build_existing_clients_section(workspace)

    if isinstance(resolved, _AudioInput):
        prompt_text = INTAKE_AUDIO_WORKFLOW_PROMPT.format(
            date=today,
            existing_clients=existing_clients,
            filename=resolved.filename,
        )
        parts = [
            types.Part.from_text(text=prompt_text),
            types.Part.from_bytes(data=resolved.data, mime_type=resolved.mime_type),
        ]
        ui.print_info(
            f"Starting audio intake workflow "
            f"({len(resolved.data) / 1024:.0f} KB, {today})."
        )
        return CommandResult(parts=parts)

    # Text flow
    message = INTAKE_WORKFLOW_PROMPT.format(
        transcript=resolved.text,
        date=today,
        existing_clients=existing_clients,
    )
    ui.print_info(
        f"Starting intake workflow ({len(resolved.text)} chars of transcript, "
        f"{today})."
    )
    return CommandResult(message=message)
