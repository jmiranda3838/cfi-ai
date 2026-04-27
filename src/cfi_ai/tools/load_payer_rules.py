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
                "Load the billing, modifier, authorization, and assessment "
                "rules for a specific payer (Optum EAP, Aetna, Evernorth). "
                "Call this ONCE at the start of an intake or session workflow, "
                "after you have identified the client's payer from intake "
                "materials or the client profile's Payer field. If the payer "
                "is ambiguous or you can't tell from the materials, call "
                "`interview` first to ask the user — do NOT guess. The "
                "returned rules govern CPT-code selection, modifier flags, "
                "authorization handling, and any payer-specific assessment "
                "instruments for the rest of the workflow."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "payer": {
                        "type": "string",
                        "enum": list(VALID_PAYERS),
                        "description": (
                            "Payer slug. Mapping from common Payer-field "
                            "values: 'Optum EWS/EAP' or 'Optum EAP' → "
                            "'optum-eap'; 'Aetna' → 'aetna'; 'Evernorth' → "
                            "'evernorth'."
                        ),
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
