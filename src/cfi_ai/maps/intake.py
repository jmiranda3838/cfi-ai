"""The /intake slash map — clinical intake map."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, register_map
from cfi_ai.prompts.intake import INTAKE_PLAN_PROMPT, INTAKE_PROMPT

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace

_NO_MATERIALS_INPUT = (
    "No materials have been provided yet. Use the `interview` tool to ask "
    "the user what intake materials they have (session recording, intake "
    "questionnaire PDF, wellness assessment, etc.) and where the files are "
    "located. Do not proceed to client identification or document writing "
    "until you have materials to work with."
)

_FILE_INPUT_TEMPLATE = (
    "The user wants to process an intake from: `{file_reference}`\n\n"
    "Extract each file path from the input. Process each file using the "
    "appropriate tool:\n"
    "- **Audio files** (.m4a, .mp3, .wav, etc.): `attach_path(path=...)` to load audio into context\n"
    "- **PDF files** (.pdf): `extract_document(path=...)` (text extraction; use `attach_path` if incomplete)\n"
    "- **Other files**: `attach_path(path=...)`"
)


@register_map("intake", description="Process intake materials into TheraNest-ready clinical documents")
def handle_intake(args: str | None, ui: UI, workspace: Workspace) -> MapResult:
    today = datetime.date.today().isoformat()

    if args and args.strip():
        file_reference = args.strip()
        intake_input = _FILE_INPUT_TEMPLATE.format(file_reference=file_reference)
        ui.print_info(f"Processing intake materials: {file_reference} ({today}).")
    else:
        intake_input = _NO_MATERIALS_INPUT
        ui.print_info(f"Starting intake ({today}).")

    message = INTAKE_PROMPT.format(
        date=today,
        intake_input=intake_input,
    )
    plan_prompt = INTAKE_PLAN_PROMPT.format(
        date=today,
        intake_input=intake_input,
    )
    return MapResult(message=message, map_mode=True, plan_prompt=plan_prompt)
