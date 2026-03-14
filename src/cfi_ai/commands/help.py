"""The /help slash command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cfi_ai.commands import CommandResult, register, get_command_descriptions

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register("help", description="Show available commands")
def handle_help(args: str | None, ui: UI, workspace: Workspace) -> CommandResult:
    lines = ["## Commands\n"]
    for name, desc in sorted(get_command_descriptions().items()):
        lines.append(f"- **/{name}** — {desc}")
    lines.append("")
    lines.append("Type any message without `/` to chat normally.")
    ui.render_markdown("\n".join(lines))
    return CommandResult(handled=True)
