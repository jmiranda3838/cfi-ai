# cfi-ai

Terminal-first agentic assistant. An interactive CLI that launches a conversational agent bound to your current working directory, with the ability to inspect and modify local files.

## Install

```bash
# From GitHub (private repo — requires authentication)
pipx install git+https://github.com/jonzywoo/cfi-ai.git

# Or from a local clone
pip install -e .
# or
pipx install .
# or
uv tool install .
```

### Upgrade

```bash
pipx upgrade cfi-ai
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
transcript> [paste text or enter a file path, then Enter to submit]
```

File paths are passed to the LLM, which uses `attach_path` to load them — this handles shell escapes, spaces in paths, and other tricky filenames naturally. Audio is sent inline to Gemini for transcription and clinical document generation.

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

Mutating operations (file writes, destructive commands) require user approval.

## How It Works

- **4 core tools** — `run_command` (allowlisted shell commands), `attach_path` (file/audio/image ingestion), `apply_patch` (search-and-replace edits), `write_file` (new files only)
- **Mutation classification** — read-only operations execute immediately; mutating operations (`apply_patch`, `write_file`, destructive commands) require user approval
- **Slash command autocomplete** — type `/` to see available commands
- Status indicator shows current mode: chatting, thinking, planning, awaiting approval, executing

## Keybindings

- `Ctrl+C` — exit
- `Escape` — cancel current generation

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Releasing

1. Bump the version in both `pyproject.toml` and `src/cfi_ai/__init__.py`
2. Commit the version bump
3. Tag and push:

```bash
git tag v0.9.0 && git push origin main --tags
```

The GitHub Actions workflow validates the tag matches `pyproject.toml` and creates a GitHub Release with auto-generated notes.
