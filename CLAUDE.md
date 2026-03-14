# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

```bash
uv pip install -e .          # Install in dev mode
uv run pytest tests/ -v      # Run all tests
uv run pytest tests/test_tools.py::test_registry -v  # Run a single test
```

## Architecture

cfi-ai is a terminal-first agentic assistant that binds to the user's current working directory. It uses Google Vertex AI (Gemini) via the `google-genai` SDK with Application Default Credentials (no API keys).

### Request flow

`main.py` → builds `Config` (from `~/.config/cfi-ai/config.toml` with env var overrides, triggering interactive setup on first run), validates ADC, `Workspace` (from cwd), `Client` (Vertex AI), `UI` (Rich + prompt-toolkit) → enters `run_agent_loop` in `agent.py`.

### Agent loop (`agent.py`)

The inner loop handles multi-turn tool-use chains. Messages are `list[types.Content]` with roles `"user"`, `"model"`, and `"user"` (for tool results). End-of-turn is detected by the **absence of function_call parts** — not by finish_reason (Gemini uses `"STOP"` for both).

### Tool system (`tools/`)

- Each tool is a `BaseTool` subclass with `definition()` returning a `ToolDefinition` and `execute(workspace, **kwargs)`.
- `tools/__init__.py` maintains a registry. `get_api_tools()` returns a single `types.Tool` with all `FunctionDeclaration`s.
- Tools are split into **read-only** (execute immediately) and **mutating** (`mutating = True` → plan-and-approve via `planner.py` before execution).
- `execute()` can return `str` or `tuple[str, list[Part]]`. The tuple form signals inline binary data (e.g. audio) — `agent.py` appends the function response *and* the extra parts to the tool result message.
- Tool results are sent as `Part.from_function_response(name=..., response={"result": ...})`. Rejected ops use `response={"error": ...}`.
- `read_file` and `read_audio` accept both absolute and workspace-relative paths. `AUDIO_EXTENSIONS` is defined in `tools/read_audio.py`.

### Streaming (`client.py`)

`StreamResult` wraps `generate_content_stream()`. `text_chunks()` yields text for `ui.stream_markdown()` and accumulates all parts. After exhaustion, `.function_calls` and `.parts` are available.

### Key Vertex AI / Gemini gotchas

- `fc.args` is a protobuf Struct — always wrap with `dict(fc.args)` before `**` unpacking.
- Streaming chunks may have empty `candidates` — guard with `if not chunk.candidates: continue`.
- No `tool_use_id` — tool results match by function `name`; order matters.

### Slash commands (`commands/`)

- `commands/__init__.py` defines `parse_command()`, `dispatch()`, `CommandResult`, and a `@register` decorator.
- Commands are registered by importing their modules at the bottom of `__init__.py`.
- `agent.py` intercepts slash commands between input and message append — if `parse_command` matches, `dispatch` runs the handler.
- `CommandResult.message` set → replaces user input sent to LLM. `CommandResult.parts` set → multipart content (e.g. text + audio) sent directly. `handled=True` + no message/parts → skip to next prompt. `error` → display and skip.
- `/help` prints available commands. `/intake` processes a session transcript (text file or pasted) or audio recording (.mp3, .wav, .m4a, etc.) into clinical intake documents. File references are passed to the LLM which uses `read_file` or `read_audio` tools to load them (handling shell escapes, spaces in paths, etc.). Pasted multi-line text is embedded directly in the prompt.
- Typing `/` in the prompt shows autocomplete for available commands via `SlashCommandCompleter` (prompt-toolkit).

### Client file structure (`clients.py`)

- `list_clients(workspace)` → sorted client-id slugs from `clients/` subdirs.
- `load_client_context(workspace, client_id)` → reads `profile/current.md` + `treatment-plan/current.md`.
- `sanitize_client_id(name)` → slug conversion ("Jane Doe" → "jane-doe").

### Configuration

- Config file: `~/.config/cfi-ai/config.toml` (created via `cfi-ai --setup` or on first run)
- Env vars (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `CFI_AI_MODEL`, `CFI_AI_MAX_TOKENS`) override config file values when set
- ADC via `gcloud auth application-default login` (validated at startup with a clear error message)

### Versioning

The version is defined in two places — keep them in sync:
- `pyproject.toml` → `version = "X.Y.Z"`
- `src/cfi_ai/__init__.py` → `__version__ = "X.Y.Z"`

Bump the version on any user-facing change (bug fix → patch, new feature or breaking change → minor).
