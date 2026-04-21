"""Shared clinical specification blocks used across prompt templates."""


def indent_block(text: str, prefix: str) -> str:
    """Prefix each non-empty line of ``text`` with ``prefix``.

    Used to nest a multi-line block (like the TheraNest intervention master
    list) cleanly underneath a Markdown bullet that requires a specific indent.
    """
    return "\n".join(f"{prefix}{line}" if line else line for line in text.splitlines())


CRITICAL_INSTRUCTIONS = """\
## When Executing This Workflow

The rules below apply only when you are actively producing the documents this map \
describes. If the user is asking a question, comparing options, or thinking through \
a decision, treat the rest of this map as reference material and answer their \
question normally — ignore these execution rules.

- Do NOT narrate the map or reproduce document content in your response text.
- Keep free-text responses to 2-3 sentences maximum. Proceed directly to tool calls.
- The user reviews all file content in the approval step — do not preview it in chat.
"""

NARRATIVE_THERAPY_PRINCIPLES = """\
## Therapeutic Orientation: Narrative Therapy

This clinician practices narrative therapy. All clinical documentation must reflect \
narrative therapy principles and language:

- **Externalization**: The problem is separate from the person. Use language that \
positions problems as external entities the client has a relationship with (e.g., \
"the anxiety," "the depression's influence," "the conflict") rather than traits \
of the client (NOT "anxious client" or "client's anger issues").
- **Re-authoring / Re-storying**: Therapy aims to help clients develop preferred \
narratives — alternative stories about their lives, identity, and relationships \
that reflect their values and intentions.
- **Unique outcomes**: Exceptions to the problem-saturated story — moments when \
the client acted against the problem's influence, resisted it, or lived from \
their preferred story. These are key clinical data points.
- **Scaffolding conversations**: Building from the known and familiar toward new \
possibilities, using questions that move from the concrete to the abstract, from \
the past to the present to the future.
- **Thickening the alternative story**: Developing rich, detailed descriptions of \
the preferred story — connecting it to the client's values, relationships, history, \
and hopes.
- **Deconstructing dominant narratives**: Examining how cultural, societal, or \
familial narratives contribute to the problem story and limit the client's sense \
of agency.
- **Absent but implicit**: What the problem story reveals about what the person \
values — distress as evidence of what matters.
- **Therapeutic documents**: Letters, certificates, and declarations used to \
anchor and circulate preferred stories.
- **Remembering practices**: Reconnecting with figures (living or deceased) who \
support the preferred story.
"""

NARRATIVE_THERAPY_PROGRESS = """\

### Measuring Progress in Narrative Therapy
Progress is documented through:
- Changes in the client's relationship to the problem (increased sense of agency, \
reduced influence of the problem on daily life)
- Frequency and richness of unique outcomes identified in session
- Degree of preferred story development (thin → thick description)
- Client's self-reported influence over the problem vs. the problem's influence \
over the client (externalizing scale: 0-10)
- Behavioral indicators of living from the preferred story (observable actions, \
relationship changes, new commitments)
- Shifts in identity conclusions (from problem-saturated to preferred)
"""

# Combined alias used by compliance.py and tp_review.py
NARRATIVE_THERAPY_ORIENTATION = NARRATIVE_THERAPY_PRINCIPLES + NARRATIVE_THERAPY_PROGRESS

INITIAL_ASSESSMENT_GUIDANCE = """\
## Initial Assessment Guidance (TheraNest Part 6)

Write the initial assessment structured to match TheraNest's "Initial Assessment & \
Diagnostic Codes" tab. The clinician should be able to copy-paste each section \
directly into the corresponding TheraNest field. Clearly note when information is \
absent or was not assessed.

- **Diagnostic Impressions** — ICD-10 codes with descriptions (e.g., \
`F32.1 — Major depressive disorder, single episode, moderate`). List primary \
diagnosis first, then any secondary diagnoses.
- **Presenting Problem** — Describe the problem(s) using externalized language: \
name the problem as separate from the client (e.g., "the depression," "the \
conflict") and describe its effects on the client's life, relationships, and \
sense of self. Include duration and precipitating factors. Note any dominant \
narratives the client holds about themselves or the problem (e.g., "I've always \
been broken"). Identify the client's preferred direction — what they want their \
life to look like when the problem has less influence. Write as a narrative \
paragraph suitable for TheraNest's Presenting Problem text area. If Wellness \
Assessment data is available, reference the GD severity level.
- **Observations** — Therapist's observations of client's presentation and \
family interactions. Include affect, appearance, engagement, and relational \
dynamics observed in session. Note the client's relationship to the problem \
as observed (e.g., how the problem's influence showed up in session, moments \
where the client resisted or stood apart from the problem). Document any \
unique outcomes observed — times the client spoke or acted from a position \
of agency rather than from the problem-saturated story.
- **Pertinent History** — Any prior therapy (including family, social, \
psychological, and medical history). Summarize relevant treatment history, \
hospitalizations, and significant life events.
- **Family/Psychosocial Assessment** — The family or psychosocial assessment. \
Cover family structure, key relationships, social supports, stressors, and \
relevant developmental/cultural context.
- **Risk Assessment** — Address all 8 risk domains (suicide, violence, physical \
abuse, sexual abuse, psychotic break, running away, substance abuse, self-harm). \
For each, indicate present/not present. If any are present, provide explanation \
and note whether a safety plan was established. Format clearly so the clinician \
can check the corresponding TheraNest checkboxes and paste the explanation. \
**Important:** If the wellness assessment Q22-24 (CAGE screen) has any "Yes" \
answers, flag substance abuse risk here and incorporate those findings.
- **Strengths** — Client/family strengths framed through preferred stories and \
insider knowledges: skills of living the client already possesses, values that \
sustain them, relationships that support their preferred identity, unique \
outcomes or exceptions to the problem story, and acts of resistance against \
the problem's influence. Include support systems, protective factors, and \
resources.
- **Tentative Goals and Plans** — Initial goals framed as narrative therapy \
directions: developing preferred stories, increasing the client's influence \
over the problem, re-authoring identity conclusions, thickening alternative \
narratives, and connecting with values and commitments. State goals in terms \
of the client's relationship to the problem and their preferred direction \
(e.g., "Reduce the influence of anxiety on client's daily functioning and \
develop a preferred story of courage and capability").
- **Involvement** — Who will be involved in treatment (e.g., individual client, \
family members, collateral contacts).
- **Treatment Length** — Expected duration of treatment (e.g., "6 months," \
"12 sessions").
- **Is Client Appropriate for Agency Services?** — Yes or No with explanation. \
Include referral resources if No.
- **Cultural Variables?** — Yes or No. If Yes, describe cultural factors relevant \
to treatment.
- **Special Needs of Client** — Yes or No. If Yes, describe (e.g., interpreter, \
religious consultant, accessibility needs).
- **Educational or Vocational Problems or Needs** — Yes or No. If Yes, describe.
"""

# Backwards-compat alias (was a separate, near-identical constant before merging)
INITIAL_ASSESSMENT_GUIDANCE_FILE = INITIAL_ASSESSMENT_GUIDANCE

# TheraNest's Treatment Plan tab populates the Intervention field on each
# objective from a fixed dropdown. Master list is the single source of truth —
# imported by tp_review.py and compliance.py so all three prompts agree on the
# allowed vocabulary and the label-mapping rules stay in sync.
THERANEST_INTERVENTIONS = """\
Acceptance (of limitations/reality)
Accountability
ACOA Issues
Anger Management
Art Therapy
Assertiveness Training
Behavior Modification
Best Practices for
Bibliotherapy
Building on Strengths
Career Counseling
Coaching
Cognitive-Behavioral Therapy
Communication Skills
Community
Conflict Resolution
Couples Therapy
Crisis Planning
Defusing/Debriefing
Dignity/Self-worth
Discipline
Drug & Alcohol Referral
Education
Empathy
Empowerment
Encouragement
Expression of Feelings
Fair Fighting Skills
Family Therapy
Feedback Loops
Forgiveness
Gestalt Therapy
Getting a Job (Better Job)
Goal Planning/Orientation
Good Choices/Bad Choices
Good Touch/Bad Touch
Gratitude
Grief/Loss/Bereavement Issues
Homework Assignments
Humility
Increasing Coping Skills
Independence
Journaling
Letting Go
Life Skills Training
Listening
Logical Consequences of Behavior
Magic Question (3 wishes/magic wand)
Making Friends
MISA/MICA Issues (Dual Dx Treatment)
Modeling Appropriate Behaviors
Money Management
Monitoring of
Motivation
Narrative Therapy
Normalization
Parent Effectiveness Training/Skills
Partializing (breaking down goals into manageable pieces)
Past Life Regression Therapy
Patience
Perseverance
Personal Hygiene
Play Therapy
Portion Control (Weight Control)
Positive Self-talk
Practice Exercises
Primal Screams
Priority Setting
Processing
Psychodrama
Psychoeducation
Reality Therapy
Recognizing
Refer to
Reframing
Rehearsal
Relapse Prevention
Relationship Issues
Relaxation Techniques
Responsibility for Actions
Role Playing
Self-care Skills
Self-direction (Independence)
Sexual Identity Issues
Sexuality
Social Skills Training
Social-Vocational Training
Socialization
Solution-focused Therapy
Spiritual Exploration
Starting Over
Stop-Think-Act
Strength Focus/Listing
Stress Inoculation
Stress Management
Supportive Relationships
Talk Therapy
Therapeutic Stories & Worksheets
Timeouts
Transactional Analysis (P-A-C)
Trigger Recognition
Twelve Step
Values Clarification
Verbal Communication Skills
Weight Control/Loss
Workbooks\
"""

_RAW_TREATMENT_PLAN_GUIDANCE = """\
## Treatment Plan Guidance (TheraNest Part 7)

Write a treatment plan structured to match TheraNest's Treatment Plan tab. Each \
section should be directly copy-pasteable into the corresponding TheraNest field.

- **Behavioral Definitions** — Describe the problem's effects on the client \
using externalized language: how the problem shows up in the client's life, \
the specific ways it influences their behavior, relationships, mood, and \
functioning. Frame as the problem's impact rather than the client's deficits \
(e.g., "The depression has reduced Client's engagement in social activities \
from daily to once per week" rather than "Client is socially withdrawn"). \
Include observable behavioral indicators and functional impairments. If \
Wellness Assessment data is available, include baseline GD score as a \
measurable indicator.
- **Referral for Additional Services?** — None, Yes, or No. If Yes, specify \
the referral (e.g., psychiatric evaluation, group therapy, substance abuse \
treatment).
- **Expected Length of Treatment** — Duration estimate (e.g., "6 months," \
"12 sessions").
- **Initiation Date** — Today's date ({date}).
- **Appointments Frequency** — e.g., "Weekly," "Biweekly."
- **Treatment Modality** — Individual / Marriage / Family / Other. Specify \
which applies.
- **Goals & Objectives** — Number each goal (Goal 1, Goal 2, etc.) and each \
objective under it (Objective 1a, 1b, 2a, etc.) so progress notes can reference \
them. For each goal:
  - **Client Goal**: State the goal in terms of the client's preferred \
relationship to the problem — measurable changes in the problem's influence \
on the client's life, development of preferred stories, or behavioral \
indicators of living from the preferred narrative. Include a target completion \
date. Examples: "Client will report the anxiety's influence on daily decisions \
has decreased from 8/10 to 4/10 or below," "Client will identify and describe \
3+ unique outcomes where they acted from their preferred story."
  - For each goal, list one or more **Objectives**:
    - Objective Description — specific, measurable steps toward the goal, \
framed as narrative therapy milestones (e.g., "Client will externalize the \
problem and name it," "Client will identify 2 unique outcomes per session," \
"Client will articulate preferred story of self in relationship to the problem")
    - Intervention — pick one or more items VERBATIM from the TheraNest \
intervention list below. **Strict rules:**
      - Use the exact label as written — do not paraphrase, abbreviate, or \
modify capitalization.
      - Multiple items per objective are allowed; separate with commas \
(e.g., "Narrative Therapy, Reframing, Empowerment").
      - Do NOT add explanatory prose, parentheticals, or therapist-action \
sentences after the labels — the Intervention field is a label list, not a \
description. The narrative-therapy framing belongs in the Client Goal and \
Objective Description fields above, not here.
      - The complete allowed list:
__INTERVENTION_LIST__
    - Target Completion Date
    - Status: In Progress
"""

TREATMENT_PLAN_GUIDANCE = _RAW_TREATMENT_PLAN_GUIDANCE.replace(
    "__INTERVENTION_LIST__",
    indent_block(THERANEST_INTERVENTIONS, "      "),
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

CLIENT_PROFILE_GUIDANCE = """\
## Client Profile Guidance (Internal Reference)

> **Note:** This document is for internal app reference only — not for pasting \
into TheraNest. The intake questionnaire data goes directly into TheraNest \
Client Profile (Parts 1-3) by the clinician. This profile is used by the app \
to provide context when generating future session notes for returning clients.

Write a concise, reusable profile summary:
- **Demographics**: Age, pronouns, relationship status, living situation, occupation (as disclosed)
- **Presenting Problems**: Brief summary of current concerns
- **Psychosocial Context**: Key relationships, stressors, supports
- **Medical / Substance History**: Relevant medical conditions, medications, substance use
- **Strengths**: Client strengths framed as narrative therapy resources — \
preferred stories, unique outcomes, insider knowledges (what the client knows \
about their own life that others may not), values and commitments, skills of \
living, and relational resources that support the preferred identity
- **Cultural Considerations**: Cultural identity, relevant cultural factors for treatment

## Billing & Provider Information

> **Important:** This section drives compliant progress note generation. The \
session map reads these fields to populate CPT modifiers, authorization fields, \
supervision lines, and Wellness Assessment tracking automatically. If any of \
these fields are missing or unknown, leave them as `[unknown]` and the session \
map will use `interview` to backfill before generating the next progress note.

- **Payer**: Insurance plan or payment source. Examples: "Optum EWS/EAP", \
"Optum Commercial", "Anthem PPO", "Aetna", "Self-pay", "Sliding scale".
- **Authorization Number**: Required for EAP/EWS clients. Blank or "N/A" \
otherwise. Example: "AUTH-2026-04829".
- **Total Authorized Sessions**: Integer count of sessions covered by the \
current authorization. Example: "5". Use "N/A" for non-authorized payers.
- **Authorization Period**: Start and end dates of the current authorization. \
Example: "2026-01-15 to 2026-04-15". Use "N/A" if not applicable.
- **Default Modality**: Typical session delivery method for this client. \
Options: `In-Person`, `Video`, `Phone`. This drives CPT code modifier selection \
(GT or 95 for telehealth).
- **Rendering Provider**: The clinician seeing the client. Example: \
"Jonathan Miranda, AMFT" or "Chris Hoff, LMFT". For Associate-level clinicians \
(AMFT, ACSW, APCC), the supervisor is the rendering provider on the claim.
- **Supervised**: `Yes` or `No`. Yes for Associate-level clinicians (AMFT, \
ACSW, APCC) practicing under supervision. When Yes, the U5 modifier MUST appear \
on every progress note for this client.
- **Supervisor**: Only populate when Supervised = Yes. Format: \
"Name, license type, NPI #". Example: "Chris Hoff, LMFT, NPI 1760705818".
- **Supervision Format**: How supervision is conducted for this case. Options: \
`live observation`, `recording review`, `individual supervision discussion`.
- **Service Setting / POS**: Place of service code for billing. Example: \
"Office (POS 11)" or "Telehealth - Patient Home (POS 10)" or \
"Telehealth - Other than Patient Home (POS 02)".
"""

WA_SCORING_RULES = """\
## Scoring Rules

### Global Distress (GD) Scale — Items 1-15
- Sum all 15 items. Range: 0-45.
- **Items 1-11** (symptom burden): Not at All=0, A Little=1, Somewhat=2, A Lot=3
- **Items 12-15** (wellbeing — already reverse-aligned on the form):
  Strongly Agree=0, Agree=1, Disagree=2, Strongly Disagree=3
- All items are scored so that higher = more distress. No manual reversal needed.

### Severity Thresholds
| Range | Severity | Clinical Significance |
|-------|----------|----------------------|
| 0-11 | Low | Below clinical cutoff |
| 12-24 | Moderate | At or above cutoff |
| 25-38 | Severe | Significant distress |
| 39-45 | Very Severe | Acute distress |

Clinical cutoff: **12** (GD >= 12 indicates clinically significant distress).

### CAGE-AID Screen (Items 22-24) — Initial Administration Only
- Count "Yes" responses. Range: 0-3.
- Any "Yes" = positive screen (flag substance use risk).

### Item 16 — Alcohol Use
- Number of drinks in past week. Document but do not formally score.

### Items 17-24 — Initial Administration Only
- Items 17-21: Health and workplace functioning. Document in table.
- Items 22-24: CAGE-AID (scored above).
- Re-administrations use items 1-16 only.

### Missing Data
- Up to 3 missing items on GD scale: impute score of 1 for each missing item.
- More than 3 missing items: mark GD score as **Invalid** and note which items \
are missing.
- If the form is partially completed, note which items are missing.
"""

WA_OUTPUT_FORMAT = """\
Use this format:

```
# Wellness Assessment (G22E02)

- **Client ID:** [client-id slug]
- **Date:** {date}
- **Administration:** [Initial | Re-administration (#N)]
- **Visit #:** [number]

## Global Distress (GD) Scale — Items 1-15

| # | Item | Response | Score |
|---|------|----------|-------|
| 1 | Nervousness or shakiness | [text] | [0-3] |
| 2 | Feeling no interest in things | [text] | [0-3] |
| 3 | Feeling hopeless about the future | [text] | [0-3] |
| 4 | Feeling blue | [text] | [0-3] |
| 5 | Worrying too much about things | [text] | [0-3] |
| 6 | Trouble falling asleep or staying asleep | [text] | [0-3] |
| 7 | Feeling everything is an effort | [text] | [0-3] |
| 8 | Feeling tense or keyed up | [text] | [0-3] |
| 9 | Having spells of terror or panic | [text] | [0-3] |
| 10 | Feeling restless or can't sit still | [text] | [0-3] |
| 11 | Feeling worthless | [text] | [0-3] |
| 12 | I have good self-esteem | [text] | [0-3] |
| 13 | I am able to cope with whatever comes my way | [text] | [0-3] |
| 14 | I am able to accomplish the things I set out to do | [text] | [0-3] |
| 15 | Friends/family I can count on | [text] | [0-3] |

- **GD Score:** [sum]/45
- **Severity:** [Low/Moderate/Severe/Very Severe]

## Alcohol Use (Q16)
- Drinks in past week: [number]

## CAGE-AID Screen (Q22-24) — Initial Only

| # | Question | Response |
|---|----------|----------|
| 22 | ... | Yes/No |
| 23 | ... | Yes/No |
| 24 | ... | Yes/No |

- **CAGE-AID Score:** [0-3]
- **Screen Result:** [Negative/Positive]

## Health & Workplace Items (Q17-21) — Initial Only

| # | Item | Response |
|---|------|----------|
| 17 | ... | ... |
| 18 | ... | ... |
| 19 | ... | ... |
| 20 | ... | ... |
| 21 | ... | ... |

## Score Trend (re-administrations only)

| Date | GD Score | Severity | Change |
|------|----------|----------|--------|
| [prior date] | [score] | [level] | -- |
| {date} | [score] | [level] | [+/-N] |

## Clinical Summary
[1-2 sentences: for initial, baseline context and clinical significance; \
for re-administrations, trend interpretation and treatment implications]

## Progress Note Snippet
[Ready-to-paste text for the Data section of the next progress note, e.g.: \
"Wellness Assessment (G22E02) administered: Global Distress = 28/45 (Severe); \
CAGE-AID = 0/3 (Negative)."]
```

For re-administrations, omit the CAGE-AID and Health & Workplace sections. \
Include the Score Trend table with all prior scores plus the current one.

For initial administrations, omit the Score Trend section.
"""
