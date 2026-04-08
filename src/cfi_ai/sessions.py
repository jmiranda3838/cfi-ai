"""On-disk persistence for chat sessions.

Each session is one JSON file under ``~/.config/cfi-ai/sessions/``. Sessions
are scoped per-workspace at list time by storing the workspace root path in
every session file. Serialization relies on google-genai types being pydantic
v2 models: ``Content.model_dump(mode="json")`` produces a JSON-safe dict
(including base64 for any ``Part.inline_data.data`` bytes), and
``Content.model_validate`` reconstructs typed objects ready to send back into
the Gemini API.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from google.genai import types

if TYPE_CHECKING:
    from cfi_ai.workspace import Workspace

_log = logging.getLogger(__name__)

SESSIONS_DIR = Path.home() / ".config" / "cfi-ai" / "sessions"

# Sessions older than this are deleted on startup and at list time. This
# bounds PHI exposure for client-facing conversations that may be stored in
# these files and keeps SESSIONS_DIR from growing without limit.
PRUNE_MAX_AGE_DAYS = 30


@dataclass
class SessionMeta:
    """Lightweight metadata for a saved session, used by the /resume menu."""

    id: str
    path: Path
    updated_at: float
    first_user_message: str
    message_count: int


def _extract_text(content: types.Content) -> str | None:
    """Return the first text part from a Content, or None."""
    if not content.parts:
        return None
    for part in content.parts:
        text = getattr(part, "text", None)
        if text:
            return text
    return None


class SessionStore:
    """Manages one cfi-ai session on disk.

    A single instance represents the current in-flight session. Call
    :meth:`save` after each completed turn to persist ``messages`` to
    ``self._path``. On :meth:`adopt`, the instance re-points itself at an
    existing session file so subsequent saves overwrite it — used by
    ``/resume`` to continue an earlier conversation in place.
    """

    def __init__(self, workspace: Workspace) -> None:
        # Normalize the workspace root so symlinked / tilde / trailing-slash
        # variants all match the same stored string in list_for_workspace.
        self._workspace_root = str(Path(workspace.root).resolve())
        ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        self.session_id = f"{ts}-{uuid.uuid4().hex[:6]}"
        self._path = SESSIONS_DIR / f"{self.session_id}.json"
        self._created_at = time.time()
        self._first_user_message: str | None = None
        # Populated by adopt() from the on-disk session payload so the agent
        # loop can seed a fresh CostTracker after /resume. None for new
        # sessions or sessions saved before this field existed.
        self.usage: dict | None = None

    def reset(self, workspace: Workspace) -> None:
        """Re-initialize this store as a brand-new session in ``workspace``.

        Used by ``/clear`` so that turns after a clear write to a fresh
        session file rather than overwriting the prior session's JSON.
        """
        self.__init__(workspace)

    def adopt(self, session_id: str, path: Path) -> None:
        """Re-point this store at an existing session file."""
        self.session_id = session_id
        self._path = path
        # Preserve created_at from the loaded file if readable; otherwise keep
        # our fresh timestamp. Best-effort — swallow any error so a corrupt
        # file can never crash the agent.
        try:
            data = json.loads(path.read_text())
            self._created_at = float(data.get("created_at", self._created_at))
            self._first_user_message = data.get("first_user_message") or None
            self.usage = data.get("usage") or None
        except Exception:
            _log.debug("session_adopt_read_failed path=%s", path, exc_info=True)

    def save(self, messages: list[types.Content], usage: dict | None = None) -> None:
        """Write the current conversation state to disk.

        Silently no-ops if ``messages`` is empty or any error occurs — session
        persistence must never crash the agent loop. ``usage`` is the
        ``CostTracker.to_dict()`` payload (or ``None``) and is persisted under
        the top-level ``"usage"`` key so /resume can restore running totals.
        """
        if not messages:
            return
        try:
            # Lazily capture the first user text for menu previews.
            if self._first_user_message is None:
                for msg in messages:
                    if msg.role == "user":
                        text = _extract_text(msg)
                        if text:
                            self._first_user_message = text.strip()
                            break

            serialized = [m.model_dump(mode="json") for m in messages]
            payload = {
                "id": self.session_id,
                "workspace": self._workspace_root,
                "created_at": self._created_at,
                "updated_at": time.time(),
                "first_user_message": self._first_user_message or "",
                "messages": serialized,
            }
            if usage is not None:
                payload["usage"] = usage

            SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(self._path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload))
            tmp.replace(self._path)
        except Exception:
            _log.debug("session_save_failed id=%s", self.session_id, exc_info=True)

    @staticmethod
    def prune_expired(max_age_days: int = PRUNE_MAX_AGE_DAYS) -> int:
        """Delete session files whose ``updated_at`` is older than the cutoff.

        Uses the ``updated_at`` field in the JSON body (not the filesystem
        mtime) so the cutoff is deterministic and survives backup/restore.
        Best-effort — any error on any individual file is swallowed so this
        can never crash the agent. Returns the number of files pruned.
        """
        if not SESSIONS_DIR.exists():
            return 0
        cutoff = time.time() - (max_age_days * 86400)
        pruned = 0
        for path in SESSIONS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if float(data.get("updated_at", 0.0)) < cutoff:
                    path.unlink()
                    pruned += 1
            except Exception:
                _log.debug("session_prune_skip path=%s", path, exc_info=True)
                continue
        if pruned:
            _log.debug("session_prune_complete count=%d", pruned)
        return pruned

    @staticmethod
    def list_for_workspace(workspace: Workspace) -> list[SessionMeta]:
        """Return sessions created in the given workspace, newest first.

        Runs ``prune_expired`` first so the menu never offers a session that's
        about to be deleted.
        """
        SessionStore.prune_expired()
        if not SESSIONS_DIR.exists():
            return []
        target = str(Path(workspace.root).resolve())
        results: list[SessionMeta] = []
        for path in SESSIONS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("workspace") != target:
                continue
            try:
                results.append(
                    SessionMeta(
                        id=str(data["id"]),
                        path=path,
                        updated_at=float(data.get("updated_at", 0.0)),
                        first_user_message=str(data.get("first_user_message") or ""),
                        message_count=len(data.get("messages") or []),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        results.sort(key=lambda m: m.updated_at, reverse=True)
        return results

    @staticmethod
    def load(path: Path) -> list[types.Content]:
        """Reconstruct a list of Content objects from a session file."""
        data = json.loads(path.read_text())
        raw = data.get("messages") or []
        return [types.Content.model_validate(d) for d in raw]
