"""Tool for LLM-initiated map activation."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import (
    build_existing_clients_section,
    count_wa_files,
    build_session_reminders,
    list_clients,
    load_client_context,
    load_compliance_context,
    load_wa_history,
)
from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
from cfi_ai.prompts.intake import (
    INTAKE_FILE_PLAN_PROMPT,
    INTAKE_FILE_MAP_PROMPT,
    INTAKE_MAP_PROMPT,
)
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

# Maps where map_mode should NOT be set (read-only analysis)
NON_MAP_MODE = {"compliance"}


def get_map_plan_prompt(
    map_name: str, workspace: Workspace, **kwargs: str
) -> str | None:
    """Return the plan-mode-specific prompt for a map, or None if none exists."""
    today = kwargs.get("date", datetime.date.today().isoformat())
    file_reference = kwargs.get("file_reference", "")
    client_id = kwargs.get("client_id", "")

    if map_name == "intake" and file_reference:
        existing_clients = build_existing_clients_section(workspace)
        return INTAKE_FILE_PLAN_PROMPT.format(
            file_reference=file_reference,
            date=today,
            existing_clients=existing_clients,
        )

    if map_name == "session" and file_reference and client_id:
        client_context = load_client_context(workspace, client_id)
        note_guidance = PROGRESS_NOTE_GUIDANCE.format(date=today)
        return SESSION_FILE_PLAN_PROMPT.format(
            file_reference=file_reference,
            date=today,
            client_id=client_id,
            client_context=client_context,
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
                "and client context. Call this when the user describes a clinical task "
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

        if map_name == "intake":
            return self._activate_intake(workspace, today, file_reference)
        if map_name == "session":
            return self._activate_session(workspace, today, client_id, file_reference)
        if map_name == "compliance":
            return self._activate_compliance(workspace, today, client_id)
        if map_name == "tp-review":
            return self._activate_tp_review(workspace, today, client_id)
        if map_name == "wellness-assessment":
            return self._activate_wa(workspace, today, client_id, file_reference)

        return f"Error: Unhandled map '{map_name}'"

    def _activate_intake(
        self, workspace: Workspace, today: str, file_reference: str
    ) -> str:
        existing_clients = build_existing_clients_section(workspace)

        if file_reference:
            return INTAKE_FILE_MAP_PROMPT.format(
                file_reference=file_reference,
                date=today,
                existing_clients=existing_clients,
            )

        return INTAKE_MAP_PROMPT.format(
            transcript=_CONVERSATION_INPUT_PLACEHOLDER,
            date=today,
            existing_clients=existing_clients,
        )

    def _activate_session(
        self,
        workspace: Workspace,
        today: str,
        client_id: str,
        file_reference: str,
    ) -> str:
        client_context = load_client_context(workspace, client_id)
        note_guidance = PROGRESS_NOTE_GUIDANCE.format(date=today)
        reminders = build_session_reminders(workspace, client_id)

        if file_reference:
            prompt = SESSION_FILE_MAP_PROMPT.format(
                file_reference=file_reference,
                date=today,
                client_id=client_id,
                client_context=client_context,
                progress_note_guidance=note_guidance,
            )
        else:
            prompt = SESSION_MAP_PROMPT.format(
                transcript=_CONVERSATION_INPUT_PLACEHOLDER,
                date=today,
                client_id=client_id,
                client_context=client_context,
                progress_note_guidance=note_guidance,
            )

        if reminders:
            return reminders + prompt
        return prompt

    def _activate_compliance(
        self, workspace: Workspace, today: str, client_id: str
    ) -> str:
        compliance_context = load_compliance_context(workspace, client_id)
        if not compliance_context:
            return (
                f"Error: No clinical files found for client '{client_id}'. "
                "Run the Intake Map first."
            )

        return COMPLIANCE_PROMPT.format(
            date=today,
            client_id=client_id,
            compliance_context=compliance_context,
        )

    def _activate_tp_review(
        self, workspace: Workspace, today: str, client_id: str
    ) -> str:
        client_dir = workspace.root / "clients" / client_id

        # Validate treatment plan exists
        tp_file = client_dir / "treatment-plan" / "current.md"
        if not tp_file.is_file():
            return (
                f"Error: No treatment plan found for client '{client_id}'. "
                "Run the Intake Map first to create the initial treatment plan."
            )

        # Validate at least one progress note exists
        sessions_dir = client_dir / "sessions"
        has_notes = sessions_dir.is_dir() and any(
            sessions_dir.glob("*-progress-note.md")
        )
        if not has_notes:
            return (
                f"Error: No progress notes found for client '{client_id}'. "
                "At least one session is needed before a treatment plan review."
            )

        review_context = load_compliance_context(workspace, client_id)

        return TP_REVIEW_PROMPT.format(
            date=today,
            client_id=client_id,
            review_context=review_context,
        )

    def _activate_wa(
        self,
        workspace: Workspace,
        today: str,
        client_id: str,
        file_reference: str,
    ) -> str:
        wa_count = count_wa_files(workspace, client_id)
        admin_type = "initial" if wa_count == 0 else "re-administration"
        admin_number = wa_count + 1

        client_context = load_client_context(workspace, client_id)
        wa_history = load_wa_history(workspace, client_id)

        if file_reference:
            return WA_FILE_MAP_PROMPT.format(
                date=today,
                client_id=client_id,
                client_context=client_context,
                wa_history=wa_history,
                admin_type=admin_type,
                admin_number=admin_number,
                file_reference=file_reference,
            )

        return WA_MAP_PROMPT.format(
            date=today,
            client_id=client_id,
            client_context=client_context,
            wa_history=wa_history,
            admin_type=admin_type,
            admin_number=admin_number,
            wa_input=_CONVERSATION_INPUT_PLACEHOLDER,
        )
