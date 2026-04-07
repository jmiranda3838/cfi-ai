from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass

from google.auth import exceptions as auth_exceptions
from google.genai import types

from cfi_ai.client import CacheManager, Client
from cfi_ai.config import Config
from cfi_ai.maps import dispatch_map, parse_map_invocation
from cfi_ai.planner import ExecutionPlan, format_plan
from cfi_ai.prompts.system import build_plan_mode_system_prompt
from cfi_ai.ui import UI, UserInput, PlanApproval
from cfi_ai.workspace import Workspace
import cfi_ai.tools as tools
from cfi_ai.tools import ACTIVATE_MAP_TOOL_NAME, END_TURN_TOOL_NAME, INTERVIEW_TOOL_NAME
from cfi_ai.tools.activate_map import get_map_plan_prompt as _get_map_plan_prompt

_log = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 25


@dataclass
class PlanModeResult:
    """Result from _run_plan_mode."""
    plan_text: str | None = None
    map_execution_prompt: str | None = None
    map_plan_prompt: str | None = None
    map_mode: bool = False


_MAP_DISPLAY_NAMES = {
    "intake": "Intake",
    "session": "Session",
    "compliance": "Compliance",
    "tp-review": "Treatment Plan Review",
    "wellness-assessment": "Wellness Assessment",
}


def _display_map_name(map_name: str) -> str:
    return _MAP_DISPLAY_NAMES.get(map_name, map_name.replace("-", " ").title())


def _should_retry_empty_turn(
    function_calls: list[types.FunctionCall],
    full_text: str,
    continuation_retries: int,
) -> bool:
    """Retry only when the model produced an empty turn with no tool calls."""
    return not function_calls and not full_text.strip() and continuation_retries < 2


def _build_result_slots(
    function_calls: list[types.FunctionCall],
) -> tuple[list[tuple[int, types.FunctionCall]], list[tuple[int, types.FunctionCall]], list[list[types.Part]]]:
    """Separate function calls into indexed read/mutate lists with result slots.

    Returns (read_ops, mutate_ops, result_slots) where each op is (original_index, fc)
    and result_slots[i] collects parts for function_calls[i].
    """
    import cfi_ai.tools as _tools
    read_ops: list[tuple[int, types.FunctionCall]] = []
    mutate_ops: list[tuple[int, types.FunctionCall]] = []
    for i, fc in enumerate(function_calls):
        if _tools.classify_mutation(fc.name, dict(fc.args)):
            mutate_ops.append((i, fc))
        else:
            read_ops.append((i, fc))
    result_slots: list[list[types.Part]] = [[] for _ in function_calls]
    return read_ops, mutate_ops, result_slots


def _split_tool_results(parts: list[types.Part]) -> list[list[types.Part]]:
    """Split tool result parts so inline binary data gets its own Content message.

    All function_response parts are collected into the first group so their count
    matches the function_call count from the model turn (Gemini API requirement).
    Each binary part then goes in a separate subsequent group.
    """
    fn_responses: list[types.Part] = []
    binary_parts: list[types.Part] = []
    for p in parts:
        is_binary = hasattr(p, "inline_data") and p.inline_data
        if is_binary:
            binary_parts.append(p)
        else:
            fn_responses.append(p)

    groups: list[list[types.Part]] = []
    if fn_responses:
        groups.append(fn_responses)
    for bp in binary_parts:
        groups.append([bp])
    return groups


def _safe_tool_summary(name: str, args: dict) -> str:
    """Return a PHI-safe metadata summary of tool call args.

    Never logs raw args, basenames, path segments, or content.
    """
    if name == "attach_path":
        path = args.get("path", "")
        ext = os.path.splitext(path)[1] if path else ""
        return (
            f"attach_path ext={ext!r} absolute={os.path.isabs(path)} "
            f"path_len={len(path)}"
        )
    if name == "run_command":
        cmd = args.get("command", "")
        argv = cmd.split() if isinstance(cmd, str) else []
        return f"run_command cmd={argv[0] if argv else '?'} argc={len(argv)}"
    if name == "apply_patch":
        path = args.get("path", "")
        ext = os.path.splitext(path)[1] if path else ""
        edits = args.get("edits", [])
        return (
            f"apply_patch ext={ext!r} edits={len(edits) if isinstance(edits, list) else '?'} "
            f"path_len={len(path)}"
        )
    if name == "write_file":
        path = args.get("path", "")
        ext = os.path.splitext(path)[1] if path else ""
        content = args.get("content", "")
        return (
            f"write_file ext={ext!r} content_len={len(content)} "
            f"path_len={len(path)}"
        )
    if name == "extract_document":
        path = args.get("path", "")
        ext = os.path.splitext(path)[1] if path else ""
        return f"extract_document ext={ext!r} path_len={len(path)}"
    if name == "interview":
        questions = args.get("questions", [])
        return f"interview questions={len(questions)}"
    return f"{name} keys={sorted(args.keys())}"


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


def _handle_interview(ui: UI, fc_name: str, fc_args: dict) -> types.Part:
    """Run an interview via UI and return the function response Part."""
    questions = fc_args.get("questions", [])
    if not questions:
        return types.Part.from_function_response(
            name=fc_name,
            response={"answers": [], "note": "No questions provided."},
        )
    ui.show_tool_call(fc_name, f"{len(questions)} question(s)")
    answers = ui.run_interview(questions)
    if answers is None:
        return types.Part.from_function_response(
            name=fc_name,
            response={"error": "User cancelled the interview."},
        )
    return types.Part.from_function_response(
        name=fc_name,
        response={"answers": answers},
    )


def _run_plan_mode(
    client: Client,
    ui: UI,
    workspace: Workspace,
    plan_system_prompt: str,
    readonly_tools: types.Tool,
    messages: list[types.Content],
    allow_map_activation: bool = True,
) -> PlanModeResult:
    """Run the plan-mode inner loop. Returns a PlanModeResult."""
    _log.debug("plan_mode_enter messages=%d", len(messages))
    plan_text = None
    saw_tool_calls = False
    preamble_retries = 0

    for _iteration in range(MAX_TOOL_ITERATIONS):
        _log.debug("plan_mode iteration=%d messages=%d", _iteration, len(messages))
        ui.status.set_mode("thinking_plan")

        try:
            stream_result = client.stream_response(
                messages=messages,
                system=plan_system_prompt,
                tools=readonly_tools,
                mode="plan",
            )
        except Exception as e:
            ui.print_error(f"API error: {e}")
            return PlanModeResult()

        try:
            full_text = ui.stream_markdown(stream_result.text_chunks())
        except KeyboardInterrupt:
            _log.debug("[req:%s] stream_aborted reason=keyboard_interrupt", stream_result.request_id)
            ui.print_info("Plan cancelled.")
            return PlanModeResult()
        except Exception as e:
            _log.debug("[req:%s] stream_aborted reason=api_error", stream_result.request_id)
            ui.print_error(f"API error: {e}")
            return PlanModeResult()
        finally:
            stream_result.log_completion()

        if not stream_result.parts:
            break

        messages.append(types.Content(role="model", parts=stream_result.parts))
        _log.debug("plan_mode model_turn_appended parts=%d", len(stream_result.parts))

        function_calls = stream_result.function_calls

        # Check for explicit end_turn signal (only honored when called alone)
        non_end = [fc for fc in function_calls if fc.name != END_TURN_TOOL_NAME]
        if not non_end and any(fc.name == END_TURN_TOOL_NAME for fc in function_calls):
            messages.append(types.Content(role="user", parts=[
                types.Part.from_function_response(
                    name=END_TURN_TOOL_NAME, response={"result": "Turn complete."}
                )
            ]))
            plan_text = full_text
            break
        # If end_turn appeared with other calls, strip it and process real tools
        if non_end and len(non_end) < len(function_calls):
            function_calls = non_end

        if not function_calls:
            if full_text.strip():
                if not saw_tool_calls and preamble_retries < 1:
                    preamble_retries += 1
                    _log.debug("plan_mode preamble_nudge text_len=%d", len(full_text))
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(
                                text="Your response had no tool calls. If your response is complete and "
                                "the user has what they need, call end_turn to hand control back. "
                                "If you intended to take an action, call the relevant tools now."
                            )],
                        )
                    )
                    continue
            plan_text = full_text
            break

        saw_tool_calls = True

        # Process tool calls (read-only only)
        tool_result_parts: list[types.Part] = []
        for fc in function_calls:
            fc_args = dict(fc.args)
            _log.debug("plan_mode tool_call %s", _safe_tool_summary(fc.name, fc_args))

            # Interview: handled by UI, not tools.execute()
            if fc.name == INTERVIEW_TOOL_NAME:
                tool_result_parts.append(_handle_interview(ui, fc.name, fc_args))
                continue

            # activate_map: capture and break out of plan mode
            if fc.name == ACTIVATE_MAP_TOOL_NAME and allow_map_activation:
                _log.debug("plan_mode activate_map %s", _safe_tool_summary(fc.name, fc_args))
                ui.show_tool_call(fc.name, _summarize_input(fc_args))
                result = tools.execute(fc.name, workspace, client, **fc_args)
                result_text = result if isinstance(result, str) else result[0]
                ui.show_tool_result(
                    fc.name,
                    result_text[:200] + "..." if len(result_text) > 200 else result_text,
                )

                if result_text.startswith("Error:"):
                    # Feed error back so model can use interview to get missing info
                    tool_result_parts.append(
                        types.Part.from_function_response(
                            name=fc.name, response={"result": result_text},
                        )
                    )
                    continue

                # Success: look up the plan prompt variant
                map_name = fc_args.pop("map", "")
                source = fc_args.get("source", "implicit")
                map_plan_prompt = _get_map_plan_prompt(map_name, workspace, **fc_args)
                map_mode = True
                if source == "implicit":
                    ui.print_info(f"Starting the {_display_map_name(map_name)} Map.")

                # Cancel co-occurring tool calls
                cancel_parts: list[types.Part] = [
                    types.Part.from_function_response(
                        name=fc.name,
                        response={"result": "Map activated. Switching to map planning mode."},
                    )
                ]
                for other_fc in function_calls:
                    if other_fc.name != ACTIVATE_MAP_TOOL_NAME:
                        cancel_parts.append(types.Part.from_function_response(
                            name=other_fc.name,
                            response={"error": "Discarded — activate_map must run alone."},
                        ))
                for group in _split_tool_results(cancel_parts):
                    messages.append(types.Content(role="user", parts=group))

                _log.debug(
                    "plan_mode activate_map returning map=%s plan_prompt=%s map_mode=%s",
                    map_name, map_plan_prompt is not None, map_mode,
                )
                return PlanModeResult(
                    map_execution_prompt=result_text,
                    map_plan_prompt=map_plan_prompt,
                    map_mode=map_mode,
                )

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
            result = tools.execute(fc.name, workspace, client, **fc_args)
            if isinstance(result, tuple):
                text, inline_parts = result
                ui.show_tool_result(fc.name, text)
                tool_result_parts.append(
                    types.Part.from_function_response(name=fc.name, response={"result": text})
                )
                tool_result_parts.extend(inline_parts)
                _log.debug(
                    "plan_mode tool_result %s type=tuple inline_parts=%d text_len=%d",
                    fc.name, len(inline_parts), len(text),
                )
            else:
                ui.show_tool_result(fc.name, result)
                tool_result_parts.append(
                    types.Part.from_function_response(name=fc.name, response={"result": result})
                )
                _log.debug(
                    "plan_mode tool_result %s type=text text_len=%d",
                    fc.name, len(result),
                )

        for group in _split_tool_results(tool_result_parts):
            messages.append(types.Content(role="user", parts=group))
        _log.debug(
            "plan_mode tool_results_appended parts=%d functions=%s",
            len(tool_result_parts),
            [fc.name for fc in function_calls],
        )
        continue

    else:
        ui.print_info(f"Reached max iterations ({MAX_TOOL_ITERATIONS}) during planning.")

    return PlanModeResult(plan_text=plan_text)


def _rebuild_client_after_reauth(
    config: Config,
    cache_manager: CacheManager | None,
    system_prompt: str,
    api_tools: types.Tool,
    plan_system_prompt: str,
    readonly_api_tools: types.Tool,
) -> Client:
    """Create a fresh Client after reauthentication and restore caches."""
    client = Client(config)
    if cache_manager is not None:
        cache_manager.reset(client.genai_client)
        _create_session_caches(
            cache_manager, system_prompt, api_tools,
            plan_system_prompt, readonly_api_tools,
        )
        client.set_cache_manager(cache_manager)
    return client


def _create_session_caches(
    cache_manager: CacheManager,
    system_prompt: str,
    api_tools: types.Tool,
    plan_system_prompt: str,
    readonly_api_tools: types.Tool,
) -> None:
    """Create context caches for normal and plan modes. Logs but does not raise on failure."""
    for key, system, tool_set in [
        ("normal", system_prompt, api_tools),
        ("plan", plan_system_prompt, readonly_api_tools),
    ]:
        try:
            cache_manager.create_cache(key, system, tool_set)
        except Exception as e:
            _log.warning("cache_create_failed key=%s error=%s", key, e)


def run_agent_loop(client: Client, ui: UI, workspace: Workspace, system_prompt: str, config: Config) -> None:
    messages: list[types.Content] = []
    api_tools = tools.get_api_tools()
    readonly_api_tools = tools.get_readonly_api_tools()
    plan_system_prompt = build_plan_mode_system_prompt(
        str(workspace.root), workspace.summary(), workspace=workspace
    )

    # Set up context caching
    cache_manager: CacheManager | None = None
    if config.context_cache:
        cache_manager = CacheManager(client.genai_client, config.model)
        _create_session_caches(
            cache_manager, system_prompt, api_tools,
            plan_system_prompt, readonly_api_tools,
        )
        client.set_cache_manager(cache_manager)

    from cfi_ai.maps import get_map_descriptions
    ui.set_maps(get_map_descriptions())

    try:
        _run_main_loop(
            client, ui, workspace, system_prompt, config,
            messages, api_tools, readonly_api_tools, plan_system_prompt,
            cache_manager,
        )
    finally:
        if cache_manager is not None:
            cache_manager.delete_all()


def _run_main_loop(
    client: Client,
    ui: UI,
    workspace: Workspace,
    system_prompt: str,
    config: Config,
    messages: list[types.Content],
    api_tools: types.Tool,
    readonly_api_tools: types.Tool,
    plan_system_prompt: str,
    cache_manager: CacheManager | None,
) -> None:
    """Inner main loop, extracted so run_agent_loop can wrap with try/finally for cache cleanup."""
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

        # --- SLASH MAP PARSING (before plan/normal mode branch) ---
        user_parts = None
        map_mode = False
        auto_approve = False
        plan_prompt = None
        parsed = parse_map_invocation(user_text)
        if parsed is not None:
            map_name, map_args = parsed
            result = dispatch_map(map_name, map_args, ui, workspace)
            if result.error:
                ui.print_error(result.error)
                continue
            if result.handled and result.message is None and result.parts is None:
                continue
            map_mode = result.map_mode
            plan_prompt = result.plan_prompt
            if map_mode:
                _log.debug("map_set map_mode=True")
            if result.parts is not None:
                user_parts = result.parts
            elif result.message is not None:
                user_text = result.message

        # --- PLAN MODE FLOW ---
        if is_plan_mode and (not map_mode or plan_prompt):
            ui.print_separator()
            ui.print_info("Plan mode: researching and planning (read-only)...")

            plan_user_text = plan_prompt if plan_prompt else user_text
            messages.append(
                types.Content(role="user", parts=[types.Part.from_text(text=plan_user_text)])
            )
            _log.debug("plan_mode_entry messages=%d", len(messages))

            t0 = time.monotonic()
            plan_result = _run_plan_mode(
                client, ui, workspace, plan_system_prompt,
                readonly_api_tools, messages,
            )
            elapsed = time.monotonic() - t0

            # --- Case A: activate_map was called during plan mode ---
            if plan_result.map_execution_prompt is not None:
                if plan_result.map_plan_prompt is not None:
                    # Dedicated plan prompt exists: re-enter plan mode with it
                    ui.print_info("Map activated. Planning map execution...")
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=plan_result.map_plan_prompt)],
                        )
                    )
                    t0_wf = time.monotonic()
                    wf_plan_result = _run_plan_mode(
                        client, ui, workspace, plan_system_prompt,
                        readonly_api_tools, messages,
                        allow_map_activation=False,
                    )
                    elapsed += time.monotonic() - t0_wf

                    plan_text = wf_plan_result.plan_text
                    if plan_text is None:
                        ui.print_elapsed(elapsed)
                        continue

                    ui.print_separator()
                    ui.show_research_plan(plan_text)
                    ui.print_elapsed(elapsed)

                    approval = ui.prompt_plan_approval()
                    if approval != PlanApproval.REJECT:
                        ui.set_plan_mode(False)
                        auto_approve = approval == PlanApproval.BYPASS
                        mode_desc = "auto-approve" if auto_approve else "reviewing each edit"
                        ui.print_info(f"Executing plan ({mode_desc})...")
                        ui.print_separator()

                        execution_prompt = (
                            f"{plan_result.map_execution_prompt}\n\n"
                            "## Approved Plan\n\n"
                            "The following plan was reviewed and approved. Follow it as a guide "
                            "for the order and content of your work:\n\n"
                            f"{plan_text}"
                        )
                        messages.append(
                            types.Content(role="user", parts=[types.Part.from_text(text=execution_prompt)])
                        )
                        map_mode = True
                        _log.debug("map_plan_execution_inject map_mode=True auto_approve=%s", auto_approve)
                    else:
                        ui.print_info("Plan rejected. You can refine your request.")
                        continue
                else:
                    # No dedicated plan prompt: execute directly with the map prompt
                    ui.print_info("Map activated. Executing...")
                    ui.print_elapsed(elapsed)
                    ui.print_separator()
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=plan_result.map_execution_prompt)],
                        )
                    )
                    map_mode = plan_result.map_mode
                    _log.debug("map_direct_execution map_mode=%s", map_mode)

            # --- Case B: Normal plan mode (no map activation) ---
            else:
                plan_text = plan_result.plan_text
                if plan_text is None:
                    ui.print_elapsed(elapsed)
                    continue

                ui.print_separator()
                ui.show_research_plan(plan_text)
                ui.print_elapsed(elapsed)

                approval = ui.prompt_plan_approval()
                if approval != PlanApproval.REJECT:
                    ui.set_plan_mode(False)
                    auto_approve = approval == PlanApproval.BYPASS

                    mode_desc = "auto-approve" if auto_approve else "reviewing each edit"
                    ui.print_info(f"Executing plan ({mode_desc})...")
                    ui.print_separator()

                    _log.debug(
                        "plan_approved messages=%d auto_approve=%s",
                        len(messages), auto_approve,
                    )

                    if plan_prompt:
                        # Slash map: use the original execution prompt + plan as guidance
                        execution_prompt = (
                            f"{user_text}\n\n"
                            "## Approved Plan\n\n"
                            "The following plan was reviewed and approved. Follow it as a guide "
                            "for the order and content of your work:\n\n"
                            f"{plan_text}"
                        )
                    else:
                        # Standard code task: plan-only execution
                        execution_prompt = (
                            "Execute the following implementation plan. Follow each step precisely. "
                            "Use the tools available to you (run_command, attach_path, apply_patch, "
                            "write_file) to implement all changes described.\n\n"
                            f"## Plan\n\n{plan_text}"
                        )

                    messages.append(
                        types.Content(role="user", parts=[types.Part.from_text(text=execution_prompt)])
                    )
                    # Fall through to the normal inner loop with map_mode enabled
                    map_mode = True
                    _log.debug("plan_execution_inject map_mode=True auto_approve=%s", auto_approve)
                else:
                    ui.print_info("Plan rejected. You can refine your request.")
                    continue
        else:
            # --- NORMAL CHAT FLOW ---
            _log.debug("normal_chat_flow")
            if user_parts is not None:
                messages.append(types.Content(role="user", parts=user_parts))
            else:
                messages.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))
            ui.print_separator()

        # Inner loop: handle tool use chains
        t0 = time.monotonic()
        approval_wait = 0.0
        continuation_retries = 0
        saw_tool_calls = False
        preamble_retries = 0
        reauth_attempted = False
        _log.debug("inner_loop_start map_mode=%s messages=%d", map_mode, len(messages))
        for _iteration in range(MAX_TOOL_ITERATIONS):
            _log.debug("inner_loop iteration=%d messages=%d", _iteration, len(messages))
            ui.status.set_mode("thinking")

            try:
                stream_result = client.stream_response(
                    messages=messages,
                    system=system_prompt,
                    tools=api_tools,
                    mode="map" if map_mode else "normal",
                )
            except Exception as e:
                if not reauth_attempted and _is_auth_error(e):
                    reauth_attempted = True
                    if _run_reauth(ui):
                        client = _rebuild_client_after_reauth(
                            config, cache_manager, system_prompt, api_tools,
                            plan_system_prompt, readonly_api_tools,
                        )
                        continue
                ui.print_error(f"API error: {e}")
                # Remove the last user message so they can retry
                messages.pop()
                break

            # Stream and render text
            try:
                full_text = ui.stream_markdown(stream_result.text_chunks())
            except KeyboardInterrupt:
                _log.debug("[req:%s] stream_aborted reason=keyboard_interrupt", stream_result.request_id)
                ui.print_info("Cancelled.")
                break
            except Exception as e:
                _log.debug("[req:%s] stream_aborted reason=api_error", stream_result.request_id)
                if not reauth_attempted and _is_auth_error(e):
                    reauth_attempted = True
                    if _run_reauth(ui):
                        client = _rebuild_client_after_reauth(
                            config, cache_manager, system_prompt, api_tools,
                            plan_system_prompt, readonly_api_tools,
                        )
                        continue
                ui.print_error(f"API error: {e}")
                break
            finally:
                stream_result.log_completion()

            has_parts = bool(stream_result.parts)
            if has_parts:
                messages.append(types.Content(role="model", parts=stream_result.parts))
                _log.debug("inner_loop model_turn_appended parts=%d", len(stream_result.parts))

            function_calls = stream_result.function_calls if has_parts else []

            # Check for explicit end_turn signal (only honored when called alone)
            non_end = [fc for fc in function_calls if fc.name != END_TURN_TOOL_NAME]
            if not non_end and any(fc.name == END_TURN_TOOL_NAME for fc in function_calls):
                messages.append(types.Content(role="user", parts=[
                    types.Part.from_function_response(
                        name=END_TURN_TOOL_NAME, response={"result": "Turn complete."}
                    )
                ]))
                _log.debug("inner_loop end_turn_signal")
                break
            # If end_turn appeared with other calls, strip it and process real tools
            if non_end and len(non_end) < len(function_calls):
                function_calls = non_end

            if not function_calls:
                if full_text.strip():
                    # No tool calls ever seen — model may be narrating before acting.
                    # Give one nudge. If tools already ran, this is a summary — break.
                    if not saw_tool_calls and preamble_retries < 1:
                        preamble_retries += 1
                        _log.debug("inner_loop preamble_nudge text_len=%d", len(full_text))
                        messages.append(
                            types.Content(
                                role="user",
                                parts=[types.Part.from_text(
                                    text="Your response had no tool calls. If your response is complete and "
                                    "the user has what they need, call end_turn to hand control back. "
                                    "If you intended to take an action, call the relevant tools now."
                                )],
                            )
                        )
                        continue
                    break
                # Empty turn: nudge the model to continue and try again.
                if _should_retry_empty_turn(function_calls, full_text, continuation_retries):
                    continuation_retries += 1
                    _log.debug("inner_loop continuation retries=%d text_len=%d", continuation_retries, len(full_text))
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(
                                text="Your last response was empty. Continue the task. "
                                "If you need to use tools, call them now. Otherwise provide your final response.",
                            )],
                        )
                    )
                    continue
                break

            saw_tool_calls = True

            # activate_map is a turn-boundary tool: process it alone,
            # discard other tool calls, and restart the inner loop so the
            # LLM sees the map prompt before making further calls.
            activate_fc = None
            for fc in function_calls:
                if fc.name == ACTIVATE_MAP_TOOL_NAME:
                    activate_fc = fc
                    break

            if activate_fc is not None:
                fc_args = dict(activate_fc.args)
                _log.debug("activate_map call %s", _safe_tool_summary(activate_fc.name, fc_args))
                ui.show_tool_call(activate_fc.name, _summarize_input(fc_args))
                result = tools.execute(activate_fc.name, workspace, client, **fc_args)
                result_text = result if isinstance(result, str) else result[0]
                ui.show_tool_result(activate_fc.name, result_text[:200] + "..." if len(result_text) > 200 else result_text)

                if not result_text.startswith("Error:"):
                    map_name = fc_args.get("map", "")
                    map_mode = True
                    if fc_args.get("source") == "implicit":
                        ui.print_info(f"Starting the {_display_map_name(map_name)} Map.")
                    _log.debug("activate_map %s map_mode=%s", map_name, map_mode)

                parts = [types.Part.from_function_response(
                    name=activate_fc.name, response={"result": result_text}
                )]
                # Send cancellation responses for any co-occurring tool calls
                # (Gemini requires responses for ALL function_calls in a model turn)
                for fc in function_calls:
                    if fc.name != ACTIVATE_MAP_TOOL_NAME:
                        parts.append(types.Part.from_function_response(
                            name=fc.name,
                            response={"error": "Discarded — activate_map must run alone."},
                        ))
                messages.append(types.Content(role="user", parts=parts))
                continue  # Restart inner loop — LLM sees map prompt next

            # Separate read and mutating tool calls, tracking original order
            read_ops, mutate_ops, result_slots = _build_result_slots(function_calls)

            # Execute read ops immediately
            for i, fc in read_ops:
                fc_args = dict(fc.args)
                _log.debug("inner_loop tool_call %s", _safe_tool_summary(fc.name, fc_args))

                # Interview: handled by UI, not tools.execute()
                if fc.name == INTERVIEW_TOOL_NAME:
                    result_slots[i].append(_handle_interview(ui, fc.name, fc_args))
                    continue

                ui.show_tool_call(fc.name, _summarize_input(fc_args))
                result = tools.execute(fc.name, workspace, client, **fc_args)
                if isinstance(result, tuple):
                    text, inline_parts = result
                    ui.show_tool_result(fc.name, text)
                    result_slots[i].append(
                        types.Part.from_function_response(name=fc.name, response={"result": text})
                    )
                    result_slots[i].extend(inline_parts)
                    _log.debug(
                        "inner_loop tool_result %s type=tuple inline_parts=%d text_len=%d",
                        fc.name, len(inline_parts), len(text),
                    )
                else:
                    ui.show_tool_result(fc.name, result)
                    result_slots[i].append(
                        types.Part.from_function_response(name=fc.name, response={"result": result})
                    )
                    _log.debug(
                        "inner_loop tool_result %s type=text text_len=%d",
                        fc.name, len(result),
                    )

            # Handle mutating ops with plan-and-approve
            if mutate_ops:
                for _i, fc in mutate_ops:
                    _log.debug("inner_loop mutate_call %s", _safe_tool_summary(fc.name, dict(fc.args)))
                ui.status.set_mode("planning")
                plan = ExecutionPlan()
                for _i, fc in mutate_ops:
                    plan.add(fc.name, dict(fc.args), workspace=workspace)

                ui.show_plan(format_plan(plan))
                if auto_approve:
                    approved = True
                else:
                    approval_start = time.monotonic()
                    approved = ui.prompt_approval()
                    approval_wait += time.monotonic() - approval_start

                if approved:
                    ui.status.set_mode("executing")
                    for i, fc in mutate_ops:
                        fc_args = dict(fc.args)
                        ui.show_tool_call(fc.name, _post_approval_summary(fc.name, fc_args))
                        result = tools.execute(fc.name, workspace, client, **fc_args)
                        if isinstance(result, tuple):
                            text, inline_parts = result
                            ui.show_tool_result(fc.name, text)
                            result_slots[i].append(
                                types.Part.from_function_response(
                                    name=fc.name, response={"result": text}
                                )
                            )
                            result_slots[i].extend(inline_parts)
                            _log.debug(
                                "inner_loop mutate_result %s type=tuple inline_parts=%d text_len=%d",
                                fc.name, len(inline_parts), len(text),
                            )
                        else:
                            ui.show_tool_result(fc.name, result)
                            result_slots[i].append(
                                types.Part.from_function_response(
                                    name=fc.name, response={"result": result}
                                )
                            )
                            _log.debug(
                                "inner_loop mutate_result %s type=text text_len=%d",
                                fc.name, len(result),
                            )
                else:
                    for i, fc in mutate_ops:
                        result_slots[i].append(
                            types.Part.from_function_response(
                                name=fc.name,
                                response={"error": "User rejected this operation."},
                            )
                        )

            # Flatten indexed slots back into original call order
            tool_result_parts: list[types.Part] = []
            for slot in result_slots:
                tool_result_parts.extend(slot)

            # Gemini uses role="user" for function responses — the API only supports
            # "user" and "model" roles, and tool results are part of the user turn.
            for group in _split_tool_results(tool_result_parts):
                messages.append(types.Content(role="user", parts=group))
            _log.debug(
                "inner_loop tool_results_appended parts=%d functions=%s",
                len(tool_result_parts),
                [fc.name for fc in function_calls],
            )
            continue  # Continue inner loop to let model process results

        else:
            # for-loop exhausted without break — max iterations reached
            ui.print_info(f"Reached max tool iterations ({MAX_TOOL_ITERATIONS}). Stopping.")

        elapsed = time.monotonic() - t0 - approval_wait
        ui.print_elapsed(elapsed)
