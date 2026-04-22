"""Progress note guidance — single source of truth for both ongoing and intake variants."""

from cfi_ai.prompts.narrative_therapy import NARRATIVE_THERAPY_PRINCIPLES

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

INTAKE_PROGRESS_NOTE_GUIDANCE = """\
## Progress Note Guidance (TheraNest 30-Field Form — Intake Session)

Write the intake progress note as a markdown document with one section per \
TheraNest field, in the EXACT field order below. The clinician will paste each \
section into the corresponding TheraNest Dynamic Form field. Today's date is \
{date}.

This is an intake session — treatment plan goals are being **established**, \
not tracked. CPT code is hardcoded to 90791. The Wellness Assessment is \
ALWAYS administered at intake (Optum EWS requirement at session 1).

Read the client profile's **Billing & Provider Information** section before \
generating the note. If that section is missing, the session map will have \
already used `interview` to populate it before reaching this step.

---

### Header / Administrative

#### 1. Participant(s) in Session
List everyone present with roles (e.g., "Client only", "Client and partner", \
"Client and therapist"). For minors, include parent/guardian role.

#### 2. Type Of Note
`Intake`

---

### Billing & Authorization

#### 3. CPT Code Billed [REQUIRED]
`90791` (Psychiatric Diagnostic Evaluation) — hardcoded for intake sessions \
regardless of duration.

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
Compute as `[count of existing progress notes for this client] + 1` of \
[Total Authorized Sessions from profile]. For intake, this is typically \
"1 of 5" or "1 of 10". Critical for EAP utilization tracking.

#### 8. Payer [REQUIRED]
Pull verbatim from the profile's Payer field (e.g., "Optum EWS/EAP", \
"Anthem PPO", "Self-pay").

---

### Diagnosis

#### 9. Diagnostic Impressions
Pull the full ICD-10/DSM-5 diagnosis list from this intake session's Initial \
Assessment document. List primary diagnosis first, then secondary diagnoses. \
Format: `F43.23 — Adjustment disorder with mixed anxiety and depressed mood`.

#### 10. Diagnosis Addressed This Session [REQUIRED]
For an intake, the primary diagnosis established in field #9. State which dx \
was the focus of the assessment (typically the primary).

---

### Treatment Plan Linkage

#### 11. Treatment Goal History
`N/A — initial intake; no prior treatment goals on record.`

#### 12. Current Treatment Goals
`Established this session — see treatment plan document for full numbered \
goals and objectives.`

#### 13. Goals/Objectives Addressed This Session [REQUIRED]
`Baseline assessment — treatment plan goals established this session.` Then \
list the goals and objectives created during intake by number for future \
session linkage (e.g., "Goal 1: Reduce the influence of the anxiety on daily \
functioning. Objective 1a: Externalize the anxiety and map its effects.").

---

### Mental Status Exam

#### 14. Mental Status
Map narrative MSE observations from the session to each sub-category. Output \
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
For intake, document baseline impairment across domains: work/school, \
relationships, self-care, ADLs (activities of daily living). Be specific and \
concrete (e.g., "Client reports missing 3 days of work in past 2 weeks due to \
anxiety; has stopped attending weekly social gatherings; reports difficulty \
cooking and grocery shopping due to fatigue from depression").

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
For intake, also include the CAGE-AID screen result if administered: \
`CAGE-AID: [Negative / Positive (N/3)]` — this satisfies the substance use \
risk domain.

#### 17. Risk Level [REQUIRED]
`None` / `Low` / `Moderate` / `High` / `Imminent`. Choose based on the risk \
assessment in #16. For most stable intake clients without active SI/HI, this \
will be `None` or `Low`.

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
suspected child/elder/dependent adult abuse, or court-ordered disclosure. \
For most intake sessions this is `No`.

#### 21. If "Yes" was selected above, please explain
Populate ONLY if #20 = Yes. Document who was contacted (CPS/APS/police/victim), \
when, what was reported, and supervisor consultation. Otherwise leave blank.

---

### Session Content

#### 22. Subjective
Client narrative and self-report. What the client reported about their \
presenting issues, history of the problem, prior treatment, current symptoms, \
and what brought them in now. Include direct quotes where clinically relevant. \
Use externalized language where the client used it (e.g., "Client describes \
the depression as 'something that pulls me under'").

#### 23. Session Focus
Primary topics, themes, and presenting issues addressed in the intake. For \
intake this is typically: history-taking, presenting problem exploration, \
externalizing introduction, risk screening, baseline functioning assessment, \
preferred direction.

#### 24. Planned Intervention
Narrative therapy interventions planned for upcoming sessions: externalizing \
conversations, re-authoring conversations, scaffolding questions, \
deconstructive listening/questioning, remembering practices, definitional \
ceremonies, therapeutic documents (letters, certificates). Frame in terms of \
the client's preferred direction.

#### 25. Therapeutic Intervention
Specific clinical techniques used in THIS intake session. For intake, this \
typically includes: diagnostic interview, biopsychosocial assessment, \
narrative therapy stance-taking, externalizing introduction, Wellness \
Assessment administration, risk assessment, treatment planning collaboration. \
Be specific.

#### 26. Client's Response to Intervention [REQUIRED]
**Distinct from #27 — this is whether the intake interventions worked TODAY.**
Document the client's observable response to the intake process: engagement \
level, willingness to externalize the problem, narrative receptivity, comfort \
with the structure, insight demonstrated, areas of resistance or difficulty.

#### 27. Client Progress
For intake: `Baseline established this session.` Briefly note the starting \
point (e.g., "Baseline GD = 28/45 Severe; baseline externalizing rating: \
client rates the depression's influence at 9/10").

---

### Synthesis

#### 28. Medical Necessity Statement [REQUIRED]
**This is Optum's #1 audit focus. Do NOT skip or boilerplate.** Explicitly tie \
today's intake to: (a) the active diagnosis from #10, (b) current symptoms / \
functional impairment from #15, (c) treatment plan goals being established in \
#13, and (d) why ongoing psychotherapy is clinically indicated. Reference \
specific clinical findings from this session — never use a template phrase. \
For intake, baseline GD score ≥ 12 supports medical necessity as objective \
evidence of clinically significant distress.

#### 29. Plan
Free-text plan that folds in the following compliance items (none of these \
have dedicated form fields):
- **Homework / between-session tasks** assigned (e.g., noticing assignments, \
reflective writing about preferred outcomes, externalizing journal)
- **Referrals made** (e.g., psychiatric eval, group therapy, medical workup) \
or `No referrals at this time`
- **Next appointment**: date/time and focus areas for the next session
- **Coordination of care**: Communication with PCP, psychiatrist, school, \
family, prior providers — OR explicitly note `Client declined ROI for \
coordination of care at this time` or `No coordination of care needed today`

#### 30. Additional Notes
Free-text field that folds in the following compliance items.

**Wellness Assessment tracking** — REQUIRED for Optum EWS clients (and \
ALWAYS at intake, since the initial WA is mandatory at session 1). Format:
```
Wellness Assessment: Administered today: Y | Tool: Optum WA-Adult (G22E02) | Score: GD=[X]/45 [Severity]; CAGE-AID=[N]/3 [Negative/Positive] | Submitted to Optum: [Y/N] on [YYYY-MM-DD]
```
If the member refused: `Member refused WA — demographics submitted with MRef \
bubble marked.` For non-Optum clients, only include the WA line if a screening \
tool was actually administered.

Any other clinical info that doesn't fit the structured fields above goes here \
(e.g., notable observations about narrative receptivity, supervisor \
consultation notes, technical issues during telehealth, etc.).

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
- **Payer is Optum EWS AND CPT = 90837** → BLOCK: 90837 is not allowed under \
Optum EWS. (Intake is always 90791, so this should never trigger for intake \
notes — but flag it loudly if it somehow does.)
- **Field #17 (Risk Level) > None** → field #19 MUST be populated with a \
real safety plan.
- **Field #20 = Yes** → field #21 MUST be populated.

Example warning block:
```
> [COMPLIANCE WARNING]
> - Payer is Optum EWS/EAP but the HJ modifier is missing from field #4.
> - Authorization Number (#6) is blank — Optum EWS requires this populated.
> Fix in TheraNest before submitting this claim.
```
"""
