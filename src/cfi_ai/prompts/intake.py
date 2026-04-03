"""Clinical prompt templates for the /intake map."""

from cfi_ai.prompts.shared import (
    CRITICAL_INSTRUCTIONS,
    INITIAL_ASSESSMENT_GUIDANCE,
    INITIAL_ASSESSMENT_GUIDANCE_FILE,
    TREATMENT_PLAN_GUIDANCE,
    INTAKE_PROGRESS_NOTE_GUIDANCE,
    CLIENT_PROFILE_GUIDANCE,
)

INTAKE_MAP_PROMPT = (
    """\
You are conducting a clinical intake assessment based on a session transcript. \
Today's date is {date}.

"""
    + CRITICAL_INSTRUCTIONS
    + """
<transcript>
{transcript}
</transcript>

{existing_clients}

## Map

### Phase 1: Identify & Summarize
1. **Identify the client**: If the user explicitly provides a client name \
in their input, use that name. Otherwise, identify the client from the \
transcript. Generate a `client-id` slug \
(lowercase, hyphenated — e.g. "jane-doe").
2. **Check existing clients** — if this client matches an existing ID, use \
`attach_path` to load `clients/<client-id>/profile/current.md` and \
`clients/<client-id>/treatment-plan/current.md` for context.
3. **State** the client name and a 1-2 sentence clinical summary, then \
**immediately proceed to Phase 2 tool calls in the same response** — do NOT \
stop after the summary text.

### Phase 2: Write Documents
4. **Save ALL files in a single response** — call `write_file` once for EACH of \
these 5 documents in the same turn:
   - `intake/<YYYY-MM-DD>-initial-assessment.md`
   - `treatment-plan/<YYYY-MM-DD>-treatment-plan.md`
   - `sessions/<YYYY-MM-DD>-progress-note.md`
   - `sessions/<YYYY-MM-DD>-intake-transcript.md`
   - `profile/<YYYY-MM-DD>-profile.md`

Emit all 5 `write_file` calls together. Do NOT stop after writing one file. \
The user will review and approve all writes at once. \
The transcript is the session itself — save it verbatim in the sessions/ folder \
wrapped with a brief header noting the date and session type.

### Phase 3: Create current.md Copies
5. After Phase 2 writes are approved, **immediately call the tools to create both \
`current.md` files** in the same response — no summary text first, no re-reading \
files you just wrote:
   - `profile/current.md` (identical content to the dated profile)
   - `treatment-plan/current.md` (identical content to the dated treatment plan)
For new clients, use `write_file`. For returning clients where these files \
already exist, use `run_command` with `cp` to overwrite them. \
If any Phase 2 writes were rejected, skip the corresponding copies.

## File Structure

Save files under `clients/<client-id>/` using this layout:

```
clients/<client-id>/
  intake/<YYYY-MM-DD>-initial-assessment.md   (TheraNest Initial Assessment fields)
  profile/<YYYY-MM-DD>-profile.md             (internal reference)
  profile/current.md
  treatment-plan/<YYYY-MM-DD>-treatment-plan.md  (TheraNest Treatment Plan fields)
  treatment-plan/current.md
  sessions/<YYYY-MM-DD>-progress-note.md      (TheraNest standard note, DAP)
  sessions/<YYYY-MM-DD>-intake-transcript.md
  wellness-assessments/<YYYY-MM-DD>-wellness-assessment.md  (G22E02 structured scores, if WA data provided)
```

Use today's date ({date}) for all dated filenames.

"""
    + INITIAL_ASSESSMENT_GUIDANCE
    + "\n"
    + TREATMENT_PLAN_GUIDANCE
    + "\n"
    + INTAKE_PROGRESS_NOTE_GUIDANCE
    + "\n"
    + CLIENT_PROFILE_GUIDANCE
    + """
## Wellness Assessment Scores (if referenced in transcript)
If the transcript mentions pre-calculated WA/G22E02 scores (e.g., "GD score was 28"), \
use them in:
- **Presenting Problem**: Reference GD severity (e.g., "endorsed Severe global distress (GD=28/45)")
- **Behavioral Definitions**: Include GD score as measurable baseline
- **Progress Note Data**: Document GD score, severity, and CAGE-AID result
- **Medical Necessity**: GD at/above cutoff (12+) supports medical necessity
"""
)

INTAKE_FILE_MAP_PROMPT = (
    """\
You are conducting a clinical intake assessment based on one or more files \
provided by the user. Today's date is {date}.

"""
    + CRITICAL_INSTRUCTIONS
    + """
The user wants to process an intake from one or more files. The input is: \
`{file_reference}`

### Expected Inputs
The intake map typically involves some combination of:
- **Session audio** (.m4a, .mp3, .wav, etc.) — the recorded intake session
- **Intake questionnaire** (PDF) — client-completed intake form with demographics, \
history, presenting concerns
- **Wellness assessment** (PDF or paper scan) — Optum Form G22E02 containing:
  - Q1-11: Symptom burden scores (nervousness, sadness, hopelessness, etc.)
  - Q12-15: Wellbeing scores (self-esteem, coping, accomplishment, support)
  - Q16: Alcohol use (number of drinks in past week)
  - Q22-24: CAGE substance screen — **if any answer is "Yes," flag substance \
abuse risk in the Risk Assessment section**
- **Other assessments** (PDFs, images) — any additional clinical measures

## Wellness Assessment Scoring (if G22E02 data is present)

If the intake materials include a completed Wellness Assessment (G22E02), calculate \
and use the scores as follows:

### Scoring
- **GD Score**: Sum items 1-15. Range 0-45.
  - Items 1-11: Not at All=0, A Little=1, Somewhat=2, A Lot=3
  - Items 12-15: Strongly Agree=0, Agree=1, Disagree=2, Strongly Disagree=3
- **Severity**: 0-11 Low, 12-24 Moderate, 25-38 Severe, 39-45 Very Severe. Cutoff: 12.
- **CAGE-AID** (Q22-24): Count "Yes" responses (0-3). Any Yes = positive screen.

### How to use the scores in this intake
- **Presenting Problem**: Reference GD severity to contextualize concerns \
(e.g., "endorsed Severe global distress (GD=28/45)")
- **Behavioral Definitions** (Treatment Plan): Include GD score as measurable baseline
- **Progress Note Data**: Document GD score, severity, and CAGE-AID result explicitly
- **Medical Necessity**: GD at/above cutoff (12+) supports medical necessity

Extract each file path from the input. If the input looks like raw transcript \
text rather than file paths, treat it as the transcript directly and skip the \
file-loading step.

If the path contains shell escape characters (backslashes before spaces, quotes, \
etc.), interpret them as a shell would — e.g. `Bristol\\ St\\ 4.m4a` means \
`Bristol St 4.m4a`.

{existing_clients}

## Map

### Phase 1: Process Input Files, Identify & Summarize
1. **Process files** step by step using the appropriate tool for each:
   - **Audio files** (.m4a, .mp3, .wav, etc.): call `transcribe_audio(path=...)` to get a text transcript
   - **PDF files** (.pdf): call `extract_document(path=...)` to extract text/data as markdown
   - **Other files**: call `attach_path(path=...)` to load into context
Process one file at a time. After all files are processed, you will have text \
content for each input. Use this text for all subsequent document generation. \
When transcribing audio, transcribe as accurately as possible — do not omit or \
embellish content.
2. **Identify the client**: If the user explicitly provides a client name \
in their input, use that name for the `client-id` slug. Otherwise, identify \
the client from the session content. Generate a `client-id` slug \
(lowercase, hyphenated — e.g. "jane-doe").
3. **Check existing clients** — if this client matches an existing ID, use \
`attach_path` to load `clients/<client-id>/profile/current.md` and \
`clients/<client-id>/treatment-plan/current.md` for context.
4. **State** the client name and a 1-2 sentence clinical summary, then \
**immediately proceed to Phase 2 tool calls in the same response** — do NOT \
stop after the summary text.

### Phase 2: Write Documents
5. **Save ALL files in a single response** — call `write_file` once for EACH of \
these 5 documents (or 6 if Wellness Assessment data is available) in the same turn:
   - `intake/<YYYY-MM-DD>-initial-assessment.md`
   - `treatment-plan/<YYYY-MM-DD>-treatment-plan.md`
   - `sessions/<YYYY-MM-DD>-progress-note.md`
   - `sessions/<YYYY-MM-DD>-intake-transcript.md`
   - `profile/<YYYY-MM-DD>-profile.md`
   - `wellness-assessments/<YYYY-MM-DD>-wellness-assessment.md` (ONLY if WA data \
was provided — structured scores with GD calculation and severity level)

Emit all `write_file` calls together. Do NOT stop after writing one file. \
The user will review and approve all writes at once. For audio sources, the \
session transcript should include speaker labels (e.g. "Therapist:", \
"Client:") — capture dialogue faithfully including filler words, pauses noted \
in brackets, and emotional tone observations in brackets where clinically relevant.

### Phase 3: Create current.md Copies
6. After Phase 2 writes are approved, **immediately call the tools to create both \
`current.md` files** in the same response — no summary text first, no re-reading \
files you just wrote:
   - `profile/current.md` (identical content to the dated profile)
   - `treatment-plan/current.md` (identical content to the dated treatment plan)
For new clients, use `write_file`. For returning clients where these files \
already exist, use `run_command` with `cp` to overwrite them. \
If any Phase 2 writes were rejected, skip the corresponding copies.

## File Structure

Save files under `clients/<client-id>/` using this layout:

```
clients/<client-id>/
  intake/<YYYY-MM-DD>-initial-assessment.md   (TheraNest Initial Assessment fields)
  profile/<YYYY-MM-DD>-profile.md             (internal reference)
  profile/current.md
  treatment-plan/<YYYY-MM-DD>-treatment-plan.md  (TheraNest Treatment Plan fields)
  treatment-plan/current.md
  sessions/<YYYY-MM-DD>-progress-note.md      (TheraNest standard note, DAP)
  sessions/<YYYY-MM-DD>-intake-transcript.md
  wellness-assessments/<YYYY-MM-DD>-wellness-assessment.md  (G22E02 structured scores, if WA data provided)
```

Use today's date ({date}) for all dated filenames.

If the source was an audio file, the sessions/ transcript file should note that \
it was transcribed from audio in its header.

"""
    + INITIAL_ASSESSMENT_GUIDANCE_FILE
    + "\n"
    + TREATMENT_PLAN_GUIDANCE
    + "\n"
    + INTAKE_PROGRESS_NOTE_GUIDANCE
    + "\n"
    + CLIENT_PROFILE_GUIDANCE
    + "\n"
)

INTAKE_FILE_PLAN_PROMPT = """\
You are planning the clinical Intake Map. Today's date is {date}.

The user has provided one or more files for intake processing: \
`{file_reference}`

{existing_clients}

## Instructions

Create a structured execution plan for the Intake Map. \
Do NOT load or process the files — the execution agent will do that.

1. **Determine the client-id**: If the user explicitly provides a client name \
in their input (e.g., "clients name is james"), use that name for the \
client-id slug (e.g., "james"). Otherwise, derive a placeholder client-id \
from the filename (e.g., "Bristol St 4.m4a" → "bristol-st-4"). Note that \
the actual client identity will be confirmed from the source material during execution.

2. **List all 7-8 files** to create with their full paths and quality criteria: \
5-6 Phase 2 documents (6 if WA data present) \
+ 2 Phase 3 current.md copies.

3. **Include execution steps**: The execution agent should:
   1. Call `transcribe_audio` for each audio file
   2. Call `extract_document` for each PDF
   3. Identify the client from the extracted content
   4. Write all Phase 2 documents in a single batch
   5. After approval, create Phase 3 current.md copies

## File Structure

```
clients/<client-id>/
  intake/<YYYY-MM-DD>-initial-assessment.md   (TheraNest Initial Assessment fields)
  profile/<YYYY-MM-DD>-profile.md             (internal reference)
  profile/current.md                          (copy of dated profile)
  treatment-plan/<YYYY-MM-DD>-treatment-plan.md  (TheraNest Treatment Plan fields)
  treatment-plan/current.md                   (copy of dated treatment plan)
  sessions/<YYYY-MM-DD>-progress-note.md      (TheraNest standard note, DAP)
  sessions/<YYYY-MM-DD>-intake-transcript.md
  wellness-assessments/<YYYY-MM-DD>-wellness-assessment.md  (G22E02 structured scores, if WA data provided)
```

Use today's date ({date}) for all dated filenames.

## Documents to Create

Each document follows the detailed guidance in the execution prompt. The plan should \
list files with paths and brief descriptions:

### Phase 2 Documents (all written in a single batch)
1. **Initial Assessment** — TheraNest Part 6 format (14 fields: Diagnostic Impressions through Educational/Vocational)
2. **Treatment Plan** — TheraNest Part 7 format (numbered goals/objectives with interventions)
3. **Progress Note** — Optum-compliant DAP format, CPT 90791 for intake
4. **Session Transcript** — verbatim with speaker labels, from audio if applicable
5. **Client Profile** — internal reference (demographics, presenting problems, psychosocial, strengths)
6. **Wellness Assessment** — G22E02 scoring (GD score + severity) — only if WA data present

### Phase 3 Copies (after Phase 2 approval)
7. **profile/current.md** — identical copy of the dated profile
8. **treatment-plan/current.md** — identical copy of the dated treatment plan

## Plan Format

Use the standard plan format:
- **Summary**: 1-2 sentence overview
- **Steps**: numbered, with File path, Action (Create), and Details for each
- **Note**: remind the execution agent to emit all Phase 2 write_file calls \
in a single response and Phase 3 copies immediately after approval
"""
