"""The /notify slash map."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from cfi_ai.config import Config, persist_notifications_settings
from cfi_ai.maps import MapResult, register_map

if TYPE_CHECKING:
    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


def _format_state(config: Config) -> str:
    popup = "on" if config.notifications_popup_enabled else "off"
    sound = "on" if config.notifications_sound_enabled else "off"
    return f"Notifications updated. Popup: {popup}. Sound: {sound}."


@register_map(
    "notify",
    description="Manage popup and sound notifications for completed turns",
)
def handle_notify(
    args: str | None,
    ui: UI,
    workspace: Workspace,
    session_store: SessionStore,
    config: Config | None = None,
) -> MapResult:
    if config is None:
        return MapResult(error="Notifications are unavailable because config is missing.")

    action = ui.prompt_notification_select(
        popup_enabled=config.notifications_popup_enabled,
        sound_enabled=config.notifications_sound_enabled,
    )
    if action is None or action == "cancel":
        ui.print_info("Notification settings unchanged.")
        return MapResult(handled=True)

    popup_enabled = config.notifications_popup_enabled
    sound_enabled = config.notifications_sound_enabled

    if action == "toggle_popup":
        popup_enabled = not popup_enabled
    elif action == "toggle_sound":
        sound_enabled = not sound_enabled
    elif action == "enable_both":
        popup_enabled = True
        sound_enabled = True
    elif action == "disable_both":
        popup_enabled = False
        sound_enabled = False
    else:
        return MapResult(error=f"Unknown notification action: {action}")

    updated = replace(
        config,
        notifications_popup_enabled=popup_enabled,
        notifications_sound_enabled=sound_enabled,
    )
    persist_notifications_settings(updated)
    ui.print_info(_format_state(updated))
    return MapResult(handled=True, updated_config=updated)
