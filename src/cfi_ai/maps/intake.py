"""The /intake slash map — clinical intake map."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import build_existing_clients_section
from cfi_ai.maps import MapResult, build_map_message, register_map
from cfi_ai.prompts.intake import (
    INTAKE_FILE_PLAN_PROMPT,
    INTAKE_FILE_MAP_PROMPT,
)

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map("intake", description="Process intake materials into TheraNest-ready clinical documents")
def handle_intake(args: str | None, ui: UI, workspace: Workspace) -> MapResult:
    # Fast path: any non-empty args → treat as file reference
    if args and args.strip():
        file_reference = args.strip()
        today = datetime.date.today().isoformat()
        existing_clients = build_existing_clients_section(workspace)

        message = INTAKE_FILE_MAP_PROMPT.format(
            file_reference=file_reference,
            date=today,
            existing_clients=existing_clients,
        )
        plan_prompt = INTAKE_FILE_PLAN_PROMPT.format(
            file_reference=file_reference,
            date=today,
            existing_clients=existing_clients,
        )
        ui.print_info(f"Processing intake materials: {file_reference} ({today}).")
        return MapResult(message=message, map_mode=True, plan_prompt=plan_prompt)

    # Map path: no args — let the LLM ask for input
    return MapResult(
        message=build_map_message(
            map_name="intake",
            description="process intake materials (recordings, transcripts, questionnaire PDFs) into TheraNest-ready clinical documents",
            user_input=args,
            workspace=workspace,
        ),
    )
