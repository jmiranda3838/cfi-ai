"""The /tp-review slash map — treatment plan review and update."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, build_map_message, register_map
from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map(
    "tp-review",
    description="Review and update a client's treatment plan based on progress notes; requires an existing treatment plan and progress notes to generate updates",
)
def handle_tp_review(args: str | None, ui: UI, workspace: "Workspace") -> MapResult:
    if args and args.strip():
        tokens = args.strip().split()
        if len(tokens) == 1:
            client_id = tokens[0]
            client_dir = workspace.root / "clients" / client_id
            if client_dir.is_dir():
                today = datetime.date.today().isoformat()
                message = TP_REVIEW_PROMPT.format(
                    date=today,
                    client_id=client_id,
                )
                ui.print_info(f"Running treatment plan review for `{client_id}` ({today}).")
                return MapResult(message=message, map_mode=True)

    # Map path: let the LLM resolve ambiguity
    return MapResult(
        message=build_map_message(
            map_name="tp-review",
            description="review and update a client's treatment plan based on progress notes",
            user_input=args,
            workspace=workspace,
        ),
    )
