"""The /wellness-assessment slash map — process G22E02 and calculate GD score."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, build_map_message, register_map
from cfi_ai.prompts.wellness_assessment import WA_FILE_MAP_PROMPT

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map("wellness-assessment", description="Process a Wellness Assessment (G22E02) and calculate GD score")
def handle_wellness_assessment(args: str | None, ui: UI, workspace: "Workspace") -> MapResult:
    if args and args.strip():
        parts = args.strip().split(maxsplit=1)
        client_id = parts[0]
        remainder = parts[1] if len(parts) > 1 else None

        client_dir = workspace.root / "clients" / client_id
        if client_dir.is_dir() and remainder:
            today = datetime.date.today().isoformat()

            message = WA_FILE_MAP_PROMPT.format(
                date=today,
                client_id=client_id,
                file_reference=remainder.strip(),
            )
            ui.print_info(
                f"Processing wellness assessment for `{client_id}`: "
                f"{remainder.strip()} ({today})."
            )
            return MapResult(message=message, map_mode=True)

    # Map path: let the LLM resolve ambiguity
    return MapResult(
        message=build_map_message(
            map_name="wellness-assessment",
            description="process a Wellness Assessment (G22E02) and calculate GD score",
            user_input=args,
            workspace=workspace,
        ),
    )
