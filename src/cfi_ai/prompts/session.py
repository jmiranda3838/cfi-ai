"""Clinical prompt templates for the /session map (ongoing progress notes)."""

from cfi_ai.prompts.shared import CRITICAL_INSTRUCTIONS

SESSION_MAP_PROMPT = (
    """\
You are generating an Optum-compliant progress note for an ongoing therapy session. \
Today's date is {date}.

"""
    + CRITICAL_INSTRUCTIONS
    + """
<transcript>
{transcript}
</transcript>

## Client Context

Client ID: `{client_id}`

Use `run_command ls clients/{client_id}/profile/` and \
`run_command ls clients/{client_id}/treatment-plan/` to find the most recent \
files (latest `YYYY-MM-DD` prefix), then `attach_path` to load them.

## Map

### Phase 1: Load Context & Summarize
1. Load the client's most recent profile and treatment plan (see above).
2. Review the transcript and client context.
2. **State** a 1-2 sentence clinical summary of this session, then \
**immediately proceed to Phase 2 tool calls in the same response** — do NOT \
stop after the summary text.

### Phase 2: Write Documents
3. **Save ALL files in a single response** — call `write_file` once for EACH:
   - `sessions/{date}-progress-note.md`
   - `sessions/{date}-session-transcript.md`

Emit both `write_file` calls together. The user will review and approve.

## File Structure

Save files under `clients/{client_id}/` using this layout:

```
clients/{client_id}/
  sessions/{date}-progress-note.md      (Optum-compliant TheraNest note, DAP)
  sessions/{date}-session-transcript.md  (verbatim transcript)
```

{progress_note_guidance}

## Session Transcript

Save the transcript verbatim with a brief header noting the date and session type.
"""
)

SESSION_FILE_MAP_PROMPT = (
    """\
You are generating an Optum-compliant progress note for an ongoing therapy session \
based on one or more files provided by the user. Today's date is {date}.

"""
    + CRITICAL_INSTRUCTIONS
    + """
The user wants to process a session from one or more files. The input is: \
`{file_reference}`

### Expected Inputs
- **Session audio** (.m4a, .mp3, .wav, etc.) — the recorded session
- **Other files** (PDFs, images) — any additional session-related documents

Extract each file path from the input. If the input looks like raw transcript \
text rather than file paths, treat it as the transcript directly and skip the \
file-loading step.

If the path contains shell escape characters (backslashes before spaces, quotes, \
etc.), interpret them as a shell would — e.g. `Bristol\\ St\\ 4.m4a` means \
`Bristol St 4.m4a`.

## Client Context

Client ID: `{client_id}`

Use `run_command ls clients/{client_id}/profile/` and \
`run_command ls clients/{client_id}/treatment-plan/` to find the most recent \
files (latest `YYYY-MM-DD` prefix), then `attach_path` to load them.

## Map

### Phase 1: Process Input Files & Summarize
1. **Process files** step by step using the appropriate tool for each:
   - **Audio files** (.m4a, .mp3, .wav, etc.): call `transcribe_audio(path=...)` \
to get a text transcript
   - **PDF files** (.pdf): call `extract_document(path=...)` to extract text/data
   - **Other files**: call `attach_path(path=...)` to load into context
Process one file at a time. After all files are processed, you will have text \
content for each input. \
When transcribing audio, transcribe as accurately as possible — do not omit or \
embellish content.
2. Load the client's most recent profile and treatment plan (see Client Context above).
3. Review all processed content and client context.
4. **State** a 1-2 sentence clinical summary of this session, then \
**immediately proceed to Phase 2 tool calls in the same response** — do NOT \
stop after the summary text.

### Phase 2: Write Documents
5. **Save ALL files in a single response** — call `write_file` once for EACH:
   - `sessions/{date}-progress-note.md`
   - `sessions/{date}-session-transcript.md`

Emit both `write_file` calls together. The user will review and approve. \
For audio sources, the session transcript should include speaker labels \
(e.g. "Therapist:", "Client:") — capture dialogue faithfully including filler \
words, pauses noted in brackets, and emotional tone observations in brackets \
where clinically relevant.

## File Structure

Save files under `clients/{client_id}/` using this layout:

```
clients/{client_id}/
  sessions/{date}-progress-note.md      (Optum-compliant TheraNest note, DAP)
  sessions/{date}-session-transcript.md  (verbatim or transcribed session)
```

If the source was an audio file, the sessions/ transcript file should note that \
it was transcribed from audio in its header.

{progress_note_guidance}
"""
)

SESSION_FILE_PLAN_PROMPT = """\
You are planning the Session Map. Today's date is {date}.

The user has provided one or more files for session processing: \
`{file_reference}`

Client ID: `{client_id}`

The execution agent should use `run_command ls` to find and `attach_path` to load \
the client's most recent profile and treatment plan for context.

## Instructions

Create a structured execution plan for the Session Map. \
Do NOT load or process the files — the execution agent will do that.

1. **List all files** to create with their full paths and quality criteria:
   - `clients/{client_id}/sessions/{date}-progress-note.md`
   - `clients/{client_id}/sessions/{date}-session-transcript.md`

2. **Include execution steps**: The execution agent should:
   1. Load client's most recent profile and treatment plan
   2. Call `transcribe_audio` for each audio file
   3. Call `extract_document` for each PDF
   4. Write both documents in a single batch
   5. User reviews and approves

## Document Criteria

### Progress Note (Optum-Compliant, DAP Format)
{progress_note_plan_criteria}

### Session Transcript
- Speaker labels (e.g. "Therapist:", "Client:")
- Capture dialogue faithfully including filler words
- Pauses noted in brackets, emotional tone observations where clinically relevant
- Header noting date, session type, and source (audio transcription or text)

## Plan Format

Use the standard plan format:
- **Summary**: 1-2 sentence overview
- **Steps**: numbered, with File path, Action (Create), and Details for each
"""

# -- Shared Optum-compliant progress note guidance --

PROGRESS_NOTE_GUIDANCE = """\
## Progress Note Guidance (Optum-Compliant, DAP Format)

Write a progress note for this session using TheraNest's standard note fields. \
The client's current treatment plan is provided in the client context above — \
you MUST reference specific goals and objectives from it. Clearly note when \
information is absent or was not assessed.

### Required Fields

- **Date of Service** — {date}
- **Service Code** — Determine the appropriate CPT code based on session duration \
and type. Common codes:
  - 90834: Individual psychotherapy, 38-52 minutes
  - 90837: Individual psychotherapy, 53+ minutes
  - 90847: Family/couples therapy with patient present
  - 90846: Family therapy without patient present
- **Session Duration** — Total session time in minutes. Must support the CPT \
code (e.g., 90837 requires ≥53 minutes face-to-face).
- **Participants in Session** — All individuals present with roles.
- **Supervision** — "Session conducted under the supervision of [supervisor \
name], [license type] #[license number]." Note supervision format (live \
observation, recording review, or individual supervision discussion).

- **Risk Assessment** —
  - Suicidal ideation: present / not present
  - Homicidal ideation: present / not present
  - Self-harm: present / not present
  - If any present: detail (passive/active, plan, means, intent) and \
document intervention/safety plan
  - If none: "Client denied suicidal ideation, homicidal ideation, and \
self-harm."

- **Medication Changes** — Changes reported or "No changes reported. \
Current medications: [list if known from profile]."

- **Treatment Plan Goals Addressed** — List the specific goal(s) and \
objective(s) from the treatment plan that were addressed in this session, \
by name and number (e.g., "Goal 1: Reduce anxiety; Objective 1a: Identify \
cognitive distortions").

- **Session Summary (DAP Format)**:
  - **D (Data):** Client self-report and objective observations. What the \
client reported, issues discussed, relevant quotes, behavioral observations \
(affect, appearance, engagement). If Wellness Assessment (G22E02) was \
administered, document: GD score [X/45], severity level \
[Low/Moderate/Severe/Very Severe], and CAGE-AID result [Negative/Positive \
(N/3)] if initial. Example: "Wellness Assessment (G22E02) re-administered: \
Global Distress = 18/45 (Moderate), down from 28/45 (Severe) at baseline."
  - **A (Assessment):** Clinical impressions. For each treatment plan goal \
addressed: document specific, measurable progress or lack of progress \
(e.g., frequency changes, severity ratings, behavioral milestones). \
Note functional status across domains (work, relationships, self-care). \
Identify emerging themes and patterns.
  - **P (Plan):** Specific interventions used this session and which TP \
objective they address (e.g., "Used cognitive restructuring [Goal 1, \
Obj 1a] to challenge catastrophic thinking"). Between-session tasks \
or homework assigned. Referrals made or needed.

- **Strengths & Barriers** — Client strengths that supported progress this \
session. Limitations or barriers encountered in working toward treatment \
plan goals.

- **Medical Necessity** — Brief justification for continued treatment: \
ongoing symptoms, functional impairment, client engagement, and progress \
trajectory. Why this level of care remains appropriate.

- **Next Appointment** — Date and specific focus areas for next session."""


PROGRESS_NOTE_PLAN_CRITERIA = """\
- Date of service, CPT code, session duration
- Participants in session with roles
- Supervision line (required for AMFTs)
- Structured risk assessment: SI, HI, self-harm (present/not present; details if present)
- Medication changes or "No changes"
- Treatment plan goals addressed by name and number
- DAP format: D (client report + observations), A (measurable progress per goal), \
P (interventions mapped to TP objectives + homework + referrals)
- Strengths & barriers
- Medical necessity justification
- Next appointment date and focus"""
