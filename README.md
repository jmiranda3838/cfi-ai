# cfi-ai

Terminal-first agentic assistant. An interactive CLI that launches a conversational agent bound to your current working directory, with the ability to inspect and modify local files.

## Install

Open Terminal and run:

```bash
curl -fsSL https://raw.githubusercontent.com/jmiranda3838/cfi-ai/main/scripts/install.sh | bash
```

The installer sets up everything you need. After it finishes, restart your terminal and run `cfi-ai`.

### Update

```bash
cfi-ai --update
```

### Prerequisites

The installer handles the package manager (`uv`) automatically. You will also need:

- **Google Cloud SDK** — the installer will remind you if it's missing. Install from https://cloud.google.com/sdk/docs/install, then run:
  ```bash
  gcloud auth application-default login
  ```

### Configuration

On first run, cfi-ai will prompt you to set up your Google Cloud project. You can re-run setup anytime:

```bash
cfi-ai --setup
```

<details>
<summary>Manual install (advanced)</summary>

```bash
# Requires uv (https://docs.astral.sh/uv/)
uv tool install git+https://github.com/jmiranda3838/cfi-ai.git
```
</details>

## Usage

```bash
cfi-ai
```

### Options

```
cfi-ai --version       Show version
cfi-ai --model MODEL   Override the default model
cfi-ai --setup         Run interactive setup (creates/updates config file)
cfi-ai --update        Update to the latest version
cfi-ai --help          Show help
```

### Environment Variable Overrides

Environment variables take precedence over the config file when set:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | from config file | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | `global` | Vertex AI location |
| `CFI_AI_MODEL` | `gemini-3-flash-preview` | Model to use |
| `CFI_AI_MAX_TOKENS` | `8192` | Max response tokens |

## Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/intake` | Process intake materials into TheraNest-ready clinical documents |

### `/intake` — Clinical Intake Workflow

Process intake materials into TheraNest-ready clinical documents. Upload a combination of session audio, intake questionnaire, wellness assessment, and other assessments — the LLM generates output structured to TheraNest's exact field layout for direct copy-paste.

Slash commands use a thin-routing design. If you provide enough structured input up front, the app activates the workflow immediately. If information is missing or ambiguous, the assistant collects it with guided follow-up questions via the `interview` tool before activating the workflow.

```bash
# Audio + intake questionnaire + wellness assessment
~ /intake /path/to/session.m4a /path/to/intake-questionnaire.pdf /path/to/wellness-assessment.pdf

# Just an audio file
~ /intake session-recording.m4a

# From an absolute path
~ /intake /Users/you/Downloads/session-recording.m4a

# Start with no args and answer follow-up questions
~ /intake
[assistant asks for transcript text or file paths]
```

If you start with `/intake` and no args, the assistant will ask for the missing transcript text or file paths interactively. File paths are passed to the LLM, which uses `attach_path` to load them — this handles shell escapes, spaces in paths, and other tricky filenames naturally. Audio is sent inline to Gemini for transcription and clinical document generation.

The workflow generates 5 documents:
- **Initial Assessment** — TheraNest "Initial Assessment & Diagnostic Codes" tab fields (diagnostic impressions, presenting problem, observations, history, risk assessment, strengths, goals, etc.)
- **Treatment Plan** — TheraNest Treatment Plan tab fields (behavioral definitions, goals & objectives with interventions, modality, frequency, etc.)
- **Progress Note** — TheraNest standard note fields in DAP format (data, assessment, plan)
- **Intake Transcript** — raw session transcript with speaker labels
- **Client Profile** — internal app reference for returning-client context (not a TheraNest deliverable)

Files are saved under `clients/<client-id>/` with dated filenames:

```
clients/jane-doe/
  intake/2025-01-15-initial-assessment.md
  profile/2025-01-15-profile.md
  profile/current.md
  treatment-plan/2025-01-15-treatment-plan.md
  treatment-plan/current.md
  sessions/2025-01-15-progress-note.md
  sessions/2025-01-15-intake-transcript.md
```

Mutating operations (file writes, destructive commands) require user approval.

## How It Works

- **6 core tools** — `run_command` (allowlisted shell commands), `attach_path` (file/audio/image ingestion), `apply_patch` (search-and-replace edits), `write_file` (new files only), `extract_document` (structured document extraction), `transcribe_audio` (audio transcription)
- **Mutation classification** — read-only operations execute immediately; mutating operations (`apply_patch`, `write_file`, destructive commands) require user approval
- **Slash command autocomplete** — type `/` to see available commands
- Status indicator shows current mode: chatting, thinking, planning, awaiting approval, executing

## Keybindings

- `Ctrl+C` — exit
- `Escape` — cancel current generation

## Development

```bash
uv pip install -e ".[dev]"
uv run pytest
```

## Releasing

```bash
scripts/release.sh <version>   # e.g. scripts/release.sh 0.12.0
```

The script bumps `pyproject.toml`, commits, tags, and pushes. GitHub Actions creates the release.
