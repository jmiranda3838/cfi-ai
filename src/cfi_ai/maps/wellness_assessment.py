"""The /wellness-assessment slash map — process G22E02 and calculate GD score."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, invocation_preface, register_map
from cfi_ai.prompts.render import render_map_prompt

if TYPE_CHECKING:
    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map("wellness-assessment", description="Process a Wellness Assessment (G22E02) and calculate GD score")
def handle_wellness_assessment(
    args: str | None,
    ui: UI,
    workspace: "Workspace",
    session_store: "SessionStore",
) -> MapResult:
    today = datetime.date.today().isoformat()
    ui.print_info(f"Processing wellness assessment ({today}).")
    message = invocation_preface("wellness-assessment", args) + render_map_prompt("wellness-assessment", date=today)
    return MapResult(message=message, map_mode=True)
