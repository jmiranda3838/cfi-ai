"""The /tp-review slash map — treatment plan review and update."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, invocation_preface, register_map
from cfi_ai.prompts.render import render_map_prompt

if TYPE_CHECKING:
    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map(
    "tp-review",
    description="Review and update a client's treatment plan based on progress notes (run at the 90-day review checkpoint or when clinical change warrants); requires an existing treatment plan and progress notes to generate updates",
)
def handle_tp_review(
    args: str | None,
    ui: UI,
    workspace: "Workspace",
    session_store: "SessionStore",
) -> MapResult:
    today = datetime.date.today().isoformat()
    ui.print_info(f"Running treatment plan review ({today}).")
    message = invocation_preface("tp-review", args) + render_map_prompt("tp-review", date=today)
    return MapResult(message=message, map_mode=True)
