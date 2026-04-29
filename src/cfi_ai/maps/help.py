"""The /help slash map."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cfi_ai.maps import MapResult, get_map_descriptions, register_map

if TYPE_CHECKING:
    from cfi_ai.config import Config
    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register_map("help", description="Show available maps")
def handle_help(
    args: str | None,
    ui: UI,
    workspace: Workspace,
    session_store: SessionStore,
    config: Config | None = None,
) -> MapResult:
    lines = ["## Maps\n"]
    for name, desc in sorted(get_map_descriptions().items()):
        lines.append(f"- **/{name}** — {desc}")
    lines.append("")
    lines.append("Type any message without `/` to chat normally.")
    ui.render_markdown("\n".join(lines))
    return MapResult(handled=True)
