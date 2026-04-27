"""The /compliance slash map — Optum audit compliance check."""

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
    "compliance",
    description="Run a payer compliance check on a client's records; missing records may be surfaced as findings",
)
def handle_compliance(
    args: str | None,
    ui: UI,
    workspace: "Workspace",
    session_store: "SessionStore",
) -> MapResult:
    today = datetime.date.today().isoformat()
    ui.print_info(f"Running compliance check ({today}).")
    message = invocation_preface("compliance", args) + render_map_prompt("compliance", date=today)
    return MapResult(message=message, map_mode=True)
