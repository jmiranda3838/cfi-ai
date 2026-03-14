# cfi-ai

Terminal-first agentic assistant. An interactive CLI that launches a conversational agent bound to your current working directory, with the ability to inspect and modify local files.

## Install

```bash
pip install -e .
# or
pipx install .
# or
uv tool install .
```

## Setup

### 1. Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

### 2. Configure cfi-ai

On first run, cfi-ai will interactively prompt you to create a config file at `~/.config/cfi-ai/config.toml`:

```bash
cfi-ai
```

Or run setup explicitly:

```bash
cfi-ai --setup
```

Example generated config:

```toml
[project]
id = "my-gcp-project"
location = "global"

[model]
name = "gemini-2.5-flash"
max_tokens = 8192
```

Re-running `--setup` pre-fills existing values as defaults.

## Usage

```bash
cfi-ai
```

### Options

```
cfi-ai --version       Show version
cfi-ai --model MODEL   Override the default model
cfi-ai --setup         Run interactive setup (creates/updates config file)
cfi-ai --help          Show help
```

### Environment Variable Overrides

Environment variables take precedence over the config file when set:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | from config file | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | `global` | Vertex AI location |
| `CFI_AI_MODEL` | `gemini-2.5-flash` | Model to use |
| `CFI_AI_MAX_TOKENS` | `8192` | Max response tokens |

## How It Works

- **Read-only tools** (`list_files`, `read_file`, `search_files`) execute immediately
- **Mutating tools** (`write_file`, `edit_file`) require an execution plan + user approval before running
- Status indicator shows current mode: chatting, thinking, planning, awaiting approval, executing

## Keybindings

- `Ctrl+C` — cancel current generation
- `Ctrl+D` — exit

## Development

```bash
pip install -e ".[dev]"
pytest
```
