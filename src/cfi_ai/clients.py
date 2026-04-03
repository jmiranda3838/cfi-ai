"""Client path helpers for the clients/ directory structure."""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from cfi_ai.workspace import Workspace


def list_clients(workspace: Workspace) -> list[str]:
    """Return sorted client-id list from clients/ subdirectories."""
    clients_dir = workspace.root / "clients"
    if not clients_dir.is_dir():
        return []
    return sorted(
        d.name for d in clients_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    )


def load_client_context(workspace: Workspace, client_id: str) -> str:
    """Read profile/current.md and treatment-plan/current.md for a client."""
    base = workspace.root / "clients" / client_id
    sections: list[str] = []
    for subdir, label in [
        ("profile", "Profile"),
        ("treatment-plan", "Treatment Plan"),
    ]:
        current = base / subdir / "current.md"
        if current.is_file():
            sections.append(f"### {label}\n{current.read_text()}")
    return "\n\n".join(sections) if sections else ""


def load_compliance_context(workspace: Workspace, client_id: str) -> str:
    """Load all clinical files for a compliance review."""
    base = workspace.root / "clients" / client_id
    sections: list[str] = []

    # Profile
    profile = base / "profile" / "current.md"
    if profile.is_file():
        sections.append(f"### Client Profile\n{profile.read_text()}")

    # Treatment Plan
    tp = base / "treatment-plan" / "current.md"
    if tp.is_file():
        sections.append(f"### Current Treatment Plan\n{tp.read_text()}")

    # Intake Assessment(s)
    intake_dir = base / "intake"
    if intake_dir.is_dir():
        for f in sorted(intake_dir.glob("*-initial-assessment.md")):
            sections.append(f"### Initial Assessment ({f.name})\n{f.read_text()}")

    # Session Progress Notes — all, sorted chronologically
    sessions_dir = base / "sessions"
    if sessions_dir.is_dir():
        notes = sorted(sessions_dir.glob("*-progress-note.md"))
        for f in notes:
            sections.append(f"### Progress Note ({f.name})\n{f.read_text()}")
        sections.append(f"\n**Total session count (progress notes): {len(notes)}**")

    # Wellness Assessments
    wa_dir = base / "wellness-assessments"
    if wa_dir.is_dir():
        wa_files = sorted(wa_dir.glob("*-wellness-assessment.md"))
        for f in wa_files:
            sections.append(f"### Wellness Assessment ({f.name})\n{f.read_text()}")
        wa_count = len(wa_files)
    else:
        wa_count = 0
    sections.append(f"**Wellness assessment administrations: {wa_count}**")

    return "\n\n---\n\n".join(sections) if sections else ""


def load_wa_history(workspace: Workspace, client_id: str) -> str:
    """Read all wellness-assessments/*-wellness-assessment.md files, sorted chronologically."""
    wa_dir = workspace.root / "clients" / client_id / "wellness-assessments"
    if not wa_dir.is_dir():
        return ""
    sections: list[str] = []
    for f in sorted(wa_dir.glob("*-wellness-assessment.md")):
        sections.append(f"### Wellness Assessment ({f.name})\n{f.read_text()}")
    return "\n\n".join(sections)


def count_wa_files(workspace: Workspace, client_id: str) -> int:
    """Count *-wellness-assessment.md files for a client."""
    wa_dir = workspace.root / "clients" / client_id / "wellness-assessments"
    if not wa_dir.is_dir():
        return 0
    return len(list(wa_dir.glob("*-wellness-assessment.md")))


def count_session_notes(workspace: Workspace, client_id: str) -> int:
    """Count *-progress-note.md files for a client."""
    sessions_dir = workspace.root / "clients" / client_id / "sessions"
    if not sessions_dir.is_dir():
        return 0
    return len(list(sessions_dir.glob("*-progress-note.md")))


def get_tp_review_date(workspace: Workspace, client_id: str) -> datetime.date | None:
    """Extract the TP review due date from treatment-plan/current.md.

    Looks for '**Review Date**' first (set by /tp-review).
    Falls back to '**Initiation Date**' + 90 days (initial TP from /intake).
    Returns None if neither is found or the file doesn't exist.
    """
    tp_file = workspace.root / "clients" / client_id / "treatment-plan" / "current.md"
    if not tp_file.is_file():
        return None
    content = tp_file.read_text()

    # Try Review Date first (set by /tp-review)
    match = re.search(r"\*\*Review Date\*\*.*?(\d{4}-\d{2}-\d{2})", content)
    if match:
        try:
            return datetime.date.fromisoformat(match.group(1))
        except ValueError:
            pass

    # Fall back to Initiation Date + 90 days (initial TP)
    match = re.search(r"\*\*Initiation Date\*\*.*?(\d{4}-\d{2}-\d{2})", content)
    if match:
        try:
            return datetime.date.fromisoformat(match.group(1)) + datetime.timedelta(days=90)
        except ValueError:
            pass

    return None


def build_session_reminders(workspace: Workspace, client_id: str) -> str:
    """Compute WA and treatment-plan reminders for a session workflow."""
    reminders: list[str] = []

    wa_count = count_wa_files(workspace, client_id)
    note_count = count_session_notes(workspace, client_id)

    if wa_count == 0:
        reminders.append(
            "- No Wellness Assessment on file. "
            "Consider administering G22E02 before or during this session."
        )
    elif wa_count == 1 and 3 <= note_count + 1 <= 5:
        reminders.append(
            f"- Wellness Assessment re-administration may be due "
            f"(visit ~{note_count + 1}; 2nd WA recommended at visits 3-5)."
        )
    elif wa_count >= 2:
        wa_dir = workspace.root / "clients" / client_id / "wellness-assessments"
        wa_files = sorted(wa_dir.glob("*-wellness-assessment.md"))
        if wa_files:
            last_wa_date = wa_files[-1].name[:10]
            sessions_dir = workspace.root / "clients" / client_id / "sessions"
            notes_since = len([
                f for f in sessions_dir.glob("*-progress-note.md")
                if f.name[:10] > last_wa_date
            ]) if sessions_dir.is_dir() else 0
            if notes_since >= 5:
                reminders.append(
                    f"- Wellness Assessment may be due for re-administration "
                    f"({notes_since} sessions since last WA)."
                )

    review_date = get_tp_review_date(workspace, client_id)
    if review_date:
        days_until = (review_date - datetime.date.today()).days
        if days_until < 0:
            reminders.append(
                f"- Treatment Plan review is past due "
                f"(was due {review_date.isoformat()})."
            )
        elif days_until <= 14:
            reminders.append(
                f"- Treatment Plan review approaching "
                f"(due {review_date.isoformat()}, {days_until} days away)."
            )

    if not reminders:
        return ""
    return "## Clinical Reminders\n\n" + "\n".join(reminders) + "\n\n"


def sanitize_client_id(name: str) -> str:
    """Convert a display name to a client-id slug. 'Jane Doe' -> 'jane-doe'."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug
