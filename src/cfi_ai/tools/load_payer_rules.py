"""Tool for LLM-initiated payer-rule loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cfi_ai.prompts.payers import PAYER_RULES, VALID_PAYERS
from cfi_ai.tools.base import BaseTool, ToolDefinition

if TYPE_CHECKING:
    from cfi_ai.workspace import Workspace


class LoadPayerRulesTool(BaseTool):
    name = "load_payer_rules"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Load billing, modifier, authorization, and assessment rules "
                "for the client's payer. The active map's payer-resolution phase "
                "tells you when to call this and how to map a Payer-field value to a slug."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "payer": {
                        "type": "string",
                        "enum": list(VALID_PAYERS),
                        "description": "Payer slug. See the active map's payer-resolution phase for slug mapping.",
                    },
                },
                "required": ["payer"],
            },
        )

    def execute(self, workspace: Workspace, client=None, **kwargs) -> str:
        payer = kwargs.get("payer", "")
        rules = PAYER_RULES.get(payer)
        if rules is None:
            return (
                f"Error: Unknown payer '{payer}'. "
                f"Valid payers: {', '.join(VALID_PAYERS)}"
            )
        return rules
