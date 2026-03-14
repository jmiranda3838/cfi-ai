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
- Tool results are sent as `Part.from_function_response(name=..., response={"result": ...})`. Rejected ops use `response={"error": ...}`.

### Streaming (`client.py`)

`StreamResult` wraps `generate_content_stream()`. `text_chunks()` yields text for `ui.stream_markdown()` and accumulates all parts. After exhaustion, `.function_calls` and `.parts` are available.

### Key Vertex AI / Gemini gotchas

- `fc.args` is a protobuf Struct — always wrap with `dict(fc.args)` before `**` unpacking.
- Streaming chunks may have empty `candidates` — guard with `if not chunk.candidates: continue`.
- No `tool_use_id` — tool results match by function `name`; order matters.

### Configuration

- Config file: `~/.config/cfi-ai/config.toml` (created via `cfi-ai --setup` or on first run)
- Env vars (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `CFI_AI_MODEL`, `CFI_AI_MAX_TOKENS`) override config file values when set
- ADC via `gcloud auth application-default login` (validated at startup with a clear error message)
