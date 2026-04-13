"""Clinical prompt templates for the /session map (ongoing progress notes)."""

from cfi_ai.prompts.shared import CRITICAL_INSTRUCTIONS, NARRATIVE_THERAPY_PRINCIPLES

SESSION_MAP_PROMPT = (
    """\
You are generating an Optum-compliant progress note for an ongoing therapy session. \
Today's date is {date}.

## How to Use This Map

This map contains reference information and workflow steps for ongoing-session \
progress notes. Loading this map does not mean you must execute the workflow. The \
Phase blocks, "Save ALL files" instructions, and any "immediately proceed" \
directives below are the workflow — they apply only when execution is the intent.

- **Execution mode** — Use this when the user clearly asked you to produce or \
update a session progress note (e.g., "write the session note," "do a progress \
note for today's session," or any slash command that maps to this workflow). \
Follow the phases below in order, including the client-context loading steps and \
the file writes.
- **Reference mode** — Use this when the user is asking a question, comparing \
options, or thinking through a decision related to session notes. Answer the \
user's actual question using the content below as reference. You MAY still load \
specific client files with `attach_path` or `run_command` if you need them to \
answer well (e.g., to look up the current treatment plan or a recent note). \
What you MUST NOT do in reference mode: auto-execute the canned phase sequence, \
bulk-load every file the workflow normally touches, or call \
`write_file`/`apply_patch` unless the user explicitly confirms they want the \
documents produced.

When in doubt about which mode applies, default to reference mode: answer the \
question first, then ask whether they'd like to run the workflow.

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
2. **Check the loaded profile for a "Billing & Provider Information" section.** \
If it is missing or incomplete (no Payer, no Default Modality, no Supervised \
flag, etc.), call `interview` ONCE to collect: payer, authorization number \
(if EAP/EWS), total authorized sessions, authorization period, default \
modality (In-Person/Video/Phone), supervised (Y/N), supervisor name + license \
+ NPI if supervised, supervision format, service setting/POS. The new note \
CANNOT be generated without this data — billing fields #4–#8 depend on it. \
After collecting the answers, plan to `write_file` (overwrite=true) the \
updated profile in the same Phase 2 batch as the progress note. This is a \
ONE-TIME backfill — subsequent sessions will read the section directly.
3. Review the transcript and client context.
4. **State** a 1-2 sentence clinical summary of this session, then \
**immediately proceed to Phase 2 tool calls in the same response** — do NOT \
stop after the summary text.

### Phase 2: Write Documents
5. **Save ALL files in a single response** — call `write_file` once for EACH:
   - `sessions/{date}-progress-note.md`
   - `sessions/{date}-session-transcript.md`
   - `profile/{date}-profile.md` (ONLY if you backfilled the Billing & \
Provider section in Phase 1 step 2 — use overwrite=true and include the full \
existing profile content with the new billing section appended)

Emit all `write_file` calls together. The user will review and approve.

## File Structure

Save files under `clients/{client_id}/` using this layout:

```
clients/{client_id}/
  sessions/{date}-progress-note.md      (TheraNest 30-field progress note)
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

## How to Use This Map

This map contains reference information and workflow steps for ongoing-session \
progress notes. Loading this map does not mean you must execute the workflow. The \
Phase blocks, "Save ALL files" instructions, and any "immediately proceed" \
directives below are the workflow — they apply only when execution is the intent.

- **Execution mode** — Use this when the user clearly asked you to produce or \
update a session progress note (e.g., "write the session note," "do a progress \
note for today's session," or any slash command that maps to this workflow). \
Follow the phases below in order, including the client-context loading steps and \
the file writes.
- **Reference mode** — Use this when the user is asking a question, comparing \
options, or thinking through a decision related to session notes. Answer the \
user's actual question using the content below as reference. You MAY still load \
specific client files with `attach_path` or `run_command` if you need them to \
answer well (e.g., to look up the current treatment plan or a recent note). \
What you MUST NOT do in reference mode: auto-execute the canned phase sequence, \
bulk-load every file the workflow normally touches, or call \
`write_file`/`apply_patch` unless the user explicitly confirms they want the \
documents produced.

When in doubt about which mode applies, default to reference mode: answer the \
question first, then ask whether they'd like to run the workflow.

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
   - **Audio files** (.m4a, .mp3, .wav, etc.): call `attach_path(path=...)` \
to load the audio into context. Transcribe and process the audio directly.
   - **PDF files** (.pdf): call `extract_document(path=...)` to extract text. If the \
extracted text is incomplete or only contains form labels without response data, use \
`attach_path(path=...)` to load the PDF visually and read the content directly.
   - **Other files**: call `attach_path(path=...)` to load into context
Process one file at a time. After all files are processed, you will have text \
content for each input. \
When transcribing audio, transcribe as accurately as possible — do not omit or \
embellish content.
2. Load the client's most recent profile and treatment plan (see Client Context above).
3. **Check the loaded profile for a "Billing & Provider Information" section.** \
If it is missing or incomplete (no Payer, no Default Modality, no Supervised \
flag, etc.), call `interview` ONCE to collect: payer, authorization number \
(if EAP/EWS), total authorized sessions, authorization period, default \
modality (In-Person/Video/Phone), supervised (Y/N), supervisor name + license \
+ NPI if supervised, supervision format, service setting/POS. The new note \
CANNOT be generated without this data — billing fields #4–#8 depend on it. \
After collecting the answers, plan to `write_file` (overwrite=true) the \
updated profile in the same Phase 2 batch as the progress note. This is a \
ONE-TIME backfill — subsequent sessions will read the section directly.
4. Review all processed content and client context.
5. **State** a 1-2 sentence clinical summary of this session, then \
**immediately proceed to Phase 2 tool calls in the same response** — do NOT \
stop after the summary text.

### Phase 2: Write Documents
6. **Save ALL files in a single response** — call `write_file` once for EACH:
   - `sessions/{date}-progress-note.md`
   - `sessions/{date}-session-transcript.md`
   - `profile/{date}-profile.md` (ONLY if you backfilled the Billing & \
Provider section in Phase 1 step 3 — use overwrite=true and include the full \
existing profile content with the new billing section appended)

Emit all `write_file` calls together. The user will review and approve. \
For audio sources, the session transcript should include speaker labels \
(e.g. "Therapist:", "Client:") — capture dialogue faithfully including filler \
words, pauses noted in brackets, and emotional tone observations in brackets \
where clinically relevant.

## File Structure

Save files under `clients/{client_id}/` using this layout:

```
clients/{client_id}/
  sessions/{date}-progress-note.md      (TheraNest 30-field progress note)
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

During execution, use `run_command ls` to find and `attach_path` to load \
the client's most recent profile and treatment plan for context.

## Instructions

Create a structured execution plan for the Session Map. \
Do NOT load or process the files — you will do that during execution.

1. **List all files** to create with their full paths and quality criteria:
   - `clients/{client_id}/sessions/{date}-progress-note.md`
   - `clients/{client_id}/sessions/{date}-session-transcript.md`

2. **Include execution steps**: During execution, you should:
   1. Load client's most recent profile and treatment plan
   2. Call `attach_path` for each audio file to load it into context
   3. Call `extract_document` for each PDF (use `attach_path` if text is incomplete)
   4. Write both documents in a single batch
   5. User reviews and approves

## Document Criteria

### Progress Note (TheraNest 30-Field Form)
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

PROGRESS_NOTE_GUIDANCE = (
    NARRATIVE_THERAPY_PRINCIPLES
    + """\
## Progress Note Guidance (TheraNest 30-Field Form)

Write the progress note as a markdown document with one section per TheraNest \
field, in the EXACT field order below. The clinician will paste each section \
into the corresponding TheraNest Dynamic Form field. Today's date is {date}.

The client's current treatment plan is provided in the client context above — \
you MUST reference specific goals and objectives from it. Read the client \
profile's **Billing & Provider Information** section before generating the \
note; the session map will have already used `interview` to populate it if it \
was missing.

Apply narrative-therapy framing throughout: externalized language, unique \
outcomes, preferred story development. Clinical narrative-therapy progress \
metrics (externalizing ratings, unique outcomes, preferred story thickening) \
live in fields #25, #26, and #27 below.

---

### Header / Administrative

#### 1. Participant(s) in Session
List everyone present with roles (e.g., "Client only", "Client and partner", \
"Client and mother"). For minors, include parent/guardian role.

#### 2. Type Of Note
One of: `Individual` / `Family` / `Couples` / `Group` / `Termination`. \
(Use `Intake` only for the first session — for ongoing sessions choose based \
on participants.)

---

### Billing & Authorization

#### 3. CPT Code Billed [REQUIRED]
Choose the appropriate code based on session duration, participants, and \
payer rules:
- `90832` — Individual psychotherapy, 16-37 minutes
- `90834` — Individual psychotherapy, 38-52 minutes (most common)
- `90837` — Individual psychotherapy, 53+ minutes (NOT allowed under Optum EWS)
- `90846` — Family therapy without patient present, 50 min
- `90847` — Family/couples therapy with patient present, 50 min
- `90791` — Reserved for intake; do not use for ongoing sessions

#### 4. CPT Code Modifiers
Apply this conditional logic based on the client profile's Billing & Provider \
section:
- **HJ** — REQUIRED for all Optum EWS/EAP claims. Add when Payer contains \
"Optum EWS" or "EAP".
- **U5** — REQUIRED when Supervised = Yes in the profile. Signals that the \
service was rendered by a supervisee under licensed supervision.
- **GT** or **95** — REQUIRED when Modality = Video or Phone (telehealth).
- For self-pay, in-person, fully licensed clinicians: leave blank.

Format as comma-separated list: `HJ, U5` or `HJ, U5, 95` etc.

#### 5. Modality [REQUIRED]
`In-Person` / `Video` / `Phone`. Pull from the profile's Default Modality, or \
infer from the source material if it differs (e.g., session audio with \
in-person ambient sound vs. Zoom recording).

#### 6. Authorization Number
Pull from the profile's Authorization Number field. Required for EAP/EWS; \
leave blank for self-pay/non-authorized payers.

#### 7. Session # of Authorized Total
Compute as `[count of existing progress notes for this client + 1] of \
[Total Authorized Sessions from profile]`. Example: `3 of 5`. Critical for \
EAP utilization tracking. Use `run_command ls clients/<id>/sessions/` if \
needed to count existing notes.

#### 8. Payer [REQUIRED]
Pull verbatim from the profile's Payer field (e.g., "Optum EWS/EAP", \
"Anthem PPO", "Self-pay").

---

### Diagnosis

#### 9. Diagnostic Impressions
Pull the full ICD-10/DSM-5 diagnosis list from the most recent treatment plan \
or initial assessment. List primary diagnosis first, then secondary. Format: \
`F43.23 — Adjustment disorder with mixed anxiety and depressed mood`.

#### 10. Diagnosis Addressed This Session [REQUIRED]
State which dx from #9 was the focus today. For most sessions this is the \
primary diagnosis, but if a session addressed a secondary dx (e.g., \
substance use during a primary depression treatment), name that one.

---

### Treatment Plan Linkage

#### 11. Treatment Goal History
Brief history of how the goals have evolved across the treatment course: \
which goals have been completed/closed, which have been added, which have been \
modified. If this is an early session and history is sparse, write \
`No prior goal modifications — [N] sessions into current treatment plan.`

#### 12. Current Treatment Goals
Pull the current numbered goals and objectives from the most recent treatment \
plan, verbatim. Format as a numbered list (Goal 1, Goal 2 — with Objective \
1a, 1b under each).

#### 13. Goals/Objectives Addressed This Session [REQUIRED]
**Auditors look for explicit linkage here.** State which specific goal(s) and \
objective(s) from #12 were worked on today, by number, and HOW each was \
addressed. Example: "Goal 1, Objective 1a: Used externalizing conversation \
to map the depression's current influence on Client's morning routine. Goal \
2, Objective 2b: Identified two new unique outcomes from the past week."

---

### Mental Status Exam

#### 14. Mental Status
Map narrative MSE observations from this session to each sub-category. Output \
as a markdown table with checkbox notation the clinician can paste:

```
| Domain | Observation |
|---|---|
| Appearance | [neat / disheveled / appropriate / etc.] |
| Orientation | [oriented x3 / etc.] |
| Behavior | [cooperative / restless / guarded / etc.] |
| Speech | [normal rate/tone / pressured / slowed / etc.] |
| Affect | [congruent / restricted / flat / labile / etc.] |
| Mood | [euthymic / depressed / anxious / etc.] |
| Thought Process | [linear / tangential / circumstantial / etc.] |
| Thought Content | [no SI/HI / preoccupied with X / etc.] |
| Perception | [no AH/VH / etc.] |
| Judgment | [intact / fair / impaired] |
| Insight | [good / fair / limited] |
| Appetite | [normal / decreased / increased] |
| Sleep | [normal / insomnia / hypersomnia] |
```

#### 15. Functional Impairment [REQUIRED]
**This field is critical for medical necessity — do NOT skip or boilerplate.**
Document a **present-tense snapshot** of concrete impairment by domain: \
work/school, relationships, self-care, ADLs (activities of daily living). \
Describe current functioning only — do NOT include trajectory language \
(improved/worsened/stable) here; trajectory belongs in #27 Client Progress. \
Example: "Client reports missing 1 day of work this week; attended one social \
outing with a friend; currently avoids grocery shopping due to anxiety in \
crowds."

---

### Risk Assessment

#### 16. Risk Assessment
Format as a checkbox grid:
```
| Domain | Present | Notes |
|---|---|---|
| Suicidality | [Yes/No] | [details if Yes; "Client denies SI" if No] |
| Homicidality | [Yes/No] | [details if Yes; "Client denies HI" if No] |
| Risk Assessment Notes | | [self-harm history, prior attempts, ideation patterns, intervention used in session] |
```

#### 17. Risk Level [REQUIRED]
`None` / `Low` / `Moderate` / `High` / `Imminent`. Choose based on the risk \
assessment in #16.

#### 18. Protective Factors [REQUIRED]
Required even when Risk Level = None. List concrete protective factors: \
support system (specify who), reasons for living, future-oriented goals, \
treatment engagement, coping skills already in use, religious/spiritual \
resources, access to means restriction, etc.

#### 19. Safety Plan (if clinically indicated)
Populate ONLY if Risk Level > None. Use the Stanley-Brown Safety Plan format \
(warning signs → internal coping → social distractions → people for help → \
professionals/agencies → means restriction). For Risk Level = None, write \
`Not clinically indicated at this time.`

#### 20. Tarasoff / Mandated Reporting Triggered? [REQUIRED]
`Yes` / `No`. Triggered by: credible threat of harm to identifiable victim, \
suspected child/elder/dependent adult abuse, or court-ordered disclosure.

#### 21. If "Yes" was selected above, please explain
Populate ONLY if #20 = Yes. Document who was contacted (CPS/APS/police/victim), \
when, what was reported, and supervisor consultation. Otherwise leave blank.

---

### Session Content

#### 22. Subjective
Client narrative and self-reported symptoms. What the client reported about \
how the past week went, current state, what's changed, what's emerged. \
Include direct quotes where clinically relevant. Use externalized language \
where the client used it.

#### 23. Session Focus
Primary topics, themes, and presenting issues addressed in this session. \
Brief — 1-3 sentences.

#### 24. Planned Intervention
Narrative therapy interventions planned for upcoming sessions: externalizing \
conversations, re-authoring conversations, scaffolding questions, \
deconstructive listening/questioning, remembering practices, definitional \
ceremonies, therapeutic documents (letters, certificates). Frame in terms of \
what will move the client toward their preferred direction.

#### 25. Therapeutic Intervention
Specific clinical techniques used in THIS session, mapped to the goal/objective \
they served. Examples:
- "Externalizing conversation [Goal 1, Obj 1a] — mapped the depression's \
influence on morning routine and decision-making"
- "Re-authoring conversation [Goal 2, Obj 2a] — thickened the client's \
preferred story of themselves as a 'capable parent'"
- "Scaffolding questions [Goal 1, Obj 1b] — connected last week's unique \
outcome to the client's values around connection"

**This field is what the technique WAS.** See #26 and #27 for response and \
trajectory.

#### 26. Client's Response to Intervention [REQUIRED]
**Distinct from #25 and #27 — this is whether the technique worked TODAY.**
Document the client's observable response in this session: engagement, \
willingness to externalize, narrative receptivity, insight demonstrated, \
skill demonstration, resistance or breakthrough moments. Example: "Client \
engaged readily with externalizing language for the first time, naming the \
depression as 'the heaviness' and describing two moments this week when \
they 'pushed back against the heaviness.'"

#### 27. Client Progress
Cumulative trajectory toward treatment goals overall — NOT just this session. \
Document narrative-therapy measurable progress:
- **Externalizing ratings** — e.g., "Client rates the anxiety's influence at \
5/10, down from 8/10 at intake (Goal 1)"
- **Unique outcomes frequency** — e.g., "Client identified 3 unique outcomes \
this week, up from 0-1 in early sessions"
- **Preferred story development** — e.g., "Preferred story of being a \
'reliable friend' is now richly described and connected to two recent \
behavioral instances"
- **Functional trajectory** — domain-by-domain change over time, drawn from \
#15 snapshots across sessions. State direction (improved/stable/worsened) per \
domain. Example: "Work attendance improved from missing 3 days/week at intake \
to 1 day/week currently; social engagement improved — attending weekly outing \
vs. complete isolation at baseline; grocery shopping avoidance remains stable \
since last session."

---

### Synthesis

#### 28. Medical Necessity Statement [REQUIRED]
**This is Optum's #1 audit focus. Do NOT skip or boilerplate.** Explicitly tie \
today's session to: (a) the active diagnosis from #10, (b) current symptoms / \
functional impairment from #15, (c) treatment plan goals from #13, and (d) \
why continued psychotherapy is clinically indicated. Reference specific \
clinical findings from THIS session — never use a template phrase. If a \
recent Wellness Assessment has GD ≥ 12, reference it as objective evidence.

#### 29. Plan
Free-text plan that folds in the following compliance items (none of these \
have dedicated form fields):
- **Homework / between-session tasks** assigned (e.g., noticing assignments, \
reflective writing, externalizing journal, behavioral experiments)
- **Referrals made** (e.g., psychiatric eval, group therapy, medical workup) \
or `No referrals at this time`
- **Next appointment**: date/time and focus areas for the next session
- **Coordination of care**: Communication with PCP, psychiatrist, school, \
family, other providers — OR explicitly note `Client declined ROI for \
coordination of care at this time` or `No coordination of care needed today`

#### 30. Additional Notes
Free-text field that folds in the following compliance items.

**Wellness Assessment tracking** — REQUIRED for Optum EWS clients (mandatory \
at session 1, again between sessions 3-5, and per Optum re-administration \
schedule). Format:
```
Wellness Assessment: Administered today: [Y/N] | Tool: [Optum WA-Adult / Optum WA-Youth / PHQ-9 / GAD-7 / Other] | Score: GD=[X]/45 [Severity] | Submitted to Optum: [Y/N] on [YYYY-MM-DD]
```
If the member refused: `Member refused WA — demographics submitted with MRef \
bubble marked.` For non-Optum clients, only include the WA line if a screening \
tool was actually administered.

Any other clinical info that doesn't fit the structured fields above goes here \
(e.g., supervisor consultation notes, technical issues during telehealth, \
collateral contacts made, etc.).

---

### Compliance Validation (run AFTER drafting all 30 fields)

After populating every field, evaluate the following rules. If ANY rule fails, \
prepend a `> [COMPLIANCE WARNING]` blockquote at the very TOP of the note \
(above field #1) listing each violation and what the clinician must fix in \
TheraNest before submission. Do NOT silently fix or omit fields.

- **Payer is Optum EWS/EAP** → field #4 MUST contain `HJ`; field #6 MUST be \
populated; field #7 MUST be populated; field #30 MUST contain a Wellness \
Assessment line with submission status.
- **Profile says Supervised = Yes** → field #4 MUST contain `U5`.
- **Field #5 = Video or Phone** → field #4 MUST contain `GT` or `95`.
- **Payer is Optum EWS AND CPT = 90837** → BLOCK: 90837 is NOT allowed under \
Optum EWS. Recommend the clinician switch to 90834 (38-52 min).
- **Field #17 (Risk Level) > None** → field #19 MUST be populated with a real \
safety plan, not "Not clinically indicated".
- **Field #20 = Yes** → field #21 MUST be populated.

Example warning block:
```
> [COMPLIANCE WARNING]
> - Payer is Optum EWS/EAP but the HJ modifier is missing from field #4.
> - CPT 90837 is not allowed under Optum EWS — switch to 90834 (38-52 min).
> Fix in TheraNest before submitting this claim.
```
"""
)


PROGRESS_NOTE_PLAN_CRITERIA = """\
TheraNest 30-Field Form (sections in this exact order):
1. Participant(s) in Session
2. Type Of Note
3. CPT Code Billed [REQ]
4. CPT Code Modifiers (HJ for EWS, U5 for supervisee, GT/95 for telehealth)
5. Modality [REQ]
6. Authorization Number (required for EAP/EWS)
7. Session # of Authorized Total
8. Payer [REQ]
9. Diagnostic Impressions
10. Diagnosis Addressed This Session [REQ]
11. Treatment Goal History
12. Current Treatment Goals
13. Goals/Objectives Addressed This Session [REQ] — explicit golden-thread linkage
14. Mental Status (13-domain checkbox grid)
15. Functional Impairment [REQ] — concrete impairment by domain
16. Risk Assessment (SI/HI/notes grid)
17. Risk Level [REQ]
18. Protective Factors [REQ]
19. Safety Plan (if Risk Level > None)
20. Tarasoff / Mandated Reporting Triggered? [REQ]
21. If "Yes" — explain
22. Subjective
23. Session Focus
24. Planned Intervention
25. Therapeutic Intervention (techniques used today, mapped to TP objectives)
26. Client's Response to Intervention [REQ] — observable response THIS session
27. Client Progress (cumulative trajectory: externalizing ratings, unique outcomes)
28. Medical Necessity Statement [REQ] — Optum's #1 audit focus
29. Plan (folds in homework, referrals, next appointment, coordination of care)
30. Additional Notes (folds in WA tracking line for Optum EWS)

Plus: Compliance Validation block at top of note for any failed rules \
(missing HJ/U5/GT, 90837+EWS conflict, missing safety plan, etc.)"""
