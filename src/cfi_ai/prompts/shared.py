"""Shared prompt-building utilities used across the clinical prompt modules.

All document-specific content has moved to per-document modules:
- `narrative_therapy.py` — Narrative Therapy principles
- `initial_assessment.py` — TheraNest Initial Assessment & Diagnostic Codes form spec
- `treatment_plan.py` — TheraNest Part 7 guidance + intervention master list
- `client_profile.py` — internal reference (drives progress-note compliance)
- `progress_note.py` — both ongoing and intake variants of the TheraNest 30-field note

This module retains only cross-map utilities (shared execution instructions and
a small text-indentation helper).
"""


def indent_block(text: str, prefix: str) -> str:
    """Prefix each non-empty line of ``text`` with ``prefix``.

    Used to nest a multi-line block (like the TheraNest intervention master
    list) cleanly underneath a Markdown bullet that requires a specific indent.
    """
    return "\n".join(f"{prefix}{line}" if line else line for line in text.splitlines())


CRITICAL_INSTRUCTIONS = """\
## Working with Clinical Maps

A loaded map prompt contains reference content and a numbered Phase \
workflow (with "Save ALL files" / "immediately proceed" directives). \
Loading the map does not mean you must execute the workflow — the Phase \
blocks apply only when execution is the intent (see "Available Clinical \
Maps" above for the reference-vs-execution distinction).

In reference mode, you MAY load specific client files with `attach_path` \
or `run_command` if you need them to answer well. What you MUST NOT do in \
reference mode: auto-execute the canned phase sequence, bulk-load every \
file the workflow normally touches, or call `write_file` / `apply_patch` \
unless the user explicitly confirms they want the documents produced. When \
in doubt about which mode applies, default to reference mode: answer the \
question first, then ask whether they'd like to run the workflow.

When you are executing a workflow:

- Do NOT narrate the map or reproduce document content in your response text.
- Keep free-text responses to 2-3 sentences maximum. Proceed directly to tool calls.
- The user reviews all file content in the approval step — do not preview it in chat.
"""


DOCUMENTATION_PRINCIPLES = """\
## Documentation Principles

These principles shape *how* the TheraNest fields are written. They do NOT \
introduce new fields or override the field-level structure described in the \
form specs — they narrow the writing posture inside each existing field.

- **Audience.** Write as if a payer auditor and (worst case) a subpoena will \
read it. Both pull for the HIPAA "minimum necessary" standard: no more \
clinical narrative than the chart needs to defend medical necessity, billing, \
risk, and continuity of care.
- **Specific where it defends necessity.** Diagnosis, risk findings, \
measurable progress indicators, interventions actually used, and the \
medical-necessity rationale must be specific and tied to the session at \
hand. Vagueness in these elements is a compliance failure.
- **Minimum-necessary everywhere else.** Client narrative, family context, \
third-party identities, trauma and substance-use history, and direct quotes \
belong only at the level needed to support the clinical reasoning above. If \
a detail is not load-bearing for necessity, billing, risk, or coordination \
of care, omit it rather than rewrite it into a softer form. When a field \
spec says to "include direct quotes where clinically relevant" or to "use \
the client's own words," apply that only when the exact wording is itself \
clinically load-bearing (e.g. an SI/HI statement, a mandated-reporting \
trigger, or a phrase that is the unique outcome being tracked).
- **Objective over narrative.** Document observable behavior, MSE findings, \
and clinical conclusions — not the client's life story. Scene-painting, \
session-by-session storytelling, and biographical color do not belong in \
the chart.
- **Privacy posture for third parties.** Refer to family, partners, \
co-workers, and other named individuals by role, not by name. Avoid \
identifying detail (workplace, schools, addresses, dates of specific \
events outside the chart's scope) unless required for risk documentation \
or mandated reporting.
- **Vague is correct for content; never for clinical conclusions.** "Client \
discussed conflict with a family member" is acceptable. "Client reports \
continued symptom reduction" without a measurable indicator is not.
"""
