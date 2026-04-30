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
                "Load a clinical map's reference content and workflow steps into the "
                "conversation. See the 'Available Clinical Maps' section of the system "
                "prompt for when to call and how it must be called."
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
