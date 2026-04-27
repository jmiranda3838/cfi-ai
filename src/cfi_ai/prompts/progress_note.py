"""Authoritative TheraNest form spec for the "Progress Note" — source of truth for both ongoing and intake variants. Clinical, narrative-therapy, and payer-compliance guidance lives in separate modules."""

# Each Mental Status domain in TheraNest is its own multi-select sub-field
# with a fixed vocabulary. Master lists are the single source of truth so all
# downstream prompts (compliance, tp-review, etc.) agree on allowed values.
THERANEST_APPEARANCE_OPTIONS = """\
clean
dirty
appropriate to age
meticulous
odor
older than age
unbathed
unkempt
unremarkable
well-groomed
younger than age
WNL\
"""

THERANEST_ORIENTATION_OPTIONS = """\
x4: time, place, person, situation
x1: time only
x1: place only
x1: person only
x1: situation only
x2: time + place (not person, situation)
x2: time + person (not place, situation)
x2: time + situation (not place, person)
x2: place + person (not time, situation)
x2: place + situation (not time, person)
x2: person + situation (not time, place)
x3: time + place + person (not situation)
x3: time + person + situation (not place)
x3: place + person + situation (not time)
WNL\
"""

THERANEST_BEHAVIOR_OPTIONS = """\
agitated
alert
awkward
belligerent
clumsy
compulsive
cooperative
delirious
distracted
echopraxia
fatigued
grimacing
guarded
hostile
hyperactive
hypoactive
impulsive
manipulative
mannerisms
playful
pleasant
provocative
relaxed
ritualistic
seductive
sleepy
stiff
stuporous
suspicious
tics
tremulous
uncooperative
withdrawn
WNL\
"""

THERANEST_SPEECH_OPTIONS = """\
expansive
hesitant
inaudible
incoherent
loud
monotonous
mute
pressured
rapid
repetitive
slow
slurred
soft
stuttering
verbose
whispering
WNL\
"""

THERANEST_AFFECT_OPTIONS = """\
appropriate to situation
blunted
constricted
expansive
flat
inappropriate to situation
labile
lively
stable
WNL\
"""

THERANEST_MOOD_OPTIONS = """\
angry
anxious: mild
anxious: moderate
anxious: severe
anxious: panic
aggressive
apathetic
apprehensive
belligerent
combative
depressed
dysphoric
elevated
euphoric
fearful
hopeless
hostile
hurt
irritable
miserable
optimistic
perplexed
pessimistic
regretful
sad
seductive
shame
WNL
hopeful\
"""

THERANEST_THOUGHT_PROCESS_OPTIONS = """\
blocked
circumstantial
coherent
disorganized
echolalia
flight of ideas
fragmented
goal directed
incoherent
irrational
loosely associated
mutism
neologistic
obsessive
organized
perseverative
preoccupied
recent memory impairment
remote memory impairment
rigid
tangential
word salad
WNL\
"""

THERANEST_THOUGHT_CONTENT_OPTIONS = """\
concrete thinking
delusions: bizarre
delusions: erotomanic
delusions: grandiose
delusions: guilt, sin
delusions: influence (active)
delusions: influence (passive)
delusions: mind-reading
delusions: mood-congruent
delusions: mood-incongruent
delusions: nihilistic
delusions: persecutory
delusions: religious
delusions: somatic
delusions: thought insertion
delusions: thought withdrawal
delusions: other
homicidal ideation
ideas of reference
obsessions
overvalued ideas
paranoid ideation
phobias
poverty of thought
suicidal ideation
WNL\
"""

THERANEST_PERCEPTION_OPTIONS = """\
depersonalization
derealization
hallucinations: auditory
hallucinations: gustatory
hallucinations: kinesthetic
hallucinations: olfactory
hallucinations: tactile
hallucinations: visual
WNL\
"""

THERANEST_JUDGMENT_OPTIONS = """\
appropriate
impaired
inappropriate
intact
unrealistic
WNL\
"""

THERANEST_INSIGHT_OPTIONS = """\
emotional
full
impaired
intellectual
intellectual and emotional
limited
none
partial
WNL\
"""

THERANEST_APPETITE_OPTIONS = """\
binging
binging and purging
decreased
erratic
increased
purging
restricting
WNL\
"""

THERANEST_SLEEP_OPTIONS = """\
early insomnia
excessive
impaired
middle insomnia
terminal insomnia
WNL\
"""

# Shared vocabulary for the Risk Assessment section's Suicidality and
# Homicidality sub-fields (both are multi-select with the same options).
THERANEST_RISK_PRESENTATION_OPTIONS = """\
Not Present
Ideation
Plan
Intent
Attempt\
"""

_RAW_PROGRESS_NOTE_GUIDANCE = """\
## TheraNest Form: Progress Note

Fields on the TheraNest Progress Note form, in the order they appear. Each \
section below maps 1:1 onto a TheraNest field. This document describes only \
what TheraNest expects — not how to write it.

Write the progress note as a markdown document with one section per TheraNest \
field, in the EXACT field order below. The clinician will paste each section \
into the corresponding TheraNest Dynamic Form field. Today's date is {date}.

The client's current treatment plan is provided in the client context above — \
you MUST reference specific goals and objectives from it. Read the client \
profile's **Billing & Provider Information** section before generating the \
note; the session map will have already used `interview` to populate it if it \
was missing.

This form spec is payer-agnostic. CPT-code allowlists, required modifiers, \
authorization handling, and any payer-specific assessment instruments come \
from the payer rules loaded via `load_payer_rules` at the start of the \
workflow. Fill billing fields per the active payer's rules — do not infer \
payer-specific behavior from this spec.

---

### Header / Administrative

#### Client Details
Auto-populated by TheraNest from the client record. No content needs to be \
produced for this field.

#### Client ID Number
Auto-generated by TheraNest. No content needs to be produced for this field.

#### Service Start/End Date
Two date fields: Service Start Date and Service End Date. For a single-session \
service these are both today ({date}).

#### Session Start/End Time
Two time fields marking the exact start and end time of the session.

#### Duration (minutes)
Auto-calculated by TheraNest from the Session Start/End Time. No content needs \
to be produced for this field.

#### Appointment
Dropdown. Select the TheraNest appointment record this progress note \
documents. Entries appear in the format: \
`<start time> - <end time>. <CPT code>: <duration> - <CPT description>, \
<Type>, <Payer>, <Supervisee/Provider> (<supervisor details>)`. Example: \
`07:00 AM - 08:00 AM. 90834: 41 - 38-52 mins, Individual, <Payer>, \
Supervisee (<supervisor name, license>, <rendering provider, license>)`. \
Produce your best guess based on the session details — the clinician will \
correct the selection in TheraNest.

#### Place Of Service
CMS Place of Service code in the format `<Label> (<code>)`. For in-person \
sessions use `Office (11)`. Select the code matching the session modality.

#### Provider(s)
Auto-populated by TheraNest with the associate therapist and supervisor. No \
content needs to be produced for this field.

#### Participant(s) in Session
Textarea. List everyone present in the session with their role (e.g., \
"Client only", "Client and partner", "Client and mother"). For minors, \
include the parent/guardian role.

#### Type Of Note
Dropdown. One of: `Individual` / `Group` / `Family` / `Collateral`. Select \
based on the participants in the session.

---

### Billing & Authorization

#### CPT Code Billed [REQUIRED]
Dropdown. Choose the appropriate code for session duration and participants:
- `90832` — Individual psychotherapy, 16-37 minutes
- `90834` — Individual psychotherapy, 38-52 minutes
- `90837` — Individual psychotherapy, 53+ minutes
- `90846` — Family therapy without patient present, 50 min
- `90847` — Family/couples therapy with patient present, 50 min
- `90791` — Reserved for intake; do not use for ongoing sessions

#### CPT Code Modifiers
Checkboxes for `HJ`, `U5`, `GT`, and `95`. Each modifier represents:
- **HJ** — EAP (Employee Assistance Program) service indicator
- **U5** — service rendered by a supervisee under licensed supervision
- **GT** — synchronous telemedicine via interactive audio/video
- **95** — synchronous real-time telehealth over HIPAA-compliant audio/video

#### Modality [REQUIRED]
Dropdown. One of: `In-Person` / `Video` / `Phone`. Pull from the profile's \
Default Modality, or infer from the source material if it differs (e.g., \
session audio with in-person ambient sound vs. Zoom recording).

#### Authorization Number
Textarea. The payer-issued authorization number for this course of \
treatment. Populate from the client profile's Authorization Number if one \
is on file; otherwise leave blank.

#### Session # of Authorized Total
The session's position within the authorized course of treatment. Compute \
as `[count of existing progress notes for this client + 1] of [Total \
Authorized Sessions from the profile]`. Example: `3 of 5`. Use \
`run_command ls clients/<id>/sessions/` to count existing notes if needed.

#### Payer [REQUIRED]
Pull verbatim from the profile's Payer field (e.g., "Optum EWS/EAP", \
"Aetna", "Evernorth", "Self-pay").

---

### Diagnosis

#### Diagnostic Impressions
Auto-populated by TheraNest from the Initial Assessment & Diagnostic Codes. \
No content needs to be produced for this field.

#### Diagnosis Addressed This Session [REQUIRED]
Textarea. State which dx from Diagnostic Impressions was the focus today. For \
most sessions this is the primary diagnosis, but if a session addressed a \
secondary dx (e.g., substance use during a primary depression treatment), \
name that one.

---

### Treatment Plan Linkage

#### Treatment Goals
Auto-populated by TheraNest from the full goals and objectives in the \
Treatment Plan. No content needs to be produced for this field.

#### Goals/Objectives Addressed This Session [REQUIRED]
Textarea. State which specific goal(s) and objective(s) from Treatment \
Goals were worked on today, by number, and HOW each was addressed in \
session.

---

### Mental Status Exam

#### Mental Status
Multi-field section. Each domain below is its own TheraNest sub-field — a \
multi-select list where the clinician picks one or more items from a fixed \
vocabulary. Use values from the provided lists verbatim; do not substitute, \
paraphrase, or invent new values. If a domain is within normal limits, select \
`WNL`.

##### Appearance
Multi-select list. Allowed values:

__APPEARANCE_LIST__

##### Orientation
Multi-select list. Allowed values:

__ORIENTATION_LIST__

##### Behavior
Multi-select list. Allowed values:

__BEHAVIOR_LIST__

##### Speech
Multi-select list. Allowed values:

__SPEECH_LIST__

##### Affect
Multi-select list. Allowed values:

__AFFECT_LIST__

##### Mood
Multi-select list. Allowed values:

__MOOD_LIST__

##### Thought Process
Multi-select list. Allowed values:

__THOUGHT_PROCESS_LIST__

##### Thought Content
Multi-select list. Allowed values:

__THOUGHT_CONTENT_LIST__

##### Perception
Multi-select list. Allowed values:

__PERCEPTION_LIST__

##### Judgment
Multi-select list. Allowed values:

__JUDGMENT_LIST__

##### Insight
Multi-select list. Allowed values:

__INSIGHT_LIST__

##### Appetite
Multi-select list. Allowed values:

__APPETITE_LIST__

##### Sleep
Multi-select list. Allowed values:

__SLEEP_LIST__

#### Functional Impairment [REQUIRED]
Textarea. A present-tense snapshot of concrete impairment by domain: \
work/school, relationships, self-care, ADLs (activities of daily living). \
Describe current functioning only — do NOT include trajectory language \
(improved/worsened/stable) here; trajectory belongs in Client Progress. \
Example: "Client reports missing 1 day of work this week; attended one \
social outing with a friend; currently avoids grocery shopping due to \
anxiety in crowds."

---

### Risk Assessment

#### Suicidality [REQUIRED]
Multi-select list. Allowed values:

__RISK_PRESENTATION_LIST__

Select `Not Present` if the client denies SI. Otherwise select all that apply \
(e.g., `Ideation` alone for passive thoughts without plan or intent).

#### Homicidality [REQUIRED]
Multi-select list. Allowed values:

__RISK_PRESENTATION_LIST__

Select `Not Present` if the client denies HI. Otherwise select all that apply.

#### Explanation
Textarea. Populate with details for any non-`Not Present` selection above: \
self-harm history, prior attempts, ideation patterns, identified target(s) \
for HI, and intervention used in session. If both Suicidality and \
Homicidality are `Not Present`, write `Client denies SI and HI.`

#### Risk Level [REQUIRED]
Dropdown. One of: `None` / `Low` / `Moderate` / `High` / `Imminent`. Choose \
based on the Suicidality, Homicidality, and Explanation fields above.

#### Protective Factors [REQUIRED]
Textarea. Required even when Risk Level = None. List concrete protective \
factors: support system (specify who), reasons for living, future-oriented \
goals, treatment engagement, coping skills already in use, \
religious/spiritual resources, access to means restriction, etc.

#### Safety Plan (if clinically indicated)
Textarea. Populate ONLY if Risk Level > None. Use the Stanley-Brown Safety \
Plan format (warning signs → internal coping → social distractions → people \
for help → professionals/agencies → means restriction). For Risk Level = \
None, write `Not clinically indicated at this time.`

#### Tarasoff / Mandated Reporting Triggered? [REQUIRED]
Dropdown. One of: `Yes` / `No`. Triggered by: credible threat of harm to \
identifiable victim, suspected child/elder/dependent adult abuse, or \
court-ordered disclosure.

#### If "Yes" was selected above, please explain
Textarea. Populate ONLY if Tarasoff/Mandated Reporting Triggered? = Yes. \
Document who was contacted (CPS/APS/police/victim), when, what was reported, \
and supervisor consultation. Otherwise leave blank.

---

### Session Content

#### Subjective
Textarea. The client's self-report for this session: what the client \
reported about the past week, current state, what has changed, what has \
emerged. Include direct quotes where clinically relevant and use the \
client's own language for symptoms, situations, and self-description.

#### Session Focus
Textarea. Primary topics, themes, and presenting issues addressed in this \
session. Brief — 1-3 sentences.

#### Planned Intervention
Textarea. **Past tense — what the clinician had planned for this session \
BEFORE it occurred**, not interventions to be used in future sessions. \
Document the pre-session plan: which interventions the clinician intended \
to use today, tied to the treatment-plan goal(s) and objective(s) they \
were selected to serve, and the clinical rationale for that plan. This \
field is distinct from Therapeutic Intervention below, which documents \
what was actually used in the session.

#### Therapeutic Intervention
Textarea. The clinical technique(s) the clinician ACTUALLY USED in this \
session, past tense, each tied to the treatment-plan goal(s) and \
objective(s) it served. For each technique, briefly describe what was \
done. This field documents execution — contrast with Planned Intervention \
(the pre-session plan) and Client's Response to Intervention (how the \
client received what was done).

#### Client's Response to Intervention [REQUIRED]
Textarea. The client's observable, in-session response to the \
intervention(s) documented in Therapeutic Intervention: engagement level, \
receptivity, insight or skill demonstrated, resistance, and any notable \
moments. Focus on what was observed during this session. Cumulative \
progress across sessions belongs in Client Progress.

#### Client Progress [REQUIRED]
Two checkboxes: `Progress` and `No Progress`. Check exactly one, reflecting \
the client's cumulative trajectory toward treatment-plan goals overall — \
NOT just this session.

#### Additional Details
Textarea. Supporting detail for the Client Progress selection above. \
Document concrete indicators of change (or lack of change) over time \
across the active treatment-plan goals and objectives: symptom ratings, \
behavioral frequencies, functional-domain change drawn from Functional \
Impairment snapshots across sessions, and any other measurable targets \
named in the treatment plan. Where possible, state direction (improved / \
stable / worsened) per goal or domain.

---

### Synthesis

#### Medical Necessity Statement [REQUIRED]
Textarea. Explicit clinical rationale for why continued psychotherapy is \
indicated, tying together: (a) the active diagnosis from Diagnosis \
Addressed This Session, (b) current symptoms and functional impairment \
from Functional Impairment, (c) treatment-plan goals from \
Goals/Objectives Addressed This Session, and (d) the clinical necessity \
of ongoing treatment. Reference specific findings from THIS session \
rather than template language.

#### Plan
Textarea. The clinical plan from today's session. Cover the items below — \
none of these have dedicated TheraNest fields:
- **Homework / between-session tasks** assigned (e.g., noticing \
assignments, reflective writing, journaling prompts, behavioral \
experiments)
- **Referrals made** (e.g., psychiatric eval, group therapy, medical \
workup) or `No referrals at this time`
- **Next appointment**: date/time and focus areas for the next session
- **Coordination of care**: communication with PCP, psychiatrist, school, \
family, or other providers — OR explicitly note `Client declined ROI for \
coordination of care at this time` or `No coordination of care needed \
today`

#### Additional Notes
Textarea. Any clinical information relevant to the session that does not \
fit the structured fields above (e.g., supervisor consultation notes, \
technical issues during telehealth, collateral contacts made).

"""

PROGRESS_NOTE_GUIDANCE = (
    _RAW_PROGRESS_NOTE_GUIDANCE
    .replace("__APPEARANCE_LIST__", THERANEST_APPEARANCE_OPTIONS)
    .replace("__ORIENTATION_LIST__", THERANEST_ORIENTATION_OPTIONS)
    .replace("__BEHAVIOR_LIST__", THERANEST_BEHAVIOR_OPTIONS)
    .replace("__SPEECH_LIST__", THERANEST_SPEECH_OPTIONS)
    .replace("__AFFECT_LIST__", THERANEST_AFFECT_OPTIONS)
    .replace("__MOOD_LIST__", THERANEST_MOOD_OPTIONS)
    .replace("__THOUGHT_PROCESS_LIST__", THERANEST_THOUGHT_PROCESS_OPTIONS)
    .replace("__THOUGHT_CONTENT_LIST__", THERANEST_THOUGHT_CONTENT_OPTIONS)
    .replace("__PERCEPTION_LIST__", THERANEST_PERCEPTION_OPTIONS)
    .replace("__JUDGMENT_LIST__", THERANEST_JUDGMENT_OPTIONS)
    .replace("__INSIGHT_LIST__", THERANEST_INSIGHT_OPTIONS)
    .replace("__APPETITE_LIST__", THERANEST_APPETITE_OPTIONS)
    .replace("__SLEEP_LIST__", THERANEST_SLEEP_OPTIONS)
    .replace("__RISK_PRESENTATION_LIST__", THERANEST_RISK_PRESENTATION_OPTIONS)
)
