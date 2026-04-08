"""The /compliance slash map — Optum audit compliance check."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, build_map_message, register_map
from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT

if TYPE_CHECKING:
    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map(
    "compliance",
    description="Run Optum compliance check on a client's records; missing records may be surfaced as findings",
)
def handle_compliance(
    args: str | None,
    ui: UI,
    workspace: "Workspace",
    session_store: "SessionStore",
) -> MapResult:
    if args and args.strip():
        tokens = args.strip().split()
        if len(tokens) == 1:
            client_id = tokens[0]
            client_dir = workspace.root / "clients" / client_id
            if client_dir.is_dir():
                today = datetime.date.today().isoformat()
                message = COMPLIANCE_PROMPT.format(
                    date=today,
                    client_id=client_id,
                )
                ui.print_info(f"Running Optum compliance check for `{client_id}` ({today}).")
                return MapResult(message=message, map_mode=True)

    # Map path: let the LLM resolve ambiguity
    return MapResult(
        message=build_map_message(
            map_name="compliance",
            description="run an Optum Treatment Record Audit compliance check",
            user_input=args,
            workspace=workspace,
        ),
    )
