"""Treatment Plan guidance (TheraNest Part 7) — single source of truth including intervention master list."""

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
