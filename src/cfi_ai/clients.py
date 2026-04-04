"""Client path helpers for the clients/ directory structure."""

from __future__ import annotations

import re

from cfi_ai.workspace import Workspace


def list_clients(workspace: Workspace) -> list[str]:
    """Return sorted client-id list from clients/ subdirectories."""
    clients_dir = workspace.root / "clients"
    if not clients_dir.is_dir():
        return []
    return sorted(
        d.name for d in clients_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    )


def sanitize_client_id(name: str) -> str:
    """Convert a display name to a client-id slug. 'Jane Doe' -> 'jane-doe'."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug
