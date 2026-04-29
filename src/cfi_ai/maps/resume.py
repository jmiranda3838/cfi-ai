"""The /resume slash map — restore a previous chat session."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, register_map
from cfi_ai.sessions import SessionStore

if TYPE_CHECKING:
    from cfi_ai.config import Config
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map("resume", description="Resume a previous chat session in this workspace")
def handle_resume(
    args: str | None,
    ui: UI,
    workspace: Workspace,
    session_store: SessionStore,
    config: Config | None = None,
) -> MapResult:
    sessions = SessionStore.list_for_workspace(workspace)
    if not sessions:
        ui.print_info(
            f"No saved sessions for this workspace ({workspace.root})."
        )
        return MapResult(handled=True)

    selected = ui.prompt_session_select(sessions)
    if selected is None:
        ui.print_info("Resume cancelled.")
        return MapResult(handled=True)

    try:
        loaded = SessionStore.load(selected.path)
    except Exception as e:
        return MapResult(error=f"Failed to load session: {e}")

    # Re-point the live store at the loaded session so subsequent saves
    # overwrite the same file (continuation, not a branch).
    session_store.adopt(selected.id, selected.path)

    ui.print_info(f"Resumed session {selected.id} ({len(loaded)} messages).")
    return MapResult(handled=True, loaded_messages=loaded)
