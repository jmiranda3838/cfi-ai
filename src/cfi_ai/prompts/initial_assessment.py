"""Authoritative TheraNest form spec for "Initial Assessment & Diagnostic Codes" — source of truth. Clinical and narrative-therapy writing guidance lives in separate modules."""

INITIAL_ASSESSMENT_TEMPLATE = """\
## TheraNest Form: Initial Assessment & Diagnostic Codes

Fields on the TheraNest "Initial Assessment & Diagnostic Codes" tab, in the \
order they appear. Each section below maps 1:1 onto a TheraNest field. This \
document describes only what TheraNest expects — not how to write it.

Global conventions:
- Write all textareas as prose.
- No textarea should be left blank. When a domain does not apply, was not \
assessed, or the client denies it, state so explicitly (e.g., "Client denies \
any history of..." or "Not assessed in this session.").

- **Diagnostic Impressions** — one subsection per diagnosis. Each subsection \
has three fields:
    - **Diagnostic Code** — dropdown. Produce in the format \
`<numeric code> (<ICD-10 code>) <Description>`.
    - **Diagnostic Classification** — dropdown: Primary, Secondary, Tertiary, \
or Quaternary. Each value may be used at most once; any fifth-or-later \
diagnosis is listed without a classification.
    - **Diagnosis Code Description** — textarea. Optional additional \
clarification about the diagnosis; appears on printed initial/behavioral \
assessments and progress notes. Write a brief clarification if one is \
useful, otherwise state "None."
- **Presenting Problem** — textarea. Per TheraNest: "client's initial \
explanation of the problem(s), duration and precipitant cause." Cover the \
problem(s) as the client describes them (use the client's own words where \
useful), how long they have been occurring, what precipitated or triggered \
them, and their current impact on the client's functioning.
- **Pertinent History** — textarea. Per TheraNest: "any prior therapy \
(including family, social, psychological, and medical)." Cover prior mental \
health treatment (providers, modalities, approximate dates, outcomes), \
inpatient hospitalizations, current and past psychiatric medications, family \
history of mental illness or substance use, substance use history, relevant \
medical conditions, and significant life events (trauma, losses, major \
transitions).
- **Observations** — textarea. Per TheraNest: "therapist's observations of \
client's presentation and family interactions." Covers mental status exam \
(MSE) domains observed directly in session: appearance and grooming, \
behavior and motor activity, attitude, speech (rate/volume/articulation), \
mood, affect (range, congruence), thought process and content, orientation, \
attention, insight, and judgment. For family, couples, or collateral \
sessions, also document relational dynamics (e.g., turn-taking, alignments, \
conflict patterns, who speaks for whom). Restrict to what was observed in \
the room — not historical information.
- **Family/Psychosocial Assessment** — textarea. Per TheraNest: "the family \
or psychosocial assessment." Cover family structure (household composition, \
marital status, children), family of origin (parents, siblings, \
relationships with them), key current relationships, living situation and \
housing stability, education and employment, financial stressors, relevant \
cultural and religious background, developmental history relevant to the \
presenting problem, and legal history if applicable. Scoped to the client's \
current psychosocial snapshot — prior treatment and hospitalizations belong \
in Pertinent History; supports and cultural/spiritual resources belong in \
Strengths; treatment-relevant cultural factors belong in Cultural Variables.
- **Risk** — Per TheraNest: "evidence of potential or actual risk(s); \
select and explain." Two-part field:
    - Checkboxes for each of the following domains; check only those that \
are present: suicide, violence, physical abuse, sexual abuse, psychotic \
break, running away, substance abuse, self-harm.
    - **Explanation** — textarea. Cover each checked domain with: nature \
and severity of the risk (ideation vs. plan vs. intent vs. means, frequency \
and recency); historical context (prior attempts, hospitalizations); and \
risk-specific protective factors. Organize by domain when multiple are \
checked. If no domains are checked, document that the client denied each \
risk area and add any other relevant context. Safety planning belongs in \
the Contract/Safety Plan field below, not here.
- **Contract/Safety Plan** — Per TheraNest: "if yes, which risk areas; if \
no, explain." Two-part field:
    - **Client Made Contract/Safety Plan To Cover Risk(s)?** — dropdown: \
None, Yes, or No. (None = not applicable / no risks present; Yes = a plan \
was made; No = no plan was made despite risks being present.)
    - **Explanation** — textarea. If Yes, list which risk areas the plan \
covers and the key elements of the plan (e.g., warning signs, internal \
coping strategies, social supports, professional/crisis contacts, means \
restriction). If No, explain why (e.g., client declined, risk too acute for \
outpatient safety planning, referred to higher level of care). If None, \
state that no risks were identified requiring safety planning.
- **Strengths** — textarea. Per TheraNest: "client/family strengths \
(including support system(s))." Cover four areas: (1) personal strengths, \
coping skills, and prior successful coping strategies; (2) family, \
relational, social, and community supports; (3) cultural, spiritual, and \
religious resources; (4) motivation for treatment and general protective \
factors.
- **Tentative Goals and Plans** — textarea. No TheraNest description. \
Outline initial treatment goals (typically 2–4), the approaches or \
modalities to be used, anticipated session frequency, and any referrals or \
adjunct services. "Tentative" distinguishes this from the formal Treatment \
Plan — keep it high-level and brief; detailed goals and interventions \
belong in the separate Treatment Plan form.
- **Involvement** — textarea. Per TheraNest: "who will be involved in \
treatment?" Name each participant and their role (e.g., individual client, \
partner, family members, parent/caregiver) and any collateral contacts \
being coordinated with (other providers, case managers, physicians, school \
personnel). Note the session format this implies (individual, couples, \
family, collateral).
- **Treatment Length** — text. Expected duration of treatment (e.g., \
"6 months," "12 sessions").
- **Is Client Appropriate for Agency Services?** — Two-part field:
    - Dropdown: Yes or No.
    - **Explanation** — textarea. If Yes, briefly state why the client is \
appropriate for the agency's services. If No, explain and include referral \
resources.
- **Special Needs of Client** — Per TheraNest: "Eg Need For Interpreter, \
Interpreter For The Deaf, Religious Consultant, Etc. If yes, what?" \
Two-part field:
    - Dropdown: None, Yes, or No.
    - **Explanation** — textarea. If Yes, describe the specific need(s) \
(e.g., interpreter, ASL interpreter, religious or cultural consultant, \
accessibility accommodations). If None or No, state that no special needs \
were identified.
- **Cultural Variables?** — Two-part field:
    - Dropdown: None, Yes, or No.
    - **Explanation** — textarea. If Yes, describe cultural factors \
relevant to treatment. If None or No, state that no treatment-relevant \
cultural factors were identified.
- **Educational or Vocational Problems or Needs** — Two-part field:
    - Dropdown: None, Yes, or No.
    - **Explanation** — textarea. If Yes, describe the educational or \
vocational problem(s) or need(s). If None or No, state that no educational \
or vocational problems or needs were identified.
"""
