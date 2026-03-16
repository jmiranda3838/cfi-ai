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

The inner loop handles multi-turn tool-use chains. Messages are `list[types.Content]` with roles `"user"`, `"model"`, and `"user"` (for tool results). End-of-turn is detected by the **absence of function_call parts** — not by finish_reason (Gemini uses `"STOP"` for both). The loop is capped at `MAX_TOOL_ITERATIONS` (25) as a safety net. If `StreamResult.repetition_detected` fires, the garbage turn is discarded, a corrective user message is injected, and the model retries once — a second detection breaks with an error. A **narration guard** (`_NARRATION_THRESHOLD = 800`) catches workflow-mode turns where the model emits long text with no tool calls — the narrating turn is discarded and a corrective message is injected (once).

### Tool system (`tools/`)

4 core tools: `run_command`, `attach_path`, `apply_patch`, `write_file`.

- Each tool is a `BaseTool` subclass with `definition()` returning a `ToolDefinition` and `execute(workspace, **kwargs)`.
- `tools/__init__.py` maintains a registry. `get_api_tools()` returns a single `types.Tool` with all `FunctionDeclaration`s.
- Mutation classification uses `classify_mutation(name, args)` — static for `apply_patch`/`write_file`, dynamic for `run_command` (checks if command is in `MUTATING_COMMANDS`).
- `execute()` can return `str` or `tuple[str, list[Part]]`. The tuple form signals inline binary data (e.g. audio, images) — `agent.py` appends the function response *and* the extra parts to the tool result message.
- Tool results are sent as `Part.from_function_response(name=..., response={"result": ...})`. Rejected ops use `response={"error": ...}`.
- `run_command` uses `subprocess.run()` with an allowlist (no shell, no pipes, no interpreters). `READONLY_COMMANDS` and `MUTATING_COMMANDS` are defined in `tools/run_command.py`.
- `attach_path` handles all file ingestion (text, audio, images, PDFs). Binary types are inlined via `Part.from_bytes()`. Accepts absolute paths.
- `apply_patch` applies sequential search-and-replace edits transactionally.
- `write_file` only creates new files — rejects overwrites.

### Streaming (`client.py`)

`StreamResult` wraps `generate_content_stream()`. `text_chunks()` yields text for `ui.stream_markdown()` and accumulates all parts. After exhaustion, `.function_calls` and `.parts` are available.

**Repetition detection**: `text_chunks()` monitors accumulated text for consecutive repetition using multiple block sizes (`_REPEAT_BLOCK_SIZES = (200, 500)` — suffix-based check, starting after 2000 chars). If detected, streaming stops early and `repetition_detected` is set. Constants `_REPEAT_BLOCK_SIZES`, `_REPEAT_MIN_TEXT_LENGTH`, `_REPEAT_CHECK_INTERVAL` are module-level and tunable. Debug logging (`CFI_AI_LOG_LEVEL=DEBUG`) shows raw chunk data for diagnosing repetition issues.

### Key Vertex AI / Gemini gotchas

- `fc.args` is a protobuf Struct — always wrap with `dict(fc.args)` before `**` unpacking.
- Streaming chunks may have empty `candidates` — guard with `if not chunk.candidates: continue`.
- No `tool_use_id` — tool results match by function `name`; order matters.

### Slash commands (`commands/`)

- `commands/__init__.py` defines `parse_command()`, `dispatch()`, `CommandResult`, and a `@register` decorator.
- Commands are registered by importing their modules at the bottom of `__init__.py`.
- `agent.py` intercepts slash commands between input and message append — if `parse_command` matches, `dispatch` runs the handler.
- `CommandResult.message` set → replaces user input sent to LLM. `CommandResult.parts` set → multipart content (e.g. text + audio) sent directly. `handled=True` + no message/parts → skip to next prompt. `error` → display and skip. `workflow_mode=True` → enables narration guard in the agent loop.
- `/help` prints available commands. `/intake` processes a session transcript (text file or pasted) or audio recording (.mp3, .wav, .m4a, etc.) into clinical intake documents. File references are passed to the LLM which uses `attach_path` to load them (handling shell escapes, spaces in paths, etc.). Pasted multi-line text is embedded directly in the prompt.
- Typing `/` in the prompt shows autocomplete for available commands via `SlashCommandCompleter` (prompt-toolkit).

### Client file structure (`clients.py`)

- `list_clients(workspace)` → sorted client-id slugs from `clients/` subdirs.
- `load_client_context(workspace, client_id)` → reads `profile/current.md` + `treatment-plan/current.md`.
- `sanitize_client_id(name)` → slug conversion ("Jane Doe" → "jane-doe").

### Configuration

- Config file: `~/.config/cfi-ai/config.toml` (created via `cfi-ai --setup` or on first run)
- Env vars (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `CFI_AI_MODEL`, `CFI_AI_MAX_TOKENS`) override config file values when set
- ADC via `gcloud auth application-default login` (validated at startup with a clear error message)

### Update checker (`update_check.py`)

Uses a detached subprocess pattern (like npm's `update-notifier`). On startup, `main.py` calls `check_for_update(__version__)` which reads the cache file synchronously — zero latency. If the cache has a newer version, it returns the update message. If the cache is stale (>24h) or missing, it spawns a fire-and-forget detached subprocess (`start_new_session=True`, DEVNULL stdio) to refresh the cache. The update notification is therefore one run behind.

- Cache: `~/.config/cfi-ai/update-check.json` — stores `last_check` timestamp + `latest_version`. Skips network if <24h old.
- Detached subprocess: `sys.executable -c "..."` with self-contained token discovery + network fetch logic.
- GitHub token discovery: `GITHUB_TOKEN` env → `GH_TOKEN` env → `gh auth token` subprocess.
- All errors silently caught — never blocks or crashes startup.
- No new dependencies (stdlib only: `urllib.request`, `json`, `subprocess`, `textwrap`).
- `GITHUB_REPO` constant in `update_check.py` controls which repo is checked.

### Versioning

The version is defined in two places — keep them in sync:
- `pyproject.toml` → `version = "X.Y.Z"`
- `src/cfi_ai/__init__.py` → `__version__ = "X.Y.Z"`

Bump the version on any user-facing change (bug fix → patch, new feature or breaking change → minor).

### Releasing

1. Bump version in `pyproject.toml` + `src/cfi_ai/__init__.py`
2. Commit, tag (`git tag vX.Y.Z`), push with tags
3. GitHub Actions (`.github/workflows/release.yml`) validates the tag matches `pyproject.toml` and creates a GitHub Release with auto-generated notes
