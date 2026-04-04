"""Tool for LLM-initiated map activation."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import list_clients
from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
from cfi_ai.prompts.intake import INTAKE_PLAN_PROMPT, INTAKE_PROMPT
from cfi_ai.prompts.session import (
    PROGRESS_NOTE_GUIDANCE,
    PROGRESS_NOTE_PLAN_CRITERIA,
    SESSION_FILE_PLAN_PROMPT,
    SESSION_FILE_MAP_PROMPT,
    SESSION_MAP_PROMPT,
)
from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT
from cfi_ai.prompts.wellness_assessment import (
    WA_FILE_MAP_PROMPT,
    WA_MAP_PROMPT,
)
from cfi_ai.tools.base import BaseTool, ToolDefinition

if TYPE_CHECKING:
    from cfi_ai.workspace import Workspace

_CONVERSATION_INPUT_PLACEHOLDER = (
    "[The user's input is already in the conversation above. "
    "Use it directly — do not ask for it again. "
    "If the user mentioned files, use attach_path to load them.]"
)

_FILE_INPUT_TEMPLATE = (
    "The user wants to process an intake from: `{file_reference}`\n\n"
    "Extract each file path from the input. Process each file using the "
    "appropriate tool:\n"
    "- **Audio files** (.m4a, .mp3, .wav, etc.): `transcribe_audio(path=...)`\n"
    "- **PDF files** (.pdf): `extract_document(path=...)`\n"
    "- **Other files**: `attach_path(path=...)`"
)

_VALID_MAPS = {
    "intake",
    "session",
    "compliance",
    "tp-review",
    "wellness-assessment",
}

_MAPS_REQUIRING_CLIENT_ID = {
    "session",
    "compliance",
    "tp-review",
    "wellness-assessment",
}


def get_map_plan_prompt(
    map_name: str, workspace: Workspace, **kwargs: str
) -> str | None:
    """Return the plan-mode-specific prompt for a map, or None if none exists."""
    today = kwargs.get("date", datetime.date.today().isoformat())
    file_reference = kwargs.get("file_reference", "")
    client_id = kwargs.get("client_id", "")

    if map_name == "intake":
        if file_reference:
            intake_input = (
                f"The user has provided one or more files for intake processing: "
                f"`{file_reference}`"
            )
        else:
            intake_input = _CONVERSATION_INPUT_PLACEHOLDER
        return INTAKE_PLAN_PROMPT.format(
            intake_input=intake_input,
            date=today,
        )

    if map_name == "session" and file_reference and client_id:
        note_guidance = PROGRESS_NOTE_GUIDANCE.format(date=today)
        return SESSION_FILE_PLAN_PROMPT.format(
            file_reference=file_reference,
            date=today,
            client_id=client_id,
            progress_note_guidance=note_guidance,
            progress_note_plan_criteria=PROGRESS_NOTE_PLAN_CRITERIA,
        )

    return None


class ActivateMapTool(BaseTool):
    name = "activate_map"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Activate a clinical map to load specialized compliance prompts "
                "and instructions. Call this when the user describes a clinical task "
                "(intake, session note, compliance check, treatment plan review, or "
                "wellness assessment) without needing the user to say 'map'. "
                "Call this tool ALONE — do not combine with other tool calls."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "map": {
                        "type": "string",
                        "enum": list(_VALID_MAPS),
                        "description": (
                            "The map to activate: intake, session, compliance, "
                            "tp-review, or wellness-assessment."
                        ),
                    },
                    "source": {
                        "type": "string",
                        "enum": ["slash", "implicit"],
                        "description": (
                            "How this map was triggered: 'slash' for an explicit /map "
                            "invocation, 'implicit' for direct intent-based activation."
                        ),
                    },
                    "client_id": {
                        "type": "string",
                        "description": (
                            "Client identifier slug (e.g. 'jane-doe'). "
                            "Required for all maps except intake."
                        ),
                    },
                    "file_reference": {
                        "type": "string",
                        "description": (
                            "Raw file path(s) mentioned by the user, passed as-is. "
                            "Omit if the user's input is already in the conversation "
                            "(e.g. pasted text) or no files were mentioned."
                        ),
                    },
                },
                "required": ["map", "source"],
            },
        )

    def execute(self, workspace: Workspace, client=None, **kwargs) -> str:
        map_name = kwargs.get("map", "")
        client_id = kwargs.get("client_id", "")
        file_reference = kwargs.get("file_reference", "")

        if map_name not in _VALID_MAPS:
            return (
                f"Error: Unknown map '{map_name}'. "
                f"Valid maps: {', '.join(sorted(_VALID_MAPS))}"
            )

        # Check client_id requirement
        if map_name in _MAPS_REQUIRING_CLIENT_ID and not client_id:
            clients = list_clients(workspace)
            client_list = ", ".join(clients) if clients else "none found"
            return (
                f"Error: The '{map_name}' map requires a client_id. "
                f"Available clients: {client_list}. "
                "Use the interview tool to ask the user which client."
            )

        # Validate client exists (when client_id provided)
        if client_id:
            client_dir = workspace.root / "clients" / client_id
            if not client_dir.is_dir():
                clients = list_clients(workspace)
                client_list = ", ".join(clients) if clients else "none found"
                return (
                    f"Error: Client '{client_id}' not found. "
                    f"Available clients: {client_list}"
                )

        today = datetime.date.today().isoformat()

        # Format the appropriate prompt template
        if map_name == "intake":
            if file_reference:
                intake_input = _FILE_INPUT_TEMPLATE.format(
                    file_reference=file_reference
                )
            else:
                intake_input = _CONVERSATION_INPUT_PLACEHOLDER
            return INTAKE_PROMPT.format(date=today, intake_input=intake_input)

        if map_name == "session":
            note_guidance = PROGRESS_NOTE_GUIDANCE.format(date=today)
            if file_reference:
                return SESSION_FILE_MAP_PROMPT.format(
                    file_reference=file_reference,
                    date=today,
                    client_id=client_id,
                    progress_note_guidance=note_guidance,
                )
            return SESSION_MAP_PROMPT.format(
                transcript=_CONVERSATION_INPUT_PLACEHOLDER,
                date=today,
                client_id=client_id,
                progress_note_guidance=note_guidance,
            )

        if map_name == "compliance":
            return COMPLIANCE_PROMPT.format(date=today, client_id=client_id)

        if map_name == "tp-review":
            return TP_REVIEW_PROMPT.format(date=today, client_id=client_id)

        if map_name == "wellness-assessment":
            if file_reference:
                return WA_FILE_MAP_PROMPT.format(
                    date=today,
                    client_id=client_id,
                    file_reference=file_reference,
                )
            return WA_MAP_PROMPT.format(
                date=today,
                client_id=client_id,
                wa_input=_CONVERSATION_INPUT_PLACEHOLDER,
            )

        return f"Error: Unhandled map '{map_name}'"
