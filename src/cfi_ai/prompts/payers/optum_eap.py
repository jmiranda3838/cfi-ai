"""Optum EWS/EAP payer rules — billing, modifiers, authorization handling, and required assessment instruments specific to Optum's Employee Assistance Program."""

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

OPTUM_EAP_RULES = ("""\
## Payer Rules: Optum EWS/EAP

Apply these rules when the client's Payer is Optum EWS or Optum EAP.

### Documentation Scope: EAP is a Brief-Intervention Benefit

Optum EAP/EWS is contractually a brief intervention + assessment + referral \
benefit, not a full course of treatment. The authorized sessions are what \
Optum is purchasing — documentation that exceeds this scope reads as \
misrepresentation of the benefit on audit. Each document type has its own \
lane; keep the clinical content in the right one.

These rules SHAPE the content of TheraNest's existing fields — they do NOT \
introduce new fields. All field names referenced below come from the \
TheraNest form specs already in this prompt; do not invent new sections or \
headings.

#### Treatment Plan (TheraNest "Treatment Plan" form): EAP-scoped goals only
The EAP treatment plan must keep its goals achievable inside the authorized \
sessions. Populate the existing TheraNest fields as follows:
- **Client Goals** — produce 3-5 numbered goals drawn from these patterns:
    - **Stabilize acute symptoms** with a measurable target (e.g. "reduce \
PHQ-9 from 18 → 12 over the authorized course"; "GD severity from Severe \
to Moderate"). Use the Wellness Assessment GD score from intake as the \
baseline where available.
    - **Develop 2-3 concrete coping skills** (e.g. behavioral activation, \
cognitive restructuring intro, sleep hygiene, grounding / affect regulation).
    - **Psychoeducation** on the presenting diagnosis or problem.
    - **Establish therapeutic alliance and clarify the continued-care \
pathway.**
    - **Develop a discharge / transition plan.** Per the Optum Provider \
Manual (p.63), discharge planning begins at the onset of treatment — every \
EAP course has a transition-planning goal from session 1, framed as a \
Client Goal with Objectives (e.g. Objective: "Client and therapist will \
identify continued-care pathway — BH benefits, OON/superbill, or referral \
out — by session N"). This is NOT a separate "Discharge Plan" section; it \
is one of the numbered Client Goals.
- **Behavioral Definitions** — include the Wellness Assessment GD score \
and any other measurable baselines (PHQ-9, GAD-7, etc.) as concrete \
markers of the problems the goals will track against.
- **Expected Length of Treatment** — match the authorized session count \
(e.g. "5 sessions"), not a longer-arc estimate.
- **Intervention** (per objective) — use only labels from the TheraNest \
intervention dropdown defined in the Treatment Plan form spec.

DO NOT write long-arc Client Goals like "remission of MDD over 20 sessions \
of weekly CBT" or "sustained sobriety over 6 months of treatment" on the \
EAP treatment plan. These exceed what EAP pays for and misrepresent the \
benefit.

#### Initial Assessment (TheraNest "Initial Assessment & Diagnostic Codes" form): full clinical picture
The initial assessment is where the full, clinically honest picture lives. \
Populate the existing TheraNest fields as follows:
- **Diagnostic Impressions** — diagnosis with severity and specifiers. \
Standard field, no EAP-specific shaping.
- **Pertinent History** — include clinical formulation elements that are \
historically grounded (course, prior episodes, prior treatment response, \
substance use, family hx) per the existing field spec.
- **Tentative Goals and Plans** — this is where the EAP-vs.-full-course \
clinical recommendation and rationale live. Cover:
    - Recommended course of treatment (e.g. "recommended course is 20-30 \
sessions of weekly individual psychotherapy"). The numeric estimate also \
goes in the Treatment Length field; the rationale lives here.
    - Prognosis, barriers to treatment, and any anticipated need for \
higher levels of care.
    - Explicit framing when the client's needs exceed EAP scope, e.g. \
"Severity and chronicity of presentation exceed the brief-intervention \
scope of EAP. EAP will be utilized for assessment, stabilization, and \
establishing a continued-care pathway."
- **Treatment Length** — recommended duration of the *full clinical \
course* (e.g. "20-30 sessions"), not the authorized EAP session count. \
The Tentative Goals and Plans field carries the rationale.

#### Progress Notes (TheraNest progress note form): clinical rationale
Progress notes carry the clinical reasoning within the existing TheraNest \
progress note fields per the Progress Note form spec — why the chosen \
interventions, how the client is responding, and ongoing assessment of \
whether EAP scope remains sufficient. Long-term clinical recommendations \
belong here as rationale, not as new treatment-plan goals.

#### Discharge Summary: not produced by /intake
At the end of the authorized course a discharge summary documents the \
reason for any ongoing care, the proposed post-discharge services, and \
the transition plan. **The /intake workflow does NOT produce a discharge \
summary** — that document is written at end-of-course in a separate \
workflow. Do not generate one during intake. If the client later moves \
to a new episode of care under BH benefits or another payer, a *new* \
treatment plan is written for that episode; the EAP discharge summary \
plus the new intake note together demonstrate clinical continuity without \
conflating benefits.

### CPT Codes
- For Optum EAP/EWS intake and ongoing sessions, bill `90834` (38-52 min \
individual psychotherapy). Do NOT use `90791` for Optum EAP intakes — Optum \
bills the EAP intake under 90834.
- Other CPT codes (`90832`, `90837`, `90846`, `90847`) are not used for EAP.

### Modifiers
- `HJ` is REQUIRED on every Optum EAP/EWS progress note — it is the EAP \
service indicator.
- `U5` applies independently when the rendering provider is an Associate-level \
clinician (AMFT, ACSW, APCC) practicing under licensed supervision. This is \
California license-driven (not payer-driven), but it must be present on Optum \
EAP claims when applicable.
- `GT` / `95` apply for telehealth modality, per the standard telehealth rules.

### Authorization
- Optum EWS/EAP requires an authorization number on every session. Pull from \
the client profile's `Authorization Number` field.
- Sessions are counted against `Total Authorized Sessions` from the profile. \
Compute `Session # of Authorized Total` as \
`[count of existing progress notes for this client + 1] of [Total Authorized]`.
- Once the authorization is exhausted, no further EAP sessions can be billed \
under this authorization.

### Required Wellness Assessment (G22E02): Intake & Re-administration

Optum requires the G22E02 Wellness Assessment at intake. It may also be \
re-administered periodically during ongoing treatment to track progress \
against the GD baseline. Whenever a completed G22E02 is provided — at intake \
or during a later session — calculate and use the scores per the rules below.

#### Detecting Initial vs. Re-administration
Check `clients/<client-id>/wellness-assessments/` for prior assessments:
- No prior assessments → this is the **initial** administration.
- Prior assessments exist → this is **re-administration #N** (where N = count \
+ 1). Load all prior assessments with `attach_path` to build the Score Trend \
table in the output format.

"""
    + WA_SCORING_RULES
    + """
#### How to use the scores
- **Presenting Problem**: Reference GD severity to contextualize the problem's \
effects on the client (e.g., "endorsed Severe global distress (GD=28/45), \
reflecting the extent of the depression's influence on daily functioning").
- **Behavioral Definitions** (Treatment Plan): Include GD score as a measurable \
baseline for the problem's impact (externalized framing).
- **Progress Note Data**: Document GD score, severity, and CAGE-AID result \
explicitly.
- **Medical Necessity**: GD at/above cutoff (12+) supports medical necessity.

#### Output File
When G22E02 data is present, also write \
`clients/<client-id>/wellness-assessments/{date}-wellness-assessment.md` using \
this format:

"""
    + WA_OUTPUT_FORMAT
    + """

### Payer Field Values
Use `"Optum EWS/EAP"` (preferred) or `"Optum EAP"` in the client profile's \
Payer field. Both map to slug `optum-eap`.

### Audit Reference
- Audit instrument: **Optum Treatment Record Audit Tool**.
- Pass threshold: **85%** of applicable items must pass.
""")
