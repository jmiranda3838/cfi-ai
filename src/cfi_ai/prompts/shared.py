"""Shared clinical specification blocks used across prompt templates."""

CRITICAL_INSTRUCTIONS = """\
## CRITICAL INSTRUCTIONS
- Do NOT narrate the map or reproduce document content in your response text.
- Keep free-text responses to 2-3 sentences maximum. Proceed directly to tool calls.
- The user reviews all file content in the approval step — do not preview it in chat.
"""

INITIAL_ASSESSMENT_GUIDANCE = """\
## Initial Assessment Guidance (TheraNest Part 6)

Write the initial assessment structured to match TheraNest's "Initial Assessment & \
Diagnostic Codes" tab. The clinician should be able to copy-paste each section \
directly into the corresponding TheraNest field. Clearly note when information is \
absent or was not assessed.

- **Diagnostic Impressions** — ICD-10 codes with descriptions (e.g., \
`F32.1 — Major depressive disorder, single episode, moderate`). List primary \
diagnosis first, then any secondary diagnoses.
- **Presenting Problem** — Client's initial explanation of the problem(s), \
duration, and precipitant cause. Write as a narrative paragraph suitable for \
TheraNest's Presenting Problem text area. If Wellness Assessment data is \
available, reference the GD severity level.
- **Observations** — Therapist's observations of client's presentation and \
family interactions. Include affect, appearance, engagement, and relational \
dynamics observed in session.
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
- **Strengths** — Client/family strengths including support systems, coping \
skills, protective factors, and resources.
- **Tentative Goals and Plans** — Initial goals discussed in session.
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

TREATMENT_PLAN_GUIDANCE = """\
## Treatment Plan Guidance (TheraNest Part 7)

Write a treatment plan structured to match TheraNest's Treatment Plan tab. Each \
section should be directly copy-pasteable into the corresponding TheraNest field.

- **Behavioral Definitions** — Observable behaviors supporting the diagnoses. \
Describe specific behaviors, symptoms, and functional impairments the client \
presents with. If Wellness Assessment data is available, include baseline GD \
score as a measurable indicator.
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
  - **Client Goal**: State the goal in measurable, observable terms. Include \
a target completion date.
  - For each goal, list one or more **Objectives**:
    - Objective Description — specific, measurable steps toward the goal
    - Intervention — use standard clinical intervention language (e.g., \
"Therapist will utilize CBT techniques to identify and challenge cognitive \
distortions")
    - Target Completion Date
    - Status: In Progress
"""

INTAKE_PROGRESS_NOTE_GUIDANCE = """\
## Progress Note Guidance (Optum-Compliant, DAP Format — Intake Session)

Write a progress note for the intake session using TheraNest's standard note \
fields. This covers the clinical session itself (not the assessment or plan). \
Since this is an intake session, treatment plan goals are being established \
rather than tracked.

### Required Fields

- **Date of Service** — {date}
- **Service Code** — 90791 (Psychiatric diagnostic evaluation) for intake sessions.
- **Session Duration** — Total session time in minutes.
- **Participants in Session** — All individuals present with roles (e.g., \
"Client, therapist"). Include names/roles for collateral participants.
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

- **Medication Changes** — Any medication changes reported by client, or \
"No changes reported. Current medications: [list if known]."

- **Treatment Plan Goals Addressed** — "Baseline assessment — treatment plan \
goals established this session." List the goals and objectives created, \
referencing them by number for future session linkage.

- **Session Summary (DAP Format)**:
  - **D (Data):** Client self-report and objective observations. What the \
client reported, presenting issues discussed, relevant quotes, behavioral \
observations (affect, appearance, engagement). If Wellness Assessment (G22E02) was administered, document: GD score \
[X/45], severity level [Low/Moderate/Severe/Very Severe], and CAGE-AID result \
[Negative/Positive (N/3)]. Example: "Wellness Assessment (G22E02) administered: \
Global Distress = 28/45 (Severe); CAGE-AID = 0/3 (Negative)."
  - **A (Assessment):** Clinical impressions. Baseline functioning assessment \
across domains (work, relationships, self-care). Diagnostic formulation. \
Emerging themes and patterns. Baseline severity ratings for presenting \
concerns (e.g., "Client rates anxiety at 8/10").
  - **P (Plan):** Treatment plan established (reference goals by number). \
Between-session tasks or homework assigned. Referrals made or needed. \
Focus areas for next session.

- **Strengths & Barriers** — Client strengths identified during intake that \
will support treatment. Barriers or limitations identified that may impact \
treatment progress.

- **Medical Necessity** — Initial session establishes baseline for treatment. \
Continued treatment indicated based on presenting concerns, diagnostic \
impressions, and functional impairment. Specify why this level of care \
(frequency, modality) is appropriate. If GD score is at or above clinical \
cutoff (12+), reference it as objective evidence supporting medical necessity.

- **Next Appointment** — Date and specific focus areas for next session.
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
- **Strengths**: Client strengths, resources, and resilience factors
- **Cultural Considerations**: Cultural identity, relevant cultural factors for treatment
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

- **Client ID:** {client_id}
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
