"""The /clear slash map — drop in-memory history and reset the cost tracker."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, register_map

if TYPE_CHECKING:
    from cfi_ai.config import Config
    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map(
    "clear",
    description="Start a fresh conversation (drops in-memory history and resets cost tracker)",
)
def handle_clear(
    args: str | None,
    ui: UI,
    workspace: Workspace,
    session_store: SessionStore,
    config: Config | None = None,
) -> MapResult:
    ui.print_info("Conversation cleared. Starting fresh.")
    return MapResult(handled=True, clear_conversation=True)
