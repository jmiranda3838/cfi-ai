"""The /session slash map — ongoing session progress notes."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, invocation_preface, register_map
from cfi_ai.prompts.render import render_map_prompt

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
    today = datetime.date.today().isoformat()
    ui.print_info(f"Starting session progress note ({today}).")
    message = invocation_preface("session", args) + render_map_prompt("session", date=today)
    return MapResult(message=message, map_mode=True)
