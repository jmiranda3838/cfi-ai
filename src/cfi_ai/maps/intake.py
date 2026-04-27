"""The /intake slash map — clinical intake map."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, invocation_preface, register_map
from cfi_ai.prompts.render import render_map_prompt

if TYPE_CHECKING:
    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map("intake", description="Process intake materials into TheraNest-ready clinical documents")
def handle_intake(
    args: str | None,
    ui: UI,
    workspace: "Workspace",
    session_store: "SessionStore",
) -> MapResult:
    today = datetime.date.today().isoformat()
    ui.print_info("/intake activated.")
    message = invocation_preface("intake", args) + render_map_prompt("intake", date=today)
    return MapResult(message=message, map_mode=True)
