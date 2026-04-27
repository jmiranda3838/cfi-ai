"""Schema for the per-client profile document — the canonical location for client-level facts cfi-ai needs across sessions. Clinical guidance and payer-compliance rules live in separate modules."""

CLIENT_PROFILE_GUIDANCE = """\
## Client Profile Guidance (Internal Reference)

> **Note:** This profile is an internal cfi-ai reference — it does not live \
in TheraNest. The information captured here is loaded as client context and \
feeds the TheraNest-bound documents cfi-ai generates (progress notes, \
treatment plans).

Write a concise, reusable profile summary:
- **Demographics**: Age, pronouns, relationship status, living situation, occupation (as disclosed)
- **Presenting Problems**: Brief summary of current concerns
- **Psychosocial Context**: Key relationships, stressors, supports
- **Medical / Substance History**: Relevant medical conditions, medications, substance use
- **Strengths**: Client strengths, values, supports, and skills relevant to the work
- **Cultural Considerations**: Cultural identity, relevant cultural factors for treatment

## Billing & Provider Information

> **Note:** Per-client billing and provider context. Capture what's known; \
if any field is missing or unknown, leave it as `[unknown]` and the session \
workflow will backfill via `interview` before the next progress note.

- **Payer**: Insurance plan or payment source. Examples: "Optum EWS/EAP", \
"Optum Commercial", "Anthem PPO", "Aetna", "Self-pay", "Sliding scale".
- **Authorization Number**: Populate when the payer requires authorization \
(e.g., EAP/EWS); otherwise blank or `N/A`. Example: "AUTH-2026-04829".
- **Total Authorized Sessions**: Integer count of sessions covered by the \
current authorization. Example: "5". Use "N/A" for non-authorized payers.
- **Authorization Period**: Start and end dates of the current authorization. \
Example: "2026-01-15 to 2026-04-15". Use "N/A" if not applicable.
- **Default Modality**: Typical session delivery method for this client. \
One of: `In-Person`, `Video`, `Phone`.
- **Rendering Provider**: The clinician seeing the client. Example: \
"Jonathan Miranda, AMFT" or "Chris Hoff, LMFT".
- **Supervised**: `Yes` or `No`. Yes for Associate-level clinicians (AMFT, \
ACSW, APCC) practicing under supervision.
- **Supervisor**: Only populate when Supervised = Yes. Format: \
"Name, license type, NPI #". Example: "Chris Hoff, LMFT, NPI 1760705818".
- **Supervision Format**: How supervision is conducted for this case. Options: \
`live observation`, `recording review`, `individual supervision discussion`.
- **Service Setting / POS**: Place of service code for billing. Example: \
"Office (POS 11)" or "Telehealth - Patient Home (POS 10)" or \
"Telehealth - Other than Patient Home (POS 02)".
"""
