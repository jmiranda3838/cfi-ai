"""Tests for macOS completed-turn notifications."""

from unittest.mock import patch

from cfi_ai.config import Config
from cfi_ai.notifications import (
    _NOTIFICATION_BODY,
    _NOTIFICATION_SOUND_PATH,
    _NOTIFICATION_TITLE,
    _play_sound,
    _show_popup,
    notify_turn_complete,
)


def _make_config(*, popup: bool, sound: bool) -> Config:
    return Config(
        project="p",
        location="global",
        model="gemini-3-flash-preview",
        max_tokens=8192,
        notifications_popup_enabled=popup,
        notifications_sound_enabled=sound,
    )


def test_notify_turn_complete_popup_only():
    config = _make_config(popup=True, sound=False)
    with patch("sys.platform", "darwin"), patch(
        "cfi_ai.notifications._show_popup"
    ) as mock_popup, patch("cfi_ai.notifications._play_sound") as mock_sound:
        notify_turn_complete(config)
    mock_popup.assert_called_once_with(
        title=_NOTIFICATION_TITLE,
        body=_NOTIFICATION_BODY,
    )
    mock_sound.assert_not_called()


def test_notify_turn_complete_sound_only():
    config = _make_config(popup=False, sound=True)
    with patch("sys.platform", "darwin"), patch(
        "cfi_ai.notifications._show_popup"
    ) as mock_popup, patch("cfi_ai.notifications._play_sound") as mock_sound:
        notify_turn_complete(config)
    mock_popup.assert_not_called()
    mock_sound.assert_called_once_with(sound_path=_NOTIFICATION_SOUND_PATH)


def test_notify_turn_complete_noop_when_disabled():
    config = _make_config(popup=False, sound=False)
    with patch("sys.platform", "darwin"), patch(
        "cfi_ai.notifications._show_popup"
    ) as mock_popup, patch("cfi_ai.notifications._play_sound") as mock_sound:
        notify_turn_complete(config)
    mock_popup.assert_not_called()
    mock_sound.assert_not_called()


def test_notify_turn_complete_noop_off_macos():
    config = _make_config(popup=True, sound=True)
    with patch("sys.platform", "linux"), patch(
        "cfi_ai.notifications._show_popup"
    ) as mock_popup, patch("cfi_ai.notifications._play_sound") as mock_sound:
        notify_turn_complete(config)
    mock_popup.assert_not_called()
    mock_sound.assert_not_called()


def test_notification_helpers_swallow_failures():
    with patch("cfi_ai.notifications.subprocess.run", side_effect=OSError):
        _show_popup(title=_NOTIFICATION_TITLE, body=_NOTIFICATION_BODY)
        _play_sound(sound_path=_NOTIFICATION_SOUND_PATH)


def test_notification_popup_text_is_generic():
    config = _make_config(popup=True, sound=False)
    with patch("sys.platform", "darwin"), patch(
        "cfi_ai.notifications._show_popup"
    ) as mock_popup:
        notify_turn_complete(config)
    title = mock_popup.call_args.kwargs["title"]
    body = mock_popup.call_args.kwargs["body"]
    assert title == "cfi-ai"
    assert body == "Response complete."
    assert "client" not in body.lower()
