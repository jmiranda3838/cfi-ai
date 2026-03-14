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

## Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/intake` | Process a session transcript or audio recording into intake documents |

### `/intake` — Clinical Intake Workflow

Process a session transcript or audio recording into structured clinical documents:

```bash
# From a text file
~ /intake session-notes.txt

# From an audio file (.mp3, .wav, .m4a, .aac, .ogg, .flac, .aiff, .webm)
~ /intake session-recording.mp3

# From an absolute path (e.g. Downloads)
~ /intake /Users/you/Downloads/session-recording.m4a

# Paste interactively
~ /intake
transcript> [paste text or enter a file path, then Esc+Enter to submit]
```

Audio files are sent directly to Gemini for transcription and clinical document generation — no separate speech-to-text step needed.

The workflow generates:
- **Intake Assessment** — presenting concerns, history, symptoms, risk, impressions
- **Client Profile** — reusable summary of demographics, context, strengths
- **Treatment Plan** — problems, goals, objectives, interventions, review timeline

Files are saved under `clients/<client-id>/` with dated filenames:

```
clients/jane-doe/
  intake/2025-01-15-intake-assessment.md
  profile/2025-01-15-profile.md
  profile/current.md
  treatment-plan/2025-01-15-treatment-plan.md
  treatment-plan/current.md
  sessions/2025-01-15-intake-transcript.md
```

All file writes go through the normal plan-and-approve flow.

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
