from __future__ import annotations

import subprocess
import time

from google.auth import exceptions as auth_exceptions
from google.genai import types

from cfi_ai.client import Client
from cfi_ai.commands import parse_command, dispatch
from cfi_ai.config import Config
from cfi_ai.planner import ExecutionPlan, format_plan
from cfi_ai.prompts.system import build_plan_mode_system_prompt
from cfi_ai.ui import UI, UserInput
from cfi_ai.workspace import Workspace
import cfi_ai.tools as tools

MAX_TOOL_ITERATIONS = 25

_NARRATION_THRESHOLD = 800


def _is_auth_error(exc: Exception) -> bool:
    """Check if an exception is caused by expired Google Cloud credentials."""
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, auth_exceptions.RefreshError):
            return True
        if "Reauthentication" in str(current):
            return True
        current = current.__cause__ or current.__context__
    return False


def _run_reauth(ui: UI) -> bool:
    """Launch interactive gcloud reauth flow. Returns True on success."""
    ui.print_info(
        "Google Cloud credentials have expired. Launching reauthentication..."
    )
    try:
        result = subprocess.run(
            ["gcloud", "auth", "application-default", "login"],
        )
    except FileNotFoundError:
        ui.print_error(
            "gcloud CLI not found. Install it from "
            "https://cloud.google.com/sdk/docs/install and run:\n"
            "  gcloud auth application-default login"
        )
        return False
    if result.returncode == 0:
        ui.print_info("Reauthentication successful. Retrying request...")
        return True
    ui.print_error("Reauthentication failed. Please try manually:\n  gcloud auth application-default login")
    return False


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
    if name in ("write_file", "apply_patch"):
        return f"path={args.get('path', '?')}"
    if name == "run_command":
        return f"command={args.get('command', '?')}"
    return _summarize_input(args)


def _run_plan_mode(
    client: Client,
    ui: UI,
    workspace: Workspace,
    plan_system_prompt: str,
    readonly_tools: types.Tool,
    messages: list[types.Content],
) -> str | None:
    """Run the plan-mode inner loop. Returns the plan text, or None on error/cancel."""
    repetition_retries = 0
    plan_text = None

    for _iteration in range(MAX_TOOL_ITERATIONS):
        ui.status.set_mode("thinking_plan")

        try:
            stream_result = client.stream_response(
                messages=messages,
                system=plan_system_prompt,
                tools=readonly_tools,
            )
        except Exception as e:
            ui.print_error(f"API error: {e}")
            return None

        try:
            full_text = ui.stream_markdown(stream_result.text_chunks())
        except KeyboardInterrupt:
            ui.print_info("Plan cancelled.")
            return None
        except Exception as e:
            ui.print_error(f"API error: {e}")
            return None

        if stream_result.repetition_detected:
            if repetition_retries >= 1:
                ui.print_error("Model output is stuck in a loop.")
                return None
            repetition_retries += 1
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(
                        text="Your response became repetitive. Be concise and proceed.",
                    )],
                )
            )
            continue

        if not stream_result.parts:
            break

        messages.append(types.Content(role="model", parts=stream_result.parts))

        function_calls = stream_result.function_calls
        if not function_calls:
            plan_text = full_text
            break

        # Process tool calls (read-only only)
        tool_result_parts: list[types.Part] = []
        for fc in function_calls:
            fc_args = dict(fc.args)

            # Reject mutations (belt-and-suspenders)
            if tools.classify_mutation(fc.name, fc_args):
                tool_result_parts.append(
                    types.Part.from_function_response(
                        name=fc.name,
                        response={"error": "Plan mode is read-only. Continue researching or produce your plan."},
                    )
                )
                continue

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

        messages.append(types.Content(role="user", parts=tool_result_parts))
        continue

    else:
        ui.print_info(f"Reached max iterations ({MAX_TOOL_ITERATIONS}) during planning.")

    return plan_text


def run_agent_loop(client: Client, ui: UI, workspace: Workspace, system_prompt: str, config: Config) -> None:
    messages: list[types.Content] = []
    api_tools = tools.get_api_tools()
    readonly_api_tools = tools.get_readonly_api_tools()
    plan_system_prompt = build_plan_mode_system_prompt(
        str(workspace.root), workspace.summary(), workspace=workspace
    )

    from cfi_ai.commands import get_command_descriptions
    ui.set_commands(get_command_descriptions())

    while True:
        # Get user input
        user_input_result = ui.get_input()

        if user_input_result is None:
            ui.print_info("Goodbye!")
            break

        user_text = user_input_result.text
        is_plan_mode = user_input_result.plan_mode

        if not user_text.strip():
            continue

        # --- PLAN MODE FLOW ---
        if is_plan_mode:
            ui.print_separator()
            ui.print_info("Plan mode: researching and planning (read-only)...")

            # Copy existing context + new user request
            plan_messages: list[types.Content] = list(messages)
            plan_messages.append(
                types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
            )

            t0 = time.monotonic()
            plan_text = _run_plan_mode(
                client, ui, workspace, plan_system_prompt,
                readonly_api_tools, plan_messages,
            )
            elapsed = time.monotonic() - t0

            if plan_text is None:
                ui.print_elapsed(elapsed)
                continue

            ui.print_separator()
            ui.show_research_plan(plan_text)
            ui.print_elapsed(elapsed)

            approved = ui.prompt_plan_approval()
            if approved:
                ui.print_info("Executing plan with full tool access...")
                ui.print_separator()

                # Clear history, inject plan as first user message
                messages.clear()
                execution_prompt = (
                    "Execute the following implementation plan. Follow each step precisely. "
                    "Use the tools available to you (run_command, attach_path, apply_patch, "
                    "write_file) to implement all changes described.\n\n"
                    f"## Plan\n\n{plan_text}"
                )
                messages.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=execution_prompt)])
                )
                # Fall through to the normal inner loop with workflow_mode enabled
                workflow_mode = True
            else:
                # Rejected: preserve plan exchange in history for refinement
                messages.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
                )
                messages.append(
                    types.Content(role="model", parts=[types.Part.from_text(text=plan_text)])
                )
                ui.print_info("Plan rejected. You can refine your request.")
                continue
        else:
            # --- NORMAL CHAT FLOW ---
            user_parts = None
            workflow_mode = False
            parsed = parse_command(user_text)
            if parsed is not None:
                cmd_name, cmd_args = parsed
                result = dispatch(cmd_name, cmd_args, ui, workspace)
                if result.error:
                    ui.print_error(result.error)
                    continue
                if result.handled and result.message is None and result.parts is None:
                    continue
                workflow_mode = result.workflow_mode
                if result.parts is not None:
                    user_parts = result.parts
                elif result.message is not None:
                    user_text = result.message

            if user_parts is not None:
                messages.append(types.Content(role="user", parts=user_parts))
            else:
                messages.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))
            ui.print_separator()

        # Inner loop: handle tool use chains
        t0 = time.monotonic()
        approval_wait = 0.0
        repetition_retries = 0
        narration_retries = 0
        reauth_attempted = False
        for _iteration in range(MAX_TOOL_ITERATIONS):
            ui.status.set_mode("thinking")

            try:
                stream_result = client.stream_response(
                    messages=messages,
                    system=system_prompt,
                    tools=api_tools,
                )
            except Exception as e:
                if not reauth_attempted and _is_auth_error(e):
                    reauth_attempted = True
                    if _run_reauth(ui):
                        client = Client(config)
                        continue
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
            except Exception as e:
                if not reauth_attempted and _is_auth_error(e):
                    reauth_attempted = True
                    if _run_reauth(ui):
                        client = Client(config)
                        continue
                ui.print_error(f"API error: {e}")
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
                # Narration guard: in workflow mode, long text with no tool calls
                # means the model is narrating instead of acting.
                if (
                    workflow_mode
                    and len(full_text) > _NARRATION_THRESHOLD
                    and narration_retries < 1
                ):
                    narration_retries += 1
                    # Discard the narrating model turn
                    messages.pop()
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(
                                text="Do not narrate the workflow or reproduce document content. "
                                "Briefly summarize in 1-2 sentences, then proceed directly "
                                "to tool calls.",
                            )],
                        )
                    )
                    continue
                break

            # Separate read and mutating tool calls
            read_ops = []
            mutate_ops = []
            for fc in function_calls:
                if tools.classify_mutation(fc.name, dict(fc.args)):
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
