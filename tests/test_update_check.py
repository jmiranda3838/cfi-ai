"""Tests for the update checker."""

import json
import time
from unittest.mock import patch

from cfi_ai.update_check import (
    _parse_version,
    _read_cache,
    _write_cache,
    check_for_update,
    CHECK_INTERVAL,
)


def test_parse_version():
    assert _parse_version("0.8.0") == (0, 8, 0)
    assert _parse_version("v1.2.3") == (1, 2, 3)
    assert _parse_version("10.0.0") == (10, 0, 0)


def test_compare_versions():
    assert _parse_version("0.9.0") > _parse_version("0.8.0")
    assert _parse_version("0.8.0") == _parse_version("0.8.0")
    assert _parse_version("0.7.0") < _parse_version("0.8.0")
    assert _parse_version("1.0.0") > _parse_version("0.99.99")


def test_cache_round_trip(tmp_path):
    cache_file = tmp_path / "update-check.json"
    with patch("cfi_ai.update_check.CACHE_FILE", cache_file):
        _write_cache("0.9.0")
        cache = _read_cache()
        assert cache is not None
        assert cache["latest_version"] == "0.9.0"
        assert isinstance(cache["last_check"], float)


def test_read_cache_missing(tmp_path):
    cache_file = tmp_path / "nonexistent.json"
    with patch("cfi_ai.update_check.CACHE_FILE", cache_file):
        assert _read_cache() is None


def test_read_cache_corrupt(tmp_path):
    cache_file = tmp_path / "update-check.json"
    cache_file.write_text("not json")
    with patch("cfi_ai.update_check.CACHE_FILE", cache_file):
        assert _read_cache() is None


def test_fresh_cache_skips_refresh(tmp_path):
    """A fresh cache should not spawn a refresh subprocess."""
    cache_file = tmp_path / "update-check.json"
    cache_file.write_text(
        json.dumps({"last_check": time.time(), "latest_version": "0.9.0"})
    )
    with (
        patch("cfi_ai.update_check.CACHE_FILE", cache_file),
        patch("cfi_ai.update_check._spawn_refresh") as mock_spawn,
    ):
        msg = check_for_update("0.8.0")
        mock_spawn.assert_not_called()
        assert msg is not None
        assert "0.9.0" in msg


def test_expired_cache_spawns_refresh(tmp_path):
    """An expired cache should spawn a refresh subprocess."""
    cache_file = tmp_path / "update-check.json"
    old_time = time.time() - CHECK_INTERVAL - 100
    cache_file.write_text(
        json.dumps({"last_check": old_time, "latest_version": "0.9.0"})
    )
    with (
        patch("cfi_ai.update_check.CACHE_FILE", cache_file),
        patch("cfi_ai.update_check._spawn_refresh") as mock_spawn,
    ):
        msg = check_for_update("0.8.0")
        mock_spawn.assert_called_once()
        # Still returns message from stale cache
        assert msg is not None
        assert "0.9.0" in msg


def test_no_cache_spawns_refresh(tmp_path):
    """Missing cache should spawn a refresh and return None."""
    cache_file = tmp_path / "nonexistent.json"
    with (
        patch("cfi_ai.update_check.CACHE_FILE", cache_file),
        patch("cfi_ai.update_check._spawn_refresh") as mock_spawn,
    ):
        msg = check_for_update("0.8.0")
        mock_spawn.assert_called_once()
        assert msg is None


def test_network_error_silent(tmp_path):
    """Popen failure should not raise and should not crash."""
    cache_file = tmp_path / "nonexistent.json"
    with (
        patch("cfi_ai.update_check.CACHE_FILE", cache_file),
        patch("cfi_ai.update_check._spawn_refresh", side_effect=OSError("boom")),
    ):
        msg = check_for_update("0.8.0")
        assert msg is None


def test_no_message_when_current(tmp_path):
    """Same version should return no update message."""
    cache_file = tmp_path / "update-check.json"
    cache_file.write_text(
        json.dumps({"last_check": time.time(), "latest_version": "0.8.0"})
    )
    with patch("cfi_ai.update_check.CACHE_FILE", cache_file):
        msg = check_for_update("0.8.0")
        assert msg is None


def test_no_message_when_ahead(tmp_path):
    """Local version newer than remote should return no message."""
    cache_file = tmp_path / "update-check.json"
    cache_file.write_text(
        json.dumps({"last_check": time.time(), "latest_version": "0.7.0"})
    )
    with patch("cfi_ai.update_check.CACHE_FILE", cache_file):
        msg = check_for_update("0.8.0")
        assert msg is None


def test_message_when_behind(tmp_path):
    """Cached newer version should return an update message."""
    cache_file = tmp_path / "update-check.json"
    cache_file.write_text(
        json.dumps({"last_check": time.time(), "latest_version": "1.0.0"})
    )
    with patch("cfi_ai.update_check.CACHE_FILE", cache_file):
        msg = check_for_update("0.8.0")
        assert msg is not None
        assert "1.0.0" in msg
        assert "pipx upgrade" in msg
