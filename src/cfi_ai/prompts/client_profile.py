"""Client Profile guidance (internal reference, drives progress-note compliance)."""

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
