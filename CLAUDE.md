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

The inner loop handles multi-turn tool-use chains. Messages are `list[types.Content]` with roles `"user"`, `"model"`, and `"user"` (for tool results). End-of-turn is detected by the **absence of function_call parts** — not by finish_reason (Gemini uses `"STOP"` for both). The loop is capped at `MAX_TOOL_ITERATIONS` (25) as a safety net. If the model stops making tool calls and returns non-empty text, the turn is complete. If it stops making tool calls and returns no text, a continuation prompt is injected (up to 2 retries) to recover from an empty or incomplete turn.

### Tool system (`tools/`)

8 tools: `run_command`, `attach_path`, `apply_patch`, `write_file`, `extract_document`, `interview`, `activate_map`, `end_turn`.

- Each tool is a `BaseTool` subclass with `definition()` returning a `ToolDefinition` and `execute(workspace, **kwargs)`.
- `tools/__init__.py` maintains a registry. `get_api_tools(enable_grounding=True)` returns a `list[types.Tool]` — the first entry is a `Tool` with all function declarations, and (when grounding is enabled) the second is a `Tool(google_search=GoogleSearch())`.
- `end_turn` is a no-arg signal tool the model calls (alone) to mark its turn complete. The agent loop treats `end_turn` as a hard break and elsewhere relies on the absence of function calls to detect natural turn end.
- Mutation classification uses `classify_mutation(name, args)` — static for `apply_patch`/`write_file`, dynamic for `run_command` (checks if command is in `MUTATING_COMMANDS`).
- `execute()` can return `str` or `tuple[str, list[Part]]`. The tuple form signals inline binary data (e.g. audio, images) — `agent.py` appends the function response *and* the extra parts to the tool result message.
- Tool results are sent as `Part.from_function_response(name=..., response={"result": ...})`. Rejected ops use `response={"error": ...}`.
- `run_command` uses `subprocess.run()` with an allowlist (no shell, no pipes, no interpreters). `READONLY_COMMANDS` and `MUTATING_COMMANDS` are defined in `tools/run_command.py`.
- `attach_path` handles all file ingestion (text, audio, images, PDFs). Binary types are inlined via `Part.from_bytes()`. Accepts absolute paths.
- `apply_patch` applies sequential search-and-replace edits transactionally.
- `write_file` rejects existing files by default — pass `overwrite=true` to replace one entirely. For targeted edits, use `apply_patch` instead.

### Streaming (`client.py`)

`StreamResult` wraps `generate_content_stream()`. `text_chunks()` yields text for `ui.stream_markdown()` and accumulates all parts. After exhaustion, `.function_calls`, `.parts`, and `.grounding_metadata` are available.

### Google Search grounding

Vertex AI Google Search grounding is enabled by default. The `GoogleSearch` tool is appended as a separate `types.Tool` entry in the tool set — it is NOT a function declaration the model "calls" through the normal function-call path.

- **Disable**: `[grounding] enabled = false` in `~/.config/cfi-ai/config.toml` or `CFI_AI_GROUNDING_ENABLED=0`. When disabled, `get_api_tools` skips the grounding tool, and the system prompts drop the `web search` bullet so the model isn't told it has a capability it doesn't.
- **Capture**: `StreamResult` reads `candidate.grounding_metadata` from the streaming chunks (last writer wins — Gemini emits it on the final chunk; see `client.py:215`).
- **Render**: `_render_grounding_sources` in `agent.py` formats citations using sparse `[idx+1]` numbering (matches Google's recommended labeling) and surfaces the `web_search_queries` the model issued for auditability. Called only after a turn produces parts — empty/aborted turns skip rendering.
- **Suggestions UI**: Vertex's `search_entry_point.rendered_content` HTML is written to `<tmpdir>/cfi-ai-search-suggestions.html` so the citations block can include a clickable `file://` URI. Auto-open in the browser is opt-in via `[grounding] open_browser = true` or `CFI_AI_GROUNDING_OPEN_BROWSER=1` (default off).
- **Incompatible models**: `_is_grounding_invalid_argument` detects Vertex `INVALID_ARGUMENT` failures from combining function calling with grounding on older models (e.g. gemini-2.5) and `_report_api_error` substitutes a targeted "switch model" message instead of the raw API error.

### Key Vertex AI / Gemini gotchas

- `fc.args` is a protobuf Struct — always wrap with `dict(fc.args)` before `**` unpacking.
- Streaming chunks may have empty `candidates` — guard with `if not chunk.candidates: continue`.
- No `tool_use_id` — tool results match by function `name`; order matters.

### Maps (`maps/`)

- `maps/__init__.py` defines `parse_map_invocation()`, `dispatch_map()`, `MapResult`, and a `@register_map` decorator.
- Maps are registered by importing their modules at the bottom of `__init__.py`.
- `agent.py` intercepts slash maps between input and message append — if `parse_map_invocation` matches, `dispatch_map` runs the handler.
- `MapResult.message` set → replaces user input sent to LLM. `MapResult.parts` set → multipart content (e.g. text + audio) sent directly. `handled=True` + no message/parts → skip to next prompt. `error` → display and skip. `map_mode=True` → uses map prompting/model mode, but turn completion still follows the standard tool-call/text rule.
- `/help` prints available maps. `/intake` processes a session transcript (text file or pasted) or audio recording (.mp3, .wav, .m4a, etc.) into clinical intake documents. File references are passed to the LLM which uses `attach_path` to load them (handling shell escapes, spaces in paths, etc.). Pasted multi-line text is embedded directly in the prompt.
- `/clear` drops in-memory history, zeros the cost tracker (mutated in place so the UI's bottom-toolbar reference stays connected), and re-points the session store at a fresh file via `SessionStore.reset()` so post-clear turns don't overwrite the prior session JSON.
- `/bugreport [description]` loads the current session JSON and sends it to Gemini with a PHI-scrubbing summarization prompt (`prompts/bugreport.py`). Gemini returns a concise markdown bug summary with PHI already redacted — NOT the full transcript. The handler previews the summary and offers `(p)ost / (e)dit / (s)ave / (q)uit`. Pressing `p` triggers a two-step confirm: the user must type `POST` (case-sensitive) to actually POST to the GitHub repo in `[bugreport] repo` (default `jmiranda3838/cfi-ai`). Token discovery (`GITHUB_TOKEN` → `GH_TOKEN` → `gh auth token`) is lazy — only runs on the real post path, so `e`, `s`, `q`, and dry-run all work without GitHub auth. `CFI_AI_BUGREPORT_DRY_RUN=1` saves the draft to `bugreport-dryrun-*.md` instead of posting. The summarizer uses a fail-closed finish-reason check (`_call_summarizer` in `maps/bugreport.py`) — any non-`STOP` outcome aborts the post. Full raw session JSON stays on disk at `~/.config/cfi-ai/sessions/` (pruned after 30 days); it is never sent to GitHub. Handler returns `handled=True` so the invocation itself is not injected into the therapy conversation. The handler reads from disk, so the most recent turn only appears if the last `session_store.save()` succeeded.
- Typing `/` in the prompt shows autocomplete for available maps via `SlashMapCompleter` (prompt-toolkit).

### Client file resolution

Client profile / treatment-plan / session files are NOT pre-loaded into the system prompt or message list, and there is no Python-side client-id registry. The system prompt includes the `clients/<client-id>/…` directory convention as reference boilerplate (see `prompts/system.py`), and each clinical map prompt has a "Resolving Client Context" section that instructs the LLM to discover clients via `run_command ls clients/` and disambiguate via `interview` at runtime. When a user mentions a client, the LLM pulls files in via `attach_path` or `run_command`, or activates a map (e.g. `session`, `tp-review`) whose prompt drives the load.

### Configuration

- Config file: `~/.config/cfi-ai/config.toml` (created via `cfi-ai --setup` or on first run). Recognized sections: `[project]`, `[model]`, `[grounding]`, `[bugreport]`. Unknown sections are preserved across `--setup` re-runs.
- Env vars override config file values when set: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `CFI_AI_MODEL`, `CFI_AI_MAX_TOKENS`, `CFI_AI_MAX_CONTEXT_TOKENS`, `CFI_AI_CONTEXT_CACHE`, `CFI_AI_GROUNDING_ENABLED`, `CFI_AI_GROUNDING_OPEN_BROWSER`, `CFI_AI_BUGREPORT_ENABLED`, `CFI_AI_BUGREPORT_REPO`, `CFI_AI_BUGREPORT_DRY_RUN`.
- `_parse_bool_env` accepts case-insensitive `0/false/no/off` as falsy. Empty / whitespace-only values fall back to the caller's `default` (so `CFI_AI_GROUNDING_ENABLED=''` doesn't accidentally flip the default-True flag to False).
- ADC via `gcloud auth application-default login` (validated at startup with a clear error message)

### Installation (`scripts/install.sh`)

One-command installer for non-technical users: `curl -fsSL https://raw.githubusercontent.com/jmiranda3838/cfi-ai/main/scripts/install.sh | bash`. Installs `uv` if missing, installs cfi-ai via `uv tool install`, fixes PATH via `uv tool update-shell`, and checks for `gcloud`. Idempotent — safe to run again (upgrades if already installed).

The `--update` flag in `main.py` runs `uv tool upgrade cfi-ai`. It uses `shutil.which("uv")` to find `uv` and prints a friendly error if not found.

### Update checker (`update_check.py`)

Uses a detached subprocess pattern (like npm's `update-notifier`). On startup, `main.py` calls `check_for_update(__version__)` which reads the cache file synchronously — zero latency. If the cache has a newer version, it returns the update message. If the cache is stale (>24h) or missing, it spawns a fire-and-forget detached subprocess (`start_new_session=True`, DEVNULL stdio) to refresh the cache. The update notification is therefore one run behind.

- Cache: `~/.config/cfi-ai/update-check.json` — stores `last_check` timestamp + `latest_version`. Skips network if <24h old.
- Detached subprocess: `sys.executable -c "..."` with self-contained token discovery + network fetch logic.
- Repo is public — no GitHub token needed, but token discovery (`GITHUB_TOKEN` env → `GH_TOKEN` env → `gh auth token`) is still in place for rate-limit avoidance.
- All errors silently caught — never blocks or crashes startup.
- No new dependencies (stdlib only: `urllib.request`, `json`, `subprocess`, `textwrap`).
- `GITHUB_REPO` constant in `update_check.py` controls which repo is checked.

### Versioning

Single source of truth: `pyproject.toml` → `version = "X.Y.Z"`. At runtime, `src/cfi_ai/__init__.py` reads it via `importlib.metadata.version("cfi-ai")` — no hardcoded version string to keep in sync. After changing `pyproject.toml`, run `uv pip install -e .` to refresh the metadata.

Bump the version on any user-facing change (bug fix → patch, new feature or breaking change → minor).

### Releasing

Run `scripts/release.sh <version>` (e.g. `scripts/release.sh 0.10.0`). The script validates inputs, updates `pyproject.toml`, reinstalls, commits, tags `vX.Y.Z`, and pushes. GitHub Actions (`.github/workflows/release.yml`) then creates the GitHub Release.