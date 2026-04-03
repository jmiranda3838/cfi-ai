"""The /wellness-assessment slash map — process G22E02 and calculate GD score."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import count_wa_files, load_client_context, load_wa_history
from cfi_ai.maps import MapResult, build_map_message, register_map
from cfi_ai.prompts.wellness_assessment import WA_FILE_MAP_PROMPT

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map("wellness-assessment", description="Process a Wellness Assessment (G22E02) and calculate GD score")
def handle_wellness_assessment(args: str | None, ui: UI, workspace: "Workspace") -> MapResult:
    # Fast path: first token is a valid client directory AND there's a remainder
    if args and args.strip():
        parts = args.strip().split(maxsplit=1)
        client_id = parts[0]
        remainder = parts[1] if len(parts) > 1 else None

        client_dir = workspace.root / "clients" / client_id
        if client_dir.is_dir() and remainder:
            # Valid client + file reference — pre-load context
            wa_count = count_wa_files(workspace, client_id)
            admin_type = "initial" if wa_count == 0 else "re-administration"
            admin_number = wa_count + 1

            client_context = load_client_context(workspace, client_id)
            wa_history = load_wa_history(workspace, client_id)
            today = datetime.date.today().isoformat()

            message = WA_FILE_MAP_PROMPT.format(
                date=today,
                client_id=client_id,
                client_context=client_context,
                wa_history=wa_history,
                admin_type=admin_type,
                admin_number=admin_number,
                file_reference=remainder.strip(),
            )
            ui.print_info(
                f"Processing wellness assessment for `{client_id}`: "
                f"{remainder.strip()} ({admin_type} #{admin_number}, {today})."
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
