import os
import tomllib

import pytest
from unittest.mock import patch

from cfi_ai.config import (
    Config,
    _DEPRECATED_MODELS,
    _load_config_file,
    _parse_bool_env,
    _parse_int_env,
    _write_toml,
    _run_first_time_setup,
    check_model_location,
)

# ── Existing from_env tests ──────────────────────────────────────────


def test_from_env_defaults():
    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "my-project"}, clear=False):
        config = Config.from_env()
    assert config.project == "my-project"
    assert config.location == "global"
    assert config.model == "gemini-3-flash-preview"
    assert config.max_tokens == 8192
    assert config.context_cache is True


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


def test_from_env_context_cache_disabled():
    env = {"GOOGLE_CLOUD_PROJECT": "my-project", "CFI_AI_CONTEXT_CACHE": "0"}
    with patch.dict(os.environ, env, clear=False):
        config = Config.from_env()
    assert config.context_cache is False


def test_from_env_context_cache_disabled_false():
    env = {"GOOGLE_CLOUD_PROJECT": "my-project", "CFI_AI_CONTEXT_CACHE": "false"}
    with patch.dict(os.environ, env, clear=False):
        config = Config.from_env()
    assert config.context_cache is False


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
            "project": {"id": "file-proj", "location": "global"},
            "model": {"name": "gemini-3-flash-preview", "max_tokens": 2048},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.project == "file-proj"
    assert config.location == "global"
    assert config.model == "gemini-3-flash-preview"
    assert config.max_tokens == 2048


def test_load_context_cache_default(tmp_path):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "file-proj", "location": "global"},
            "model": {"name": "gemini-3-flash-preview", "max_tokens": 8192},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.context_cache is True


def test_load_context_cache_disabled(tmp_path):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "file-proj", "location": "global"},
            "model": {"name": "gemini-3-flash-preview", "max_tokens": 8192},
        },
    )
    with patch.dict(os.environ, {"CFI_AI_CONTEXT_CACHE": "0"}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.context_cache is False


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
    inputs = iter(["auto-proj", "", "", "", ""])
    with patch.dict(os.environ, {}, clear=True):
        with patch("builtins.input", side_effect=inputs):
            config = Config.load(config_path=cfg)
    assert config.project == "auto-proj"
    assert cfg.exists()


def test_check_model_location_global_only_on_global_returns_none():
    assert check_model_location("gemini-3-flash-preview", "global") is None


def test_check_model_location_global_only_on_regional_returns_error():
    err = check_model_location("gemini-3-flash-preview", "us-central1")
    assert err is not None
    assert "gemini-3-flash-preview" in err
    assert "requires Vertex AI location 'global'" in err
    assert "us-central1" in err


def test_load_rejects_global_only_model_on_regional_endpoint(tmp_path, capsys):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "file-proj", "location": "us-central1"},
            "model": {"name": "gemini-3-flash-preview", "max_tokens": 8192},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit):
            Config.load(config_path=cfg)
    err = capsys.readouterr().err
    assert "gemini-3-flash-preview" in err
    assert "requires Vertex AI location 'global'" in err


def test_load_allows_global_only_model_on_global_endpoint(tmp_path):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "file-proj", "location": "global"},
            "model": {"name": "gemini-3-flash-preview", "max_tokens": 8192},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.location == "global"
    assert config.model == "gemini-3-flash-preview"


def test_load_allows_other_models_on_regional_endpoints(tmp_path):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "file-proj", "location": "us-central1"},
            "model": {"name": "some-regional-model", "max_tokens": 8192},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.location == "us-central1"
    assert config.model == "some-regional-model"


# ── First-run setup ─────────────────────────────────────────────────


def test_first_run_setup(tmp_path):
    cfg = tmp_path / "config.toml"
    inputs = iter(["my-proj", "us-central1", "gemini-2.5-pro", "4096", "64000"])
    with patch("builtins.input", side_effect=inputs):
        data = _run_first_time_setup(path=cfg)
    assert data["project"]["id"] == "my-proj"
    assert data["project"]["location"] == "us-central1"
    assert data["model"]["name"] == "gemini-2.5-pro"
    assert data["model"]["max_tokens"] == 4096
    assert data["model"]["max_context_tokens"] == 64000
    # verify file was written and is valid TOML
    parsed = tomllib.loads(cfg.read_text())
    assert parsed == data


def test_first_run_setup_defaults(tmp_path):
    cfg = tmp_path / "config.toml"
    # only project ID is provided; rest use defaults (empty input)
    inputs = iter(["my-proj", "", "", "", ""])
    with patch("builtins.input", side_effect=inputs):
        data = _run_first_time_setup(path=cfg)
    assert data["project"]["id"] == "my-proj"
    assert data["project"]["location"] == "global"
    assert data["model"]["name"] == "gemini-3-flash-preview"
    assert data["model"]["max_tokens"] == 8192
    assert data["model"]["max_context_tokens"] == 128_000


def test_setup_preserves_unknown_sections(tmp_path):
    """If a user has manually added [grounding] to their config and then re-runs
    setup, the [grounding] section must survive the round-trip."""
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[project]\nid = "old-project"\nlocation = "us-central1"\n\n'
        '[model]\nname = "gemini-3-flash-preview"\nmax_tokens = 8192\n\n'
        '[grounding]\nopen_browser = true\n'
    )
    existing = _load_config_file(cfg_path)
    # Accept all defaults by pressing enter on every prompt.
    with patch("builtins.input", side_effect=iter(["", "", "", "", ""])):
        _run_first_time_setup(existing=existing, path=cfg_path)

    reloaded = _load_config_file(cfg_path)
    assert reloaded is not None
    assert reloaded.get("grounding", {}).get("open_browser") is True
    # And the existing project values should still be there too.
    assert reloaded["project"]["id"] == "old-project"
    assert reloaded["project"]["location"] == "us-central1"


def test_write_toml_serializes_bools_as_literals(tmp_path):
    """_write_toml must emit lowercase TOML bool literals (not quoted strings or
    Python-style True/False) so they round-trip cleanly through tomllib."""
    cfg = tmp_path / "out.toml"
    _write_toml(cfg, {"grounding": {"open_browser": False}})
    text = cfg.read_text()
    assert "open_browser = false" in text
    assert 'open_browser = "false"' not in text  # not a quoted string
    parsed = _load_config_file(cfg)
    assert parsed["grounding"]["open_browser"] is False

    cfg2 = tmp_path / "out2.toml"
    _write_toml(cfg2, {"grounding": {"open_browser": True}})
    parsed2 = _load_config_file(cfg2)
    assert parsed2["grounding"]["open_browser"] is True


@pytest.mark.parametrize(
    "val,expected",
    [
        ("0", False),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("no", False),
        ("off", False),
        ("", False),
        ("1", True),
        ("true", True),
        ("True", True),
        ("yes", True),
    ],
)
def test_grounding_open_browser_env_parsing(val, expected):
    """CFI_AI_GROUNDING_OPEN_BROWSER must accept case-insensitive falsy values
    so users typing 'False' don't accidentally enable the browser auto-open."""
    env = {"GOOGLE_CLOUD_PROJECT": "test", "CFI_AI_GROUNDING_OPEN_BROWSER": val}
    with patch.dict(os.environ, env, clear=True):
        config = Config.from_env()
    assert config.grounding_open_browser is expected


def test_load_grounding_open_browser_env_overrides_file(tmp_path):
    """Env var override for grounding_open_browser should beat the file setting,
    and case-insensitive falsy values should turn it off."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[project]\nid = "p"\nlocation = "global"\n\n'
        '[model]\nname = "gemini-3-flash-preview"\nmax_tokens = 8192\n\n'
        '[grounding]\nopen_browser = true\n'
    )
    # File says true, env says "False" — env should win and parse to False.
    env = {"CFI_AI_GROUNDING_OPEN_BROWSER": "False"}
    with patch.dict(os.environ, env, clear=True):
        config = Config.load(config_path=cfg)
    assert config.grounding_open_browser is False


# ── grounding_enabled (kill switch) ──────────────────────────────────


def test_grounding_enabled_default_true():
    """Without env or file config, grounding_enabled defaults to True."""
    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test"}, clear=True):
        config = Config.from_env()
    assert config.grounding_enabled is True


@pytest.mark.parametrize(
    "val,expected",
    [
        ("0", False),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("no", False),
        ("off", False),
        ("", True),  # empty string falls back to default (True for grounding_enabled)
        ("1", True),
        ("true", True),
        ("True", True),
        ("yes", True),
    ],
)
def test_grounding_enabled_env_parsing(val, expected):
    """CFI_AI_GROUNDING_ENABLED parses falsy strings to False, empty falls back
    to the default (True for this flag)."""
    env = {"GOOGLE_CLOUD_PROJECT": "test", "CFI_AI_GROUNDING_ENABLED": val}
    with patch.dict(os.environ, env, clear=True):
        config = Config.from_env()
    assert config.grounding_enabled is expected


def test_load_grounding_enabled_from_file(tmp_path):
    """[grounding] enabled = false in the config file should disable grounding."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[project]\nid = "p"\nlocation = "global"\n\n'
        '[model]\nname = "gemini-3-flash-preview"\nmax_tokens = 8192\n\n'
        '[grounding]\nenabled = false\n'
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.grounding_enabled is False


def test_load_grounding_enabled_env_overrides_file(tmp_path):
    """Env var override beats the file setting for grounding_enabled."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[project]\nid = "p"\nlocation = "global"\n\n'
        '[model]\nname = "gemini-3-flash-preview"\nmax_tokens = 8192\n\n'
        '[grounding]\nenabled = true\n'
    )
    # File says true, env says "0" — env wins.
    env = {"CFI_AI_GROUNDING_ENABLED": "0"}
    with patch.dict(os.environ, env, clear=True):
        config = Config.load(config_path=cfg)
    assert config.grounding_enabled is False


def test_load_grounding_enabled_default_when_section_missing(tmp_path):
    """A config file with no [grounding] section should default grounding_enabled
    to True (preserves backward compatibility)."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[project]\nid = "p"\nlocation = "global"\n\n'
        '[model]\nname = "gemini-3-flash-preview"\nmax_tokens = 8192\n'
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.grounding_enabled is True


# ── _parse_bool_env empty-string asymmetry fix ──────────────────────


@pytest.mark.parametrize(
    "value,default,expected",
    [
        (None, True, True),
        (None, False, False),
        ("", True, True),       # empty string falls back to default (was False before fix)
        ("", False, False),
        ("   ", True, True),    # whitespace-only also falls back to default
        ("   ", False, False),
        ("1", False, True),
        ("0", True, False),
    ],
)
def test_parse_bool_env_empty_string_falls_back_to_default(value, default, expected):
    """Empty/whitespace-only env var values must return the default rather than
    silently flipping to False. Prevents `CFI_AI_GROUNDING_ENABLED=''` from
    accidentally disabling a default-True flag."""
    assert _parse_bool_env(value, default) is expected


# ── max_context_tokens (input cap) ──────────────────────────────────


@pytest.mark.parametrize(
    "value,default,expected",
    [
        (None, 128_000, 128_000),
        ("", 128_000, 128_000),
        ("   ", 128_000, 128_000),
        ("not-a-number", 128_000, 128_000),
        ("64000", 128_000, 64_000),
        ("0", 128_000, 0),       # 0 disables the cap
        ("-1", 128_000, -1),     # negative also disables
    ],
)
def test_parse_int_env(value, default, expected):
    """Empty/None/unparseable values fall back to default; well-formed values
    parse cleanly. 0 and negative are accepted (caller treats them as
    disabling the cap)."""
    assert _parse_int_env(value, default) == expected


def test_from_env_max_context_tokens_default():
    """Without an env var, the cap defaults to 128k."""
    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "p"}, clear=True):
        config = Config.from_env()
    assert config.max_context_tokens == 128_000


def test_from_env_max_context_tokens_custom():
    env = {"GOOGLE_CLOUD_PROJECT": "p", "CFI_AI_MAX_CONTEXT_TOKENS": "50000"}
    with patch.dict(os.environ, env, clear=True):
        config = Config.from_env()
    assert config.max_context_tokens == 50_000


def test_from_env_max_context_tokens_zero_disables():
    env = {"GOOGLE_CLOUD_PROJECT": "p", "CFI_AI_MAX_CONTEXT_TOKENS": "0"}
    with patch.dict(os.environ, env, clear=True):
        config = Config.from_env()
    assert config.max_context_tokens == 0


def test_from_env_max_context_tokens_unparseable_falls_back():
    env = {"GOOGLE_CLOUD_PROJECT": "p", "CFI_AI_MAX_CONTEXT_TOKENS": "not-a-number"}
    with patch.dict(os.environ, env, clear=True):
        config = Config.from_env()
    assert config.max_context_tokens == 128_000


def test_load_max_context_tokens_from_file(tmp_path):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "p", "location": "global"},
            "model": {
                "name": "gemini-3-flash-preview",
                "max_tokens": 8192,
                "max_context_tokens": 64_000,
            },
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.max_context_tokens == 64_000


def test_load_max_context_tokens_env_overrides_file(tmp_path):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "p", "location": "global"},
            "model": {
                "name": "gemini-3-flash-preview",
                "max_tokens": 8192,
                "max_context_tokens": 64_000,
            },
        },
    )
    env = {"CFI_AI_MAX_CONTEXT_TOKENS": "32000"}
    with patch.dict(os.environ, env, clear=True):
        config = Config.load(config_path=cfg)
    assert config.max_context_tokens == 32_000


def test_load_max_context_tokens_default_when_absent(tmp_path):
    """A config file with no max_context_tokens should default to 128k."""
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "p", "location": "global"},
            "model": {"name": "gemini-3-flash-preview", "max_tokens": 8192},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.max_context_tokens == 128_000


# ── Deprecated model migration ─────────────────────────────────────


def test_load_migrates_deprecated_model_and_location(tmp_path, capsys):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "my-proj", "location": "us-central1"},
            "model": {"name": "gemini-2.5-flash", "max_tokens": 8192},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.model == "gemini-3-flash-preview"
    assert config.location == "global"
    # File was rewritten
    reloaded = _load_config_file(cfg)
    assert reloaded["model"]["name"] == "gemini-3-flash-preview"
    assert reloaded["project"]["location"] == "global"
    # Notice was printed
    err = capsys.readouterr().err
    assert "deprecated" in err
    assert "gemini-2.5-flash" in err


def test_load_migrates_deprecated_model_already_global(tmp_path, capsys):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "my-proj", "location": "global"},
            "model": {"name": "gemini-2.5-pro", "max_tokens": 4096},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.model == "gemini-3-flash-preview"
    assert config.location == "global"
    err = capsys.readouterr().err
    assert "gemini-2.5-pro" in err


def test_load_no_migration_when_env_var_overrides(tmp_path, capsys):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "my-proj", "location": "us-central1"},
            "model": {"name": "gemini-2.5-flash", "max_tokens": 8192},
        },
    )
    env = {"CFI_AI_MODEL": "gemini-2.5-pro"}
    with patch.dict(os.environ, env, clear=True):
        config = Config.load(config_path=cfg)
    assert config.model == "gemini-2.5-pro"
    # File was NOT rewritten
    reloaded = _load_config_file(cfg)
    assert reloaded["model"]["name"] == "gemini-2.5-flash"


def test_load_migration_preserves_other_sections(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[project]\nid = "my-proj"\nlocation = "eu-west1"\n\n'
        '[model]\nname = "gemini-2.5-flash-lite"\nmax_tokens = 8192\n\n'
        '[grounding]\nopen_browser = true\nenabled = false\n'
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.model == "gemini-3-flash-preview"
    reloaded = _load_config_file(cfg)
    assert reloaded["grounding"]["open_browser"] is True
    assert reloaded["grounding"]["enabled"] is False


@pytest.mark.parametrize("old_model", ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"])
def test_load_migrates_all_deprecated_models(tmp_path, old_model):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "p", "location": "us-central1"},
            "model": {"name": old_model, "max_tokens": 8192},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.model == "gemini-3-flash-preview"
    assert config.location == "global"


def test_load_migration_idempotent_on_second_run(tmp_path, capsys):
    cfg = tmp_path / "config.toml"
    _write_toml(
        cfg,
        {
            "project": {"id": "p", "location": "us-central1"},
            "model": {"name": "gemini-2.5-flash", "max_tokens": 8192},
        },
    )
    with patch.dict(os.environ, {}, clear=True):
        Config.load(config_path=cfg)
    capsys.readouterr()  # consume first-run output

    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.model == "gemini-3-flash-preview"
    err = capsys.readouterr().err
    assert "deprecated" not in err


def test_from_env_warns_on_deprecated_model(capsys):
    env = {
        "GOOGLE_CLOUD_PROJECT": "my-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "CFI_AI_MODEL": "gemini-2.5-flash",
    }
    with patch.dict(os.environ, env, clear=True):
        config = Config.from_env()
    assert config.model == "gemini-2.5-flash"
    err = capsys.readouterr().err
    assert "deprecated" in err.lower()
    assert "gemini-2.5-flash" in err


def test_from_env_no_warning_for_current_model(capsys):
    env = {"GOOGLE_CLOUD_PROJECT": "my-project"}
    with patch.dict(os.environ, env, clear=True):
        config = Config.from_env()
    assert config.model == "gemini-3-flash-preview"
    err = capsys.readouterr().err
    assert "deprecated" not in err.lower()


# ── bugreport ────────────────────────────────────────────────────────


def test_load_bugreport_defaults(tmp_path):
    """Config file with [project]+[model] but no [bugreport] section should give
    enabled=True, repo="jmiranda3838/cfi-ai", dry_run=False."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[project]\nid = "p"\nlocation = "global"\n\n'
        '[model]\nname = "gemini-3-flash-preview"\nmax_tokens = 8192\n'
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.bugreport_enabled is True
    assert config.bugreport_repo == "jmiranda3838/cfi-ai"
    assert config.bugreport_dry_run is False


def test_load_bugreport_from_file(tmp_path):
    """[bugreport] repo and enabled in TOML should be picked up."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[project]\nid = "p"\nlocation = "global"\n\n'
        '[model]\nname = "gemini-3-flash-preview"\nmax_tokens = 8192\n\n'
        '[bugreport]\nrepo = "x/y"\nenabled = false\n'
    )
    with patch.dict(os.environ, {}, clear=True):
        config = Config.load(config_path=cfg)
    assert config.bugreport_enabled is False
    assert config.bugreport_repo == "x/y"


def test_load_bugreport_env_overrides_file(tmp_path):
    """Env wins over file for both enabled and repo."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[project]\nid = "p"\nlocation = "global"\n\n'
        '[model]\nname = "gemini-3-flash-preview"\nmax_tokens = 8192\n\n'
        '[bugreport]\nrepo = "x/y"\nenabled = true\n'
    )
    env = {
        "CFI_AI_BUGREPORT_ENABLED": "0",
        "CFI_AI_BUGREPORT_REPO": "other/repo",
    }
    with patch.dict(os.environ, env, clear=True):
        config = Config.load(config_path=cfg)
    assert config.bugreport_enabled is False
    assert config.bugreport_repo == "other/repo"


@pytest.mark.parametrize(
    "val,expected",
    [
        ("0", False),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("no", False),
        ("off", False),
        ("", True),  # empty falls back to default (True)
        ("   ", True),  # whitespace falls back to default (True)
        ("1", True),
        ("true", True),
        ("True", True),
        ("yes", True),
    ],
)
def test_bugreport_enabled_env_parsing(val, expected):
    """CFI_AI_BUGREPORT_ENABLED parses falsy strings to False, empty/whitespace
    falls back to the default (True)."""
    env = {"GOOGLE_CLOUD_PROJECT": "test", "CFI_AI_BUGREPORT_ENABLED": val}
    with patch.dict(os.environ, env, clear=True):
        config = Config.from_env()
    assert config.bugreport_enabled is expected


@pytest.mark.parametrize(
    "val,expected",
    [
        ("0", False),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("no", False),
        ("off", False),
        ("", False),  # empty falls back to default (False)
        ("   ", False),
        ("1", True),
        ("true", True),
        ("True", True),
        ("yes", True),
    ],
)
def test_bugreport_dry_run_env_parsing(val, expected):
    """CFI_AI_BUGREPORT_DRY_RUN defaults to False; empty falls back to default."""
    env = {"GOOGLE_CLOUD_PROJECT": "test", "CFI_AI_BUGREPORT_DRY_RUN": val}
    with patch.dict(os.environ, env, clear=True):
        config = Config.from_env()
    assert config.bugreport_dry_run is expected
