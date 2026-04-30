"""Tool for LLM-initiated form-template loading."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.prompts.progress_note import PROGRESS_NOTE_GUIDANCE
from cfi_ai.tools.base import BaseTool, ToolDefinition

if TYPE_CHECKING:
    from cfi_ai.workspace import Workspace


VALID_TEMPLATES: tuple[str, ...] = ("progress-note",)


class LoadFormTemplateTool(BaseTool):
    name = "load_form_template"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Load the TheraNest field-by-field form spec for a clinical document. "
                "Load the spec before drafting the corresponding document. After "
                "this tool returns, use the returned spec to produce the subsequent "
                "write_file call(s) or answer field-structure questions."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "enum": list(VALID_TEMPLATES),
                        "description": (
                            "The form template to load. The active map's write phase "
                            "tells you which template to request."
                        ),
                    },
                },
                "required": ["template"],
            },
        )

    def execute(self, workspace: Workspace, client=None, **kwargs) -> str:
        template = kwargs.get("template", "")
        today = datetime.date.today().isoformat()
        if template == "progress-note":
            return PROGRESS_NOTE_GUIDANCE.format(date=today)
        return (
            f"Error: Unknown template '{template}'. "
            f"Valid templates: {', '.join(VALID_TEMPLATES)}"
        )
