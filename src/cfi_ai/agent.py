from __future__ import annotations

import time

from google.genai import types

from cfi_ai.client import Client
from cfi_ai.commands import parse_command, dispatch
from cfi_ai.planner import ExecutionPlan, format_plan
from cfi_ai.ui import UI
from cfi_ai.workspace import Workspace
import cfi_ai.tools as tools

MAX_TOOL_ITERATIONS = 25


def _summarize_input(tool_input: dict) -> str:
    """Create a short summary of tool input for display."""
    parts: list[str] = []
    for k, v in tool_input.items():
        s = str(v)
        if len(s) > 80:
            s = s[:77] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts)


def _post_approval_summary(name: str, args: dict) -> str:
    """Return a condensed summary for post-approval display."""
    if name in ("write_file", "edit_file"):
        return f"path={args.get('path', '?')}"
    return _summarize_input(args)


def run_agent_loop(client: Client, ui: UI, workspace: Workspace, system_prompt: str) -> None:
    messages: list[types.Content] = []
    api_tools = tools.get_api_tools()

    from cfi_ai.commands import get_command_descriptions
    ui.set_commands(get_command_descriptions())

    while True:
        # Get user input
        ui.status.set_mode("chatting")
        user_input = ui.get_input()

        if user_input is None:
            ui.print_info("Goodbye!")
            break
        if not user_input.strip():
            continue

        # Check for slash commands
        user_parts = None
        parsed = parse_command(user_input)
        if parsed is not None:
            cmd_name, cmd_args = parsed
            result = dispatch(cmd_name, cmd_args, ui, workspace)
            if result.error:
                ui.print_error(result.error)
                continue
            if result.handled and result.message is None and result.parts is None:
                continue
            if result.parts is not None:
                user_parts = result.parts
            elif result.message is not None:
                user_input = result.message

        if user_parts is not None:
            messages.append(types.Content(role="user", parts=user_parts))
        else:
            messages.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))
        ui.print_separator()

        # Inner loop: handle tool use chains
        t0 = time.monotonic()
        approval_wait = 0.0
        repetition_retries = 0
        for _iteration in range(MAX_TOOL_ITERATIONS):
            ui.status.set_mode("thinking")

            try:
                stream_result = client.stream_response(
                    messages=messages,
                    system=system_prompt,
                    tools=api_tools,
                )
            except Exception as e:
                ui.print_error(f"API error: {e}")
                # Remove the last user message so they can retry
                messages.pop()
                break

            # Stream and render text
            try:
                full_text = ui.stream_markdown(stream_result.text_chunks())
            except KeyboardInterrupt:
                ui.print_info("Cancelled.")
                break

            # Handle repetition detection
            if stream_result.repetition_detected:
                if repetition_retries >= 1:
                    ui.print_error("Model output is stuck in a loop. Please try again.")
                    break
                repetition_retries += 1
                # Do not append the garbage turn — inject corrective message
                messages.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(
                            text="Your previous response became repetitive. "
                            "Do not restate the plan. Summarize in 1-2 sentences "
                            "and proceed directly to tool calls.",
                        )],
                    )
                )
                continue

            if not stream_result.parts:
                break

            # Append assistant message to history
            messages.append(types.Content(role="model", parts=stream_result.parts))

            # Check for function calls
            function_calls = stream_result.function_calls
            if not function_calls:
                break

            # Separate read and mutating tool calls
            read_ops = []
            mutate_ops = []
            for fc in function_calls:
                if tools.is_mutating(fc.name):
                    mutate_ops.append(fc)
                else:
                    read_ops.append(fc)

            tool_result_parts: list[types.Part] = []

            # Execute read ops immediately
            for fc in read_ops:
                fc_args = dict(fc.args)
                ui.show_tool_call(fc.name, _summarize_input(fc_args))
                result = tools.execute(fc.name, workspace, **fc_args)
                if isinstance(result, tuple):
                    text, inline_parts = result
                    ui.show_tool_result(fc.name, text)
                    tool_result_parts.append(
                        types.Part.from_function_response(name=fc.name, response={"result": text})
                    )
                    tool_result_parts.extend(inline_parts)
                else:
                    ui.show_tool_result(fc.name, result)
                    tool_result_parts.append(
                        types.Part.from_function_response(name=fc.name, response={"result": result})
                    )

            # Handle mutating ops with plan-and-approve
            if mutate_ops:
                ui.status.set_mode("planning")
                plan = ExecutionPlan()
                for fc in mutate_ops:
                    plan.add(fc.name, dict(fc.args), workspace=workspace)

                ui.show_plan(format_plan(plan))
                approval_start = time.monotonic()
                approved = ui.prompt_approval()
                approval_wait += time.monotonic() - approval_start

                if approved:
                    ui.status.set_mode("executing")
                    for fc in mutate_ops:
                        fc_args = dict(fc.args)
                        ui.show_tool_call(fc.name, _post_approval_summary(fc.name, fc_args))
                        result = tools.execute(fc.name, workspace, **fc_args)
                        if isinstance(result, tuple):
                            text, inline_parts = result
                            ui.show_tool_result(fc.name, text)
                            tool_result_parts.append(
                                types.Part.from_function_response(
                                    name=fc.name, response={"result": text}
                                )
                            )
                            tool_result_parts.extend(inline_parts)
                        else:
                            ui.show_tool_result(fc.name, result)
                            tool_result_parts.append(
                                types.Part.from_function_response(
                                    name=fc.name, response={"result": result}
                                )
                            )
                else:
                    for fc in mutate_ops:
                        tool_result_parts.append(
                            types.Part.from_function_response(
                                name=fc.name,
                                response={"error": "User rejected this operation."},
                            )
                        )

            # Gemini uses role="user" for function responses — the API only supports
            # "user" and "model" roles, and tool results are part of the user turn.
            messages.append(types.Content(role="user", parts=tool_result_parts))
            continue  # Continue inner loop to let model process results

        else:
            # for-loop exhausted without break — max iterations reached
            ui.print_info(f"Reached max tool iterations ({MAX_TOOL_ITERATIONS}). Stopping.")

        elapsed = time.monotonic() - t0 - approval_wait
        ui.print_elapsed(elapsed)
