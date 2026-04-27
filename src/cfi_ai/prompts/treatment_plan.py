"""Authoritative TheraNest form spec for "Treatment Plan" — source of truth. Clinical and narrative-therapy writing guidance lives in separate modules."""

from cfi_ai.prompts.shared import indent_block

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
## TheraNest Form: Treatment Plan

Fields on the TheraNest "Treatment Plan" tab, in the order they appear. Each \
section below maps 1:1 onto a TheraNest field. This document describes only \
what TheraNest expects — not how to write it.

Global conventions:
- Write all textareas as prose.
- No textarea should be left blank. When a field does not apply, state so \
explicitly (e.g., "No additional referrals were identified as needed.").
- All dropdown values must be selected verbatim from the provided options — \
do not substitute, paraphrase, or invent new values.

- **Review** — dropdown: 7, 14, 30, 60, 90, or 120 days. TheraNest \
displays this as "Review in <days> days on <date>," auto-calculating the \
review date by adding the selected number of days to the Initiation Date.
- **Diagnostic Impressions** — Auto-populated by TheraNest from the \
diagnoses selected on the Initial Assessment & Diagnostic Codes tab. Not \
editable on the Treatment Plan form; no content needs to be produced for \
this field.
- **Behavioral Definitions** — textarea. Concrete, observable descriptions \
of how each presenting problem currently manifests in the client's life. \
For each problem area covered in the plan, cover the specific behaviors, \
symptoms, and functional impairments (work, school, relationships, daily \
living) that define that problem. Include measurable baselines where \
available — frequency, duration, or severity of behaviors, and standardized \
assessment scores such as a Wellness Assessment GD score. When multiple \
problems are being treated, delineate the behavioral definitions for each.
- **Referral for Additional Services?** — Two-part field:
    - dropdown: None, Yes, or No.
    - **Explanation** — textarea. If Yes, specify the referral(s) (e.g., \
psychiatric evaluation, group therapy, substance abuse treatment, medical \
consultation). If None or No, state that no additional referrals were \
identified as needed.
- **Expected Length of Treatment** — Duration estimate (e.g., "6 months," \
"12 sessions").
- **Initiation Date** — Today's date ({date}).
- **Appointments Frequency** — e.g., "Weekly," "Biweekly."
- **Treatment Modality** — Individual / Marriage / Family / Other. Specify \
which applies.
- **Client Goals** — one subsection per goal. Number each goal (Goal 1, \
Goal 2, etc.) and each objective within it (Objective 1, Objective 2, etc.) \
so progress notes can reference them. Each Client Goal subsection has the \
following fields:
    - **Client Goal** — textarea. State the goal in measurable terms tied \
to the problem(s) identified in Behavioral Definitions.
    - **Target Completion Date** — date for this goal.
    - **Objectives** — one sub-subsection per objective. Each objective \
subsection has the following fields:
        - **Objective [number]** — the objective's number within the \
parent goal (e.g., Objective 1, Objective 2).
        - **Objective Description** — textarea. Specific, measurable step \
toward the parent goal; describes what the client will do or demonstrate.
        - **Intervention** — dropdown. One or more items from the \
TheraNest intervention list. Rules:
            - Multiple items per objective are allowed; separate with \
commas (e.g., "Narrative Therapy, Reframing, Empowerment").
            - Do NOT add explanatory prose, parentheticals, or \
therapist-action sentences after the labels — the Intervention field is \
a label list, not a description.
            - The complete allowed list:
__INTERVENTION_LIST__
        - **Target Completion Date** — date for this objective.
        - **Status** — dropdown: In Progress, Complete, Closed, or Deferred.
"""

TREATMENT_PLAN_GUIDANCE = _RAW_TREATMENT_PLAN_GUIDANCE.replace(
    "__INTERVENTION_LIST__",
    indent_block(THERANEST_INTERVENTIONS, "            "),
)
