"""Shared prompt-building utilities used across the clinical prompt modules.

All document-specific content has moved to per-document modules:
- `narrative_therapy.py` — Narrative Therapy principles
- `initial_assessment.py` — TheraNest Part 6 guidance
- `treatment_plan.py` — TheraNest Part 7 guidance + intervention master list
- `client_profile.py` — internal reference (drives progress-note compliance)
- `progress_note.py` — both ongoing and intake variants of the TheraNest 30-field note
- `wellness_assessment.py` — scoring rules and output format

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
## When Executing This Workflow

The rules below apply only when you are actively producing the documents this map \
describes. If the user is asking a question, comparing options, or thinking through \
a decision, treat the rest of this map as reference material and answer their \
question normally — ignore these execution rules.

- Do NOT narrate the map or reproduce document content in your response text.
- Keep free-text responses to 2-3 sentences maximum. Proceed directly to tool calls.
- The user reviews all file content in the approval step — do not preview it in chat.
"""
