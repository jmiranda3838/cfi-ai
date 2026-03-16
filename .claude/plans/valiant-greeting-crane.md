# Plan: Add Plan Mode with Shift+Tab Toggle

## Context

Users need a way to have the LLM research and propose changes before executing them. Plan mode lets the user toggle into a read-only research phase where the LLM explores the codebase and produces a structured implementation plan. The user can then approve (clearing context and executing with a fresh LLM call) or reject (continuing to chat with history preserved).

## Files to Modify

1. **`src/cfi_ai/ui.py`** — Input layer: `UserInput` type, Shift+Tab toggle, plan-mode visuals
2. **`src/cfi_ai/tools/__init__.py`** — New `get_readonly_api_tools()`
3. **`src/cfi_ai/prompts/system.py`** — New `build_plan_mode_system_prompt()`
4. **`src/cfi_ai/agent.py`** — Plan-mode branch + `_run_plan_mode()` helper
5. **`tests/test_plan_mode.py`** — New tests

## Step 1: `src/cfi_ai/ui.py`

- Add `UserInput` dataclass (`text: str`, `plan_mode: bool = False`)
- Add `_plan_mode: bool` to `UI.__init__`, with `toggle_plan_mode()` method
- Add to `MODE_DISPLAY`: `"chatting_plan": "plan mode"`, `"thinking_plan": "researching .."`
- Update `_chat_key_bindings(on_toggle_plan=None)`: bind `s-tab` → call callback + `event.app.invalidate()` for toolbar refresh
- Update `get_input() -> UserInput | None`:
  - Prompt char: `"@ "` (accent color) in plan mode, `"~ "` normally
  - Toolbar: add `Shift+Tab to toggle plan mode` hint
  - Capture `plan_mode` at submission time, auto-reset `_plan_mode = False`
- Add `show_research_plan(plan_text)` — Rich Panel with Markdown, titled "Implementation Plan"
- Add `prompt_plan_approval() -> bool` — `"execute plan? [Y/n] "` prompt
- Update `print_welcome()` to mention Shift+Tab

## Step 2: `src/cfi_ai/tools/__init__.py`

- Add `get_readonly_api_tools()`: filters `_REGISTRY` to return only `run_command` and `attach_path` declarations
- Add to `__all__`

## Step 3: `src/cfi_ai/prompts/system.py`

- Add `build_plan_mode_system_prompt(workspace_path, workspace_summary, workspace)`:
  - Identity: "You are cfi-ai in PLAN MODE"
  - Only read-only tools: `run_command` (read-only commands), `attach_path`
  - Explicitly no `apply_patch`, `write_file`, or mutating commands
  - Output format: Summary, Steps (File + Action + Details for each), Dependencies, Risks
  - Guidelines: research thoroughly, read actual code, be specific with locations

## Step 4: `src/cfi_ai/agent.py`

**Setup changes in `run_agent_loop()`:**
- Build `readonly_api_tools` and `plan_system_prompt` at init
- Update input handling to use `UserInput` type (`.text`, `.plan_mode`)

**Plan-mode branch** (before normal chat flow):
- If `plan_mode=True`:
  - Copy existing `messages`, append user request
  - Call `_run_plan_mode()` → returns plan text or None
  - Display plan via `ui.show_research_plan()`
  - Prompt via `ui.prompt_plan_approval()`
  - **Approve**: `messages.clear()`, inject plan as first user message with execution instruction, set `workflow_mode=True`, fall through to normal inner loop
  - **Reject**: append user request + plan to `messages` for context, `continue` to next prompt

**New `_run_plan_mode()` helper:**
- Signature: `(client, ui, workspace, plan_system_prompt, readonly_tools, messages) -> str | None`
- Inner loop: stream → handle repetition → execute read-only tools → reject mutations (belt-and-suspenders via `classify_mutation`) → return final text as plan
- Sets mode to `"thinking_plan"` during streaming
- Returns `None` on error/cancel/KeyboardInterrupt

## Step 5: `tests/test_plan_mode.py`

- `test_user_input_dataclass`: verify fields and defaults
- `test_get_readonly_api_tools`: only `run_command` + `attach_path`
- `test_plan_mode_system_prompt`: contains "PLAN MODE", "read-only", no `apply_patch`/`write_file`
- `test_plan_mode_rejects_mutations`: `classify_mutation` guard works
- `test_mode_display_plan_modes`: new entries in `MODE_DISPLAY`

## Verification

1. `uv run pytest tests/ -v` — all tests pass
2. Manual: press Shift+Tab → toolbar shows "plan mode", prompt changes to `@ `
3. Manual: submit request → LLM researches read-only → outputs structured plan
4. Manual: approve → context clears, fresh LLM executes with full tools
5. Manual: reject → back to chat with history preserved
