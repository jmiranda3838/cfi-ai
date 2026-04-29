"""Tests for the /notify slash map handler."""

from unittest.mock import MagicMock

from cfi_ai.config import Config, _load_config_file, _write_toml
from cfi_ai.maps.notify import handle_notify
from cfi_ai.workspace import Workspace


def _make_config() -> Config:
    return Config(
        project="p",
        location="global",
        model="gemini-3-flash-preview",
        max_tokens=8192,
        notifications_popup_enabled=False,
        notifications_sound_enabled=False,
    )


def test_handle_notify_cancel_leaves_settings_unchanged(tmp_path, monkeypatch):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "p", "location": "global"},
            "model": {"name": "gemini-3-flash-preview", "max_tokens": 8192},
            "notifications": {"popup_enabled": False, "sound_enabled": False},
        },
    )
    monkeypatch.setattr("cfi_ai.config.CONFIG_PATH", cfg)

    ui = MagicMock()
    ui.prompt_notification_select.return_value = None
    ws = Workspace(str(tmp_path))
    store = MagicMock()

    result = handle_notify(None, ui, ws, store, _make_config())

    assert result.handled is True
    assert result.updated_config is None
    assert _load_config_file(cfg)["notifications"] == {
        "popup_enabled": False,
        "sound_enabled": False,
    }
    ui.print_info.assert_called_once()
    assert "unchanged" in ui.print_info.call_args[0][0].lower()


def test_handle_notify_toggle_popup_persists_and_returns_updated_config(tmp_path, monkeypatch):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "p", "location": "global"},
            "model": {"name": "gemini-3-flash-preview", "max_tokens": 8192},
            "notifications": {"popup_enabled": False, "sound_enabled": False},
        },
    )
    monkeypatch.setattr("cfi_ai.config.CONFIG_PATH", cfg)

    ui = MagicMock()
    ui.prompt_notification_select.return_value = "toggle_popup"
    ws = Workspace(str(tmp_path))
    store = MagicMock()

    result = handle_notify(None, ui, ws, store, _make_config())

    assert result.handled is True
    assert result.updated_config is not None
    assert result.updated_config.notifications_popup_enabled is True
    assert result.updated_config.notifications_sound_enabled is False
    persisted = _load_config_file(cfg)
    assert persisted["notifications"] == {
        "popup_enabled": True,
        "sound_enabled": False,
    }
    assert persisted["project"]["id"] == "p"
    ui.print_info.assert_called_once()
    rendered = ui.print_info.call_args[0][0]
    assert "popup: on" in rendered.lower()
    assert "sound: off" in rendered.lower()


def test_notify_map_is_registered():
    from cfi_ai.maps import MAPS, get_map_descriptions

    assert "notify" in MAPS
    assert "notify" in get_map_descriptions()
