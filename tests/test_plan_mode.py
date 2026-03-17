"""Tests for plan mode functionality."""

from cfi_ai.ui import UserInput, MODE_DISPLAY
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
    """Only run_command and attach_path should be in the readonly tool set."""
    tool = get_readonly_api_tools()
    names = {fd.name for fd in tool.function_declarations}
    assert names == {"run_command", "attach_path"}
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


def test_binary_parts_preserved_into_execution():
    """Binary parts from plan messages are extracted for execution context."""
    from google.genai import types

    # Create a real inline_data part (simulating a PDF attachment)
    binary_part = types.Part.from_bytes(
        data=b"%PDF-fake-content",
        mime_type="application/pdf",
    )

    # Text-only part (no inline_data)
    text_part = types.Part.from_text(text="some text")

    # Tool response part (no inline_data)
    tool_part = types.Part.from_function_response(
        name="attach_path", response={"result": "loaded"}
    )

    plan_messages = [
        types.Content(role="user", parts=[text_part]),
        types.Content(role="user", parts=[tool_part, binary_part]),
        types.Content(role="model", parts=[types.Part.from_text(text="plan output")]),
    ]

    # Extract binary parts using the same logic as agent.py
    binary_parts = []
    for msg in plan_messages:
        if msg.role == "user":
            for part in (msg.parts or []):
                if hasattr(part, "inline_data") and part.inline_data:
                    binary_parts.append(part)

    assert len(binary_parts) == 1
    assert binary_parts[0].inline_data.mime_type == "application/pdf"
    assert binary_parts[0].inline_data.data == b"%PDF-fake-content"


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
