"""Best-effort local notifications for completed assistant turns."""

from __future__ import annotations

import logging
import subprocess
import sys

from cfi_ai.config import Config

_log = logging.getLogger(__name__)

_NOTIFICATION_TITLE = "cfi-ai"
_NOTIFICATION_BODY = "Response complete."
_NOTIFICATION_SOUND_PATH = "/System/Library/Sounds/Glass.aiff"


def _run_best_effort(argv: list[str]) -> None:
    try:
        subprocess.run(
            argv,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        _log.debug("notification_command_failed cmd=%s error=%s", argv[0], type(e).__name__)


def _show_popup(*, title: str, body: str) -> None:
    _run_best_effort(
        [
            "osascript",
            "-e",
            f'display notification "{body}" with title "{title}"',
        ]
    )


def _play_sound(*, sound_path: str) -> None:
    _run_best_effort(["afplay", sound_path])


def notify_turn_complete(config: Config) -> None:
    """Fire macOS completion notifications based on user preferences."""
    if sys.platform != "darwin":
        return
    if not config.notifications_popup_enabled and not config.notifications_sound_enabled:
        return
    if config.notifications_popup_enabled:
        _show_popup(title=_NOTIFICATION_TITLE, body=_NOTIFICATION_BODY)
    if config.notifications_sound_enabled:
        _play_sound(sound_path=_NOTIFICATION_SOUND_PATH)
