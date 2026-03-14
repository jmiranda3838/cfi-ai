import os
import tomllib

import pytest
from unittest.mock import patch

from cfi_ai.config import (
    Config,
    _load_config_file,
    _write_toml,
    _run_first_time_setup,
)

# ── Existing from_env tests ──────────────────────────────────────────


def test_from_env_defaults():
    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "my-project"}, clear=False):
        config = Config.from_env()
    assert config.project == "my-project"
    assert config.location == "global"
    assert config.model == "gemini-2.5-flash"
    assert config.max_tokens == 8192


def test_from_env_custom():
    env = {
        "GOOGLE_CLOUD_PROJECT": "custom-proj",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "CFI_AI_MODEL": "gemini-2.5-pro",
        "CFI_AI_MAX_TOKENS": "4096",
    }
    with patch.dict(os.environ, env, clear=False):
        config = Config.from_env()
    assert config.project == "custom-proj"
    assert config.location == "us-central1"
    assert config.model == "gemini-2.5-pro"
    assert config.max_tokens == 4096


def test_from_env_missing_project():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit):
            Config.from_env()


def test_frozen():
    config = Config(project="p", location="l", model="m", max_tokens=1)
    with pytest.raises(AttributeError):
        config.project = "other"


# ── Config file read/write ───────────────────────────────────────────


def test_load_config_file(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[project]\nid = "my-proj"\nlocation = "global"\n\n'
        '[model]\nname = "gemini-2.5-flash"\nmax_tokens = 8192\n'
    )
    data = _load_config_file(cfg)
    assert data["project"]["id"] == "my-proj"
    assert data["model"]["max_tokens"] == 8192


def test_load_config_file_missing(tmp_path):
    assert _load_config_file(tmp_path / "nope.toml") is None


def test_load_config_file_invalid(tmp_path):
    cfg = tmp_path / "bad.toml"
    cfg.write_text("not valid [[[ toml")
    assert _load_config_file(cfg) is None


def test_write_toml(tmp_path):
    cfg = tmp_path / "out.toml"
    data = {
        "project": {"id": "test-proj", "location": "us-east1"},
        "model": {"name": "gemini-2.5-pro", "max_tokens": 4096},
    }
    _write_toml(cfg, data)
    parsed = tomllib.loads(cfg.read_text())
    assert parsed == data


# ── Config.load ──────────────────────────────────────────────────────


def test_load_from_file(tmp_path):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "file-proj", "location": "eu-west1"},
            "model": {"name": "gemini-2.5-pro", "max_tokens": 2048},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.project == "file-proj"
    assert config.location == "eu-west1"
    assert config.model == "gemini-2.5-pro"
    assert config.max_tokens == 2048


def test_load_env_overrides_file(tmp_path):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "file-proj", "location": "global"},
            "model": {"name": "gemini-2.5-flash", "max_tokens": 8192},
        },
    )
    env = {"GOOGLE_CLOUD_PROJECT": "env-proj", "CFI_AI_MODEL": "gemini-2.5-pro"}
    with patch.dict(os.environ, env, clear=True):
        config = Config.load(config_path=cfg)
    assert config.project == "env-proj"
    assert config.location == "global"
    assert config.model == "gemini-2.5-pro"
    assert config.max_tokens == 8192


def test_load_triggers_setup_when_missing(tmp_path):
    cfg = tmp_path / "config.toml"
    inputs = iter(["auto-proj", "", "", ""])
    with patch.dict(os.environ, {}, clear=True):
        with patch("builtins.input", side_effect=inputs):
            config = Config.load(config_path=cfg)
    assert config.project == "auto-proj"
    assert cfg.exists()


# ── First-run setup ─────────────────────────────────────────────────


def test_first_run_setup(tmp_path):
    cfg = tmp_path / "config.toml"
    inputs = iter(["my-proj", "us-central1", "gemini-2.5-pro", "4096"])
    with patch("builtins.input", side_effect=inputs):
        data = _run_first_time_setup(path=cfg)
    assert data["project"]["id"] == "my-proj"
    assert data["project"]["location"] == "us-central1"
    assert data["model"]["name"] == "gemini-2.5-pro"
    assert data["model"]["max_tokens"] == 4096
    # verify file was written and is valid TOML
    parsed = tomllib.loads(cfg.read_text())
    assert parsed == data


def test_first_run_setup_defaults(tmp_path):
    cfg = tmp_path / "config.toml"
    # only project ID is provided; rest use defaults (empty input)
    inputs = iter(["my-proj", "", "", ""])
    with patch("builtins.input", side_effect=inputs):
        data = _run_first_time_setup(path=cfg)
    assert data["project"]["id"] == "my-proj"
    assert data["project"]["location"] == "global"
    assert data["model"]["name"] == "gemini-2.5-flash"
    assert data["model"]["max_tokens"] == 8192
