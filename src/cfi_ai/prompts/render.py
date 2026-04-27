"""Shared rendering helpers for clinical map prompts.

Both `tools/activate_map.py` (implicit LLM activation) and `maps/*.py`
(explicit slash invocation) render the same map prompt templates. Keeping the
dispatch in one place avoids the two paths drifting.
"""

from __future__ import annotations

import datetime

from cfi_ai.prompts.compliance import COMPLIANCE_PROMPT
from cfi_ai.prompts.intake import INTAKE_PROMPT
from cfi_ai.prompts.progress_note import PROGRESS_NOTE_GUIDANCE
from cfi_ai.prompts.session import SESSION_MAP_PROMPT
from cfi_ai.prompts.tp_review import TP_REVIEW_PROMPT

VALID_MAPS: tuple[str, ...] = (
    "intake",
    "session",
    "compliance",
    "tp-review",
)


def render_map_prompt(map_name: str, *, date: str | None = None) -> str:
    """Render a map's execution prompt with `{date}` substituted."""
    today = date or datetime.date.today().isoformat()
    if map_name == "intake":
        return INTAKE_PROMPT.format(date=today)
    if map_name == "session":
        return SESSION_MAP_PROMPT.format(
            date=today,
            progress_note_guidance=PROGRESS_NOTE_GUIDANCE.format(date=today),
        )
    if map_name == "compliance":
        return COMPLIANCE_PROMPT.format(date=today)
    if map_name == "tp-review":
        return TP_REVIEW_PROMPT.format(date=today)
    raise ValueError(f"Unhandled map: {map_name}")
