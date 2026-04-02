"""Tool for LLM-initiated workflow activation (skills system)."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import (
    count_session_notes,
    count_wa_files,
    get_tp_review_date,
    list_clients,
    load_client_context,
    load_compliance_context,
    load_wa_history,
)
from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
from cfi_ai.prompts.intake import (
    INTAKE_FILE_PLAN_PROMPT,
    INTAKE_FILE_WORKFLOW_PROMPT,
    INTAKE_WORKFLOW_PROMPT,
)
from cfi_ai.prompts.session import (
    PROGRESS_NOTE_GUIDANCE,
    PROGRESS_NOTE_PLAN_CRITERIA,
    SESSION_FILE_PLAN_PROMPT,
    SESSION_FILE_WORKFLOW_PROMPT,
    SESSION_WORKFLOW_PROMPT,
)
from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT
from cfi_ai.prompts.wellness_assessment import (
    WA_FILE_WORKFLOW_PROMPT,
    WA_WORKFLOW_PROMPT,
)
from cfi_ai.tools.base import BaseTool, ToolDefinition

if TYPE_CHECKING:
    from cfi_ai.workspace import Workspace

_CONVERSATION_INPUT_PLACEHOLDER = (
    "[The user's input is already in the conversation above. "
    "Use it directly — do not ask for it again. "
    "If the user mentioned files, use attach_path to load them.]"
)

_VALID_WORKFLOWS = {
    "intake",
    "session",
    "compliance",
    "tp-review",
    "wellness-assessment",
}

_REQUIRES_CLIENT_ID = {
    "session",
    "compliance",
    "tp-review",
    "wellness-assessment",
}

# Workflows where workflow_mode should NOT be set (read-only analysis)
NON_WORKFLOW_MODE = {"compliance"}


def _build_existing_clients_section(workspace: Workspace) -> str:
    """Build a section describing existing clients for the prompt."""
    clients = list_clients(workspace)
    if not clients:
        return "## Existing Clients\nNo existing clients found. This will be a new client."

    client_list = "\n".join(f"- `{cid}`" for cid in clients)
    return (
        "## Existing Clients\n\n"
        "The following client IDs already exist:\n"
        f"{client_list}\n\n"
        "If the session subject matches an existing client, use `attach_path` to load "
        "`clients/<client-id>/profile/current.md` and "
        "`clients/<client-id>/treatment-plan/current.md` for context before writing."
    )


def _build_session_reminders(
    workspace: Workspace, client_id: str
) -> str:
    """Compute WA due date and TP review date reminders for a session workflow."""
    reminders: list[str] = []

    wa_count = count_wa_files(workspace, client_id)
    note_count = count_session_notes(workspace, client_id)

    if wa_count == 0:
        reminders.append(
            "- No Wellness Assessment on file. "
            "Consider administering G22E02 before or during this session."
        )
    elif wa_count == 1 and 3 <= note_count + 1 <= 5:
        reminders.append(
            f"- Wellness Assessment re-administration may be due "
            f"(visit ~{note_count + 1}; 2nd WA recommended at visits 3-5)."
        )
    elif wa_count >= 2:
        wa_dir = workspace.root / "clients" / client_id / "wellness-assessments"
        wa_files = sorted(wa_dir.glob("*-wellness-assessment.md"))
        if wa_files:
            last_wa_date = wa_files[-1].name[:10]
            sessions_dir = workspace.root / "clients" / client_id / "sessions"
            notes_since = len([
                f for f in sessions_dir.glob("*-progress-note.md")
                if f.name[:10] > last_wa_date
            ]) if sessions_dir.is_dir() else 0
            if notes_since >= 5:
                reminders.append(
                    f"- Wellness Assessment may be due for re-administration "
                    f"({notes_since} sessions since last WA)."
                )

    review_date = get_tp_review_date(workspace, client_id)
    if review_date:
        days_until = (review_date - datetime.date.today()).days
        if days_until < 0:
            reminders.append(
                f"- Treatment Plan review is past due "
                f"(was due {review_date.isoformat()})."
            )
        elif days_until <= 14:
            reminders.append(
                f"- Treatment Plan review approaching "
                f"(due {review_date.isoformat()}, {days_until} days away)."
            )

    if not reminders:
        return ""
    return "## Clinical Reminders\n\n" + "\n".join(reminders) + "\n\n"


def get_plan_prompt(
    workflow: str, workspace: Workspace, **kwargs: str
) -> str | None:
    """Return the plan-mode-specific prompt for a workflow, or None if none exists."""
    today = kwargs.get("date", datetime.date.today().isoformat())
    file_reference = kwargs.get("file_reference", "")
    client_id = kwargs.get("client_id", "")

    if workflow == "intake" and file_reference:
        existing_clients = _build_existing_clients_section(workspace)
        return INTAKE_FILE_PLAN_PROMPT.format(
            file_reference=file_reference,
            date=today,
            existing_clients=existing_clients,
        )

    if workflow == "session" and file_reference and client_id:
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


class ActivateWorkflowTool(BaseTool):
    name = "activate_workflow"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Activate a clinical workflow to load specialized compliance prompts "
                "and client context. Call this when the user describes a clinical task "
                "(intake, session note, compliance check, treatment plan review, or "
                "wellness assessment) without using an explicit slash command. "
                "Call this tool ALONE — do not combine with other tool calls."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "workflow": {
                        "type": "string",
                        "enum": list(_VALID_WORKFLOWS),
                        "description": (
                            "The workflow to activate: intake, session, compliance, "
                            "tp-review, or wellness-assessment."
                        ),
                    },
                    "client_id": {
                        "type": "string",
                        "description": (
                            "Client identifier slug (e.g. 'jane-doe'). "
                            "Required for all workflows except intake."
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
                "required": ["workflow"],
            },
        )

    def execute(self, workspace: Workspace, client=None, **kwargs) -> str:
        workflow = kwargs.get("workflow", "")
        client_id = kwargs.get("client_id", "")
        file_reference = kwargs.get("file_reference", "")

        if workflow not in _VALID_WORKFLOWS:
            return (
                f"Error: Unknown workflow '{workflow}'. "
                f"Valid workflows: {', '.join(sorted(_VALID_WORKFLOWS))}"
            )

        # Check client_id requirement
        if workflow in _REQUIRES_CLIENT_ID and not client_id:
            clients = list_clients(workspace)
            client_list = ", ".join(clients) if clients else "none found"
            return (
                f"Error: The '{workflow}' workflow requires a client_id. "
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

        if workflow == "intake":
            return self._activate_intake(workspace, today, file_reference)
        elif workflow == "session":
            return self._activate_session(workspace, today, client_id, file_reference)
        elif workflow == "compliance":
            return self._activate_compliance(workspace, today, client_id)
        elif workflow == "tp-review":
            return self._activate_tp_review(workspace, today, client_id)
        elif workflow == "wellness-assessment":
            return self._activate_wa(workspace, today, client_id, file_reference)

        return f"Error: Unhandled workflow '{workflow}'"

    def _activate_intake(
        self, workspace: Workspace, today: str, file_reference: str
    ) -> str:
        existing_clients = _build_existing_clients_section(workspace)

        if file_reference:
            return INTAKE_FILE_WORKFLOW_PROMPT.format(
                file_reference=file_reference,
                date=today,
                existing_clients=existing_clients,
            )

        return INTAKE_WORKFLOW_PROMPT.format(
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
        reminders = _build_session_reminders(workspace, client_id)

        if file_reference:
            prompt = SESSION_FILE_WORKFLOW_PROMPT.format(
                file_reference=file_reference,
                date=today,
                client_id=client_id,
                client_context=client_context,
                progress_note_guidance=note_guidance,
            )
        else:
            prompt = SESSION_WORKFLOW_PROMPT.format(
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
                "Run the intake workflow first."
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
                "Run the intake workflow first to create the initial treatment plan."
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
            return WA_FILE_WORKFLOW_PROMPT.format(
                date=today,
                client_id=client_id,
                client_context=client_context,
                wa_history=wa_history,
                admin_type=admin_type,
                admin_number=admin_number,
                file_reference=file_reference,
            )

        return WA_WORKFLOW_PROMPT.format(
            date=today,
            client_id=client_id,
            client_context=client_context,
            wa_history=wa_history,
            admin_type=admin_type,
            admin_number=admin_number,
            wa_input=_CONVERSATION_INPUT_PLACEHOLDER,
        )
