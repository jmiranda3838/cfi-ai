"""Tool for LLM-initiated map activation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cfi_ai.prompts.render import VALID_MAPS, render_map_prompt
from cfi_ai.tools.base import BaseTool, ToolDefinition

if TYPE_CHECKING:
    from cfi_ai.workspace import Workspace


class ActivateMapTool(BaseTool):
    name = "activate_map"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Load a clinical map's reference content, instructions, and workflow "
                "steps into the conversation. Call this in two situations: (1) the user "
                "has clearly asked you to produce or update clinical documents (intake, "
                "session note, compliance check, tp-review, wellness assessment), OR "
                "(2) the user is asking a question or thinking through a clinical "
                "decision and you need the map's reference content to answer well. "
                "Loading a map does NOT commit you to executing its workflow — when in "
                "doubt, load it and use the content to answer the user's actual "
                "question rather than auto-executing the steps. "
                "The map prompt itself tells you how to resolve the client and any "
                "session input — you do NOT pass those in. "
                "Call this tool ALONE — do not combine with other tool calls."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "map": {
                        "type": "string",
                        "enum": list(VALID_MAPS),
                        "description": f"The map to activate: {', '.join(VALID_MAPS)}.",
                    },
                },
                "required": ["map"],
            },
        )

    def execute(self, workspace: Workspace, client=None, **kwargs) -> str:
        map_name = kwargs.get("map", "")
        if map_name not in VALID_MAPS:
            return (
                f"Error: Unknown map '{map_name}'. "
                f"Valid maps: {', '.join(VALID_MAPS)}"
            )
        return render_map_prompt(map_name)
