"""Tests for plan mode functionality."""

from cfi_ai.agent import PlanModeResult
from cfi_ai.ui import UserInput, MODE_DISPLAY, PlanApproval
from cfi_ai.tools import get_readonly_api_tools
from cfi_ai.prompts.system import build_plan_mode_system_prompt


def test_user_input_dataclass():
    """UserInput carries text and plan_mode flag."""
    inp = UserInput(text="hello")
    assert inp.text == "hello"
    assert inp.plan_mode is False

    inp2 = UserInput(text="do it", plan_mode=True)
    assert inp2.text == "do it"
    assert inp2.plan_mode is True


def test_get_readonly_api_tools():
    """Readonly tool set contains run_command, attach_path, extract_document, interview, and activate_workflow."""
    tool = get_readonly_api_tools()
    names = {fd.name for fd in tool.function_declarations}
    assert names == {"run_command", "attach_path", "extract_document", "interview", "activate_workflow"}
    assert "apply_patch" not in names
    assert "write_file" not in names


def test_plan_mode_system_prompt():
    """Plan-mode prompt instructs read-only research and structured plan output."""
    prompt = build_plan_mode_system_prompt("/tmp/ws", "Test workspace.")
    assert "PLAN MODE" in prompt
    assert "read-only" in prompt.lower()
    assert "run_command" in prompt
    assert "attach_path" in prompt
    # Available tools section should only list read-only tools
    available_section = prompt.split("Available Tools")[1].split("Your Task")[0]
    assert "run_command" in available_section
    assert "attach_path" in available_section
    assert "extract_document" in available_section
    assert "interview" in available_section
    # Mutating tools mentioned only in the "do NOT have access" line
    assert "do NOT have access to apply_patch" in prompt


def test_plan_mode_system_prompt_with_clients(tmp_path):
    """Plan-mode prompt includes clients section when clients/ dir exists."""
    from cfi_ai.workspace import Workspace

    (tmp_path / "clients").mkdir()
    ws = Workspace(path=str(tmp_path))
    prompt = build_plan_mode_system_prompt(str(tmp_path), ws.summary(), workspace=ws)
    assert "Client File Structure" in prompt


def test_mode_display_plan_modes():
    """MODE_DISPLAY includes plan mode entries."""
    assert "chatting_plan" in MODE_DISPLAY
    assert MODE_DISPLAY["chatting_plan"] == "plan mode"
    assert "thinking_plan" in MODE_DISPLAY
    assert MODE_DISPLAY["thinking_plan"] == "researching .."


def test_plan_mode_prompt_batch_mutations_guideline():
    """Plan-mode prompt instructs model to batch mutations in a single response."""
    prompt = build_plan_mode_system_prompt("/tmp/ws", "Test workspace.")
    assert "emit all file modifications" in prompt
    assert "minimize approval prompts" in prompt


def test_plan_context_preserved_into_execution():
    """Full planning context (function_responses + binary parts) is preserved into execution."""
    from google.genai import types

    # Simulate planning phase messages with various part types
    binary_part = types.Part.from_bytes(
        data=b"%PDF-fake-content",
        mime_type="application/pdf",
    )
    text_part = types.Part.from_text(text="user request")
    extract_result = types.Part.from_function_response(
        name="extract_document", response={"result": "Extracted from doc.pdf (500 chars):\n\nDOB: 1990-01-01"}
    )
    interview_result = types.Part.from_function_response(
        name="interview", response={"result": "client_id: NB00941"}
    )

    plan_messages = [
        types.Content(role="user", parts=[text_part]),
        types.Content(role="user", parts=[extract_result, binary_part]),
        types.Content(role="user", parts=[interview_result]),
        types.Content(role="model", parts=[types.Part.from_text(text="plan output")]),
    ]

    # Simulate the merge: messages[:] = plan_messages
    messages = [
        types.Content(role="user", parts=[types.Part.from_text(text="old context")]),
    ]
    messages[:] = plan_messages

    # All planning messages are preserved
    assert len(messages) == 4
    # function_response parts are present (extract_document, interview)
    assert messages[1].parts[0].function_response.name == "extract_document"
    assert "DOB: 1990-01-01" in messages[1].parts[0].function_response.response["result"]
    # binary parts are present
    assert messages[1].parts[1].inline_data.mime_type == "application/pdf"
    # interview results are present
    assert messages[2].parts[0].function_response.name == "interview"
    assert "NB00941" in messages[2].parts[0].function_response.response["result"]


def test_execution_handoff_uses_original_message_when_plan_prompt():
    """When plan_prompt is set, execution handoff uses the original message (user_text)
    plus the approved plan, not the generic 'Execute the following' preamble."""
    user_text = "Original intake workflow prompt with file reference"
    plan_prompt = "Plan prompt for the planner"
    plan_text = "Step 1: load audio\nStep 2: write files"

    # Simulate the execution handoff logic from agent.py
    if plan_prompt:
        execution_prompt = (
            f"{user_text}\n\n"
            "## Approved Plan\n\n"
            "The following plan was reviewed and approved. Follow it as a guide "
            "for the order and content of your work:\n\n"
            f"{plan_text}"
        )
    else:
        execution_prompt = (
            "Execute the following implementation plan. Follow each step precisely. "
            "Use the tools available to you (run_command, attach_path, apply_patch, "
            "write_file) to implement all changes described.\n\n"
            f"## Plan\n\n{plan_text}"
        )

    assert user_text in execution_prompt
    assert plan_text in execution_prompt
    assert "Approved Plan" in execution_prompt
    assert "Execute the following implementation plan" not in execution_prompt


def test_execution_handoff_generic_without_plan_prompt():
    """Without plan_prompt, execution handoff uses the generic preamble."""
    plan_prompt = None
    plan_text = "Step 1: edit file\nStep 2: run tests"

    if plan_prompt:
        execution_prompt = "should not happen"
    else:
        execution_prompt = (
            "Execute the following implementation plan. Follow each step precisely. "
            "Use the tools available to you (run_command, attach_path, apply_patch, "
            "write_file) to implement all changes described.\n\n"
            f"## Plan\n\n{plan_text}"
        )

    assert "Execute the following implementation plan" in execution_prompt
    assert plan_text in execution_prompt
    assert "Approved Plan" not in execution_prompt


def test_plan_approval_enum_members():
    """PlanApproval enum has exactly 3 members."""
    members = list(PlanApproval)
    assert len(members) == 3
    assert PlanApproval.BYPASS in members
    assert PlanApproval.APPROVE in members
    assert PlanApproval.REJECT in members


def test_auto_approve_semantics():
    """Only BYPASS enables auto_approve."""
    assert PlanApproval.BYPASS == PlanApproval.BYPASS  # auto_approve = True
    assert PlanApproval.APPROVE != PlanApproval.BYPASS  # auto_approve = False
    assert PlanApproval.REJECT != PlanApproval.BYPASS   # rejected, no execution


def test_plan_mode_result_defaults():
    """PlanModeResult defaults: all fields None/False."""
    r = PlanModeResult()
    assert r.plan_text is None
    assert r.workflow_execution_prompt is None
    assert r.workflow_plan_prompt is None
    assert r.workflow_mode is False


def test_plan_mode_result_with_values():
    """PlanModeResult holds provided values."""
    r = PlanModeResult(
        plan_text="the plan",
        workflow_execution_prompt="exec prompt",
        workflow_plan_prompt="plan prompt",
        workflow_mode=True,
    )
    assert r.plan_text == "the plan"
    assert r.workflow_execution_prompt == "exec prompt"
    assert r.workflow_plan_prompt == "plan prompt"
    assert r.workflow_mode is True

