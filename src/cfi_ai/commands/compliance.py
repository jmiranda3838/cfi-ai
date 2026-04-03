"""The /compliance slash command — Optum audit compliance check."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from cfi_ai.clients import load_compliance_context
from cfi_ai.commands import CommandResult, build_skill_message, register
from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT

if TYPE_CHECKING:
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


@register("compliance", description="Run Optum compliance check on a client's records")
def handle_compliance(args: str | None, ui: UI, workspace: "Workspace") -> CommandResult:
    # Fast path: single-token arg that matches a valid client directory
    if args and args.strip():
        tokens = args.strip().split()
        if len(tokens) == 1:
            client_id = tokens[0]
            client_dir = workspace.root / "clients" / client_id
            if client_dir.is_dir():
                # Require at least one clinical file before running audit
                clinical_dirs = ("intake", "profile", "treatment-plan", "sessions", "wellness-assessments")
                has_clinical_files = any(
                    (client_dir / d).is_dir() and any((client_dir / d).glob("*.md"))
                    for d in clinical_dirs
                )
                if has_clinical_files:
                    compliance_context = load_compliance_context(workspace, client_id)
                    today = datetime.date.today().isoformat()
                    message = COMPLIANCE_PROMPT.format(
                        date=today,
                        client_id=client_id,
                        compliance_context=compliance_context,
                    )
                    ui.print_info(f"Running Optum compliance check for `{client_id}` ({today}).")
                    return CommandResult(message=message, workflow_mode=False)

    # Skill path: let the LLM resolve ambiguity
    return CommandResult(
        message=build_skill_message(
            workflow="compliance",
            description="run an Optum Treatment Record Audit compliance check",
            user_input=args,
            workspace=workspace,
        ),
    )
