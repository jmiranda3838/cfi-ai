"""Clinical prompt templates for the /intake map."""

from cfi_ai.prompts.client_profile import CLIENT_PROFILE_GUIDANCE
from cfi_ai.prompts.initial_assessment import INITIAL_ASSESSMENT_TEMPLATE
from cfi_ai.prompts.narrative_therapy import NARRATIVE_THERAPY_ORIENTATION
from cfi_ai.prompts.progress_note import PROGRESS_NOTE_GUIDANCE
from cfi_ai.prompts.shared import CRITICAL_INSTRUCTIONS
from cfi_ai.prompts.treatment_plan import TREATMENT_PLAN_GUIDANCE

INTAKE_PROMPT = (
    """\
You are conducting a clinical intake assessment. Today's date is {date}.

"""
    + CRITICAL_INSTRUCTIONS
    + """
## Processing Intake Inputs

The intake map typically involves some combination of:
- **Session audio** (.m4a, .mp3, .wav, etc.) — the recorded intake session
- **Intake questionnaire** (PDF) — client-completed intake form
- **Intake assessment instrument** (PDF or paper scan) — payer-specific. \
The active payer's rules say which instrument applies and how to score it.
- **Other assessments** (PDFs, images)
- **Pasted transcript** — session transcript already in the conversation

Inspect what the user has provided and process each accordingly:

- **File paths**: extract each path from the user's input. If a path contains \
shell escape characters (backslashes before spaces, quotes), interpret them \
as a shell would — e.g. `Bristol\\ St\\ 4.m4a` means `Bristol St 4.m4a`.
  - Audio files (.m4a, .mp3, .wav, etc.): `attach_path(path=...)` to load \
into context, then transcribe directly.
  - PDF files (.pdf): `extract_document(path=...)` for text. If the extracted \
text only contains form labels without response data, fall back to \
`attach_path(path=...)` to read the PDF visually.
  - Other files: `attach_path(path=...)`.
  Process one file at a time. After processing, you'll have text content for \
each input.
- **Pasted transcript or response text**: use it directly as the intake content.
- **Nothing provided yet**: call `interview` alone to ask what intake materials \
the user has (session recording, questionnaire PDF, intake assessment \
instrument) and where the files are located. Do not proceed to client \
identification or document writing until you have materials.

When transcribing audio, transcribe as accurately as possible — do not omit or \
embellish content.

## Map

### Phase 1: Resolve Payer, Process Input, Identify & Summarize
1. **Resolve the payer FIRST.** Before generating any document, identify the \
client's payer from the intake materials (insurance card photo, completed \
intake questionnaire, or text the user pasted). Map the payer name to a slug:
   - `"Optum EWS/EAP"` or `"Optum EAP"` → `optum-eap`
   - `"Aetna"` → `aetna`
   - `"Evernorth"` → `evernorth`
   If you cannot determine the payer from the materials, call `interview` \
ONCE to ask the user — do NOT guess. Then call `load_payer_rules(payer=<slug>)` \
exactly once. The returned rules govern CPT-code selection, modifier flags, \
authorization fields, and any required intake assessment instrument for the \
rest of this workflow.
2. **Process all intake input** per the "Processing Intake Inputs" section above.
3. **Identify the client**: If the user explicitly provides a client name \
in their input, use that name for the `client-id` slug. Otherwise, identify \
the client from the session content. Generate a `client-id` slug \
(lowercase, hyphenated — e.g. "jane-doe").
4. **Check existing clients** — use `run_command ls clients/` to see existing \
client IDs. If this client matches an existing ID, use `run_command ls` to find \
the most recent files in `clients/<client-id>/profile/` and \
`clients/<client-id>/treatment-plan/` (latest `YYYY-MM-DD` prefix), then \
`attach_path` to load them for context.
5. **State** the client name and a 1-2 sentence clinical summary, then \
**immediately proceed to Phase 2 tool calls in the same response** — do NOT \
stop after the summary text.

### Phase 2: Write Documents
6. **Save ALL files in a single response** — call `write_file` once for EACH of \
these 5 documents (plus 1 more if the active payer requires an intake \
assessment instrument and the client provided one) in the same turn:
   - `clients/<client-id>/intake/{date}-initial-assessment.md`
   - `clients/<client-id>/treatment-plan/{date}-treatment-plan.md`
   - `clients/<client-id>/sessions/{date}-progress-note.md`
   - `clients/<client-id>/sessions/{date}-intake-transcript.md`
   - `clients/<client-id>/profile/{date}-profile.md`
   - `clients/<client-id>/wellness-assessments/{date}-wellness-assessment.md` \
(ONLY if the active payer's rules describe a required intake assessment \
instrument AND the client provided one — see the loaded payer rules for \
scoring and structure)

Emit all `write_file` calls together. Do NOT stop after writing one file. \
The user will review and approve all writes at once. For audio sources, the \
session transcript should include speaker labels (e.g. "Therapist:", \
"Client:") — capture dialogue faithfully including filler words, pauses noted \
in brackets, and emotional tone observations in brackets where clinically relevant.

## File Structure

Save files under `clients/<client-id>/` using this layout:

```
clients/<client-id>/
  intake/<YYYY-MM-DD>-initial-assessment.md   (TheraNest Initial Assessment fields)
  profile/<YYYY-MM-DD>-profile.md             (internal reference, includes Billing & Provider section)
  treatment-plan/<YYYY-MM-DD>-treatment-plan.md  (TheraNest Treatment Plan fields)
  sessions/<YYYY-MM-DD>-progress-note.md      (TheraNest 30-field progress note)
  sessions/<YYYY-MM-DD>-intake-transcript.md
  wellness-assessments/<YYYY-MM-DD>-wellness-assessment.md  (structured scores per the active payer's rules, if applicable)
```

Use today's date ({date}) for all dated filenames.

If the source was an audio file, the sessions/ transcript file should note that \
it was transcribed from audio in its header.

The client profile MUST include a populated "Billing & Provider Information" \
section. If the intake materials don't supply payer/authorization/supervisor \
data directly (which is common — these come from the intake paperwork rather \
than the session itself), use `interview` to collect them from the user before \
writing the profile and progress note.

"""
    + NARRATIVE_THERAPY_ORIENTATION
    + "\n"
    + INITIAL_ASSESSMENT_TEMPLATE
    + "\n"
    + TREATMENT_PLAN_GUIDANCE
    + "\n"
    + PROGRESS_NOTE_GUIDANCE
    + "\n"
    + CLIENT_PROFILE_GUIDANCE
    + "\n"
)
