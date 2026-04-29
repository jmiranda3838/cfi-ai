import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "cfi-ai" / "config.toml"

# Models the user can pick via /model. Second tuple element is True if that
# model's Vertex AI deployment is only available at location="global". Adding
# a regional model is `("name", False)` — it joins ACTIVE_MODELS without
# leaking into _GLOBAL_ONLY_MODELS.
_MODELS: tuple[tuple[str, bool], ...] = (
    ("gemini-3-flash-preview", True),
    ("gemini-3.1-pro-preview", True),
    ("gemini-3.1-pro-preview-customtools", True),
)
ACTIVE_MODELS: tuple[str, ...] = tuple(name for name, _ in _MODELS)
_GLOBAL_ONLY_MODELS: frozenset[str] = frozenset(
    name for name, global_only in _MODELS if global_only
)
_DEPRECATED_MODELS: dict[str, str] = {
    "gemini-2.5-pro": "gemini-3-flash-preview",
    "gemini-2.5-flash": "gemini-3-flash-preview",
    "gemini-2.5-flash-lite": "gemini-3-flash-preview",
}


def check_model_location(model: str, location: str) -> str | None:
    """Return an error message if model/location are incompatible, else None.

    Used by Config.validate() at startup and by the /model swap path mid-session
    to gate transitions into invalid combinations.
    """
    if model in _GLOBAL_ONLY_MODELS and location != "global":
        return (
            f"Model '{model}' requires Vertex AI location 'global', "
            f"but the current location is '{location}'."
        )
    return None


def _load_config_file(path: Path = CONFIG_PATH) -> dict | None:
    """Read config TOML file. Returns None if missing or invalid."""
    try:
        return tomllib.loads(path.read_text())
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return None


def _write_toml(path: Path, data: dict) -> None:
    """Write a simple nested dict as TOML (strings, ints, and bools)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        for key, val in values.items():
            if isinstance(val, bool):
                # bool must come before int (bool is a subclass of int)
                lines.append(f"{key} = {'true' if val else 'false'}")
            elif isinstance(val, int):
                lines.append(f"{key} = {val}")
            else:
                lines.append(f'{key} = "{val}"')
        lines.append("")
    path.write_text("\n".join(lines))


def _parse_bool_env(value: str | None, default: bool) -> bool:
    """Parse a boolean env var with case-insensitive recognition of common
    falsy values. Returns default if value is None or an empty/whitespace string
    (so a user setting CFI_AI_FOO='' doesn't accidentally flip a default-True
    flag to False)."""
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


def _parse_int_env(value: str | None, default: int) -> int:
    """Parse an integer env var. Returns default if value is None, empty,
    whitespace-only, or unparseable. A value of 0 or negative disables any
    associated cap (callers check for ``<= 0``)."""
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def _prompt(label: str, default: str) -> str:
    """Prompt user for input with a default value."""
    suffix = f" [{default}]" if default else ""
    response = input(f"  {label}{suffix}: ").strip()
    return response or default


def _run_first_time_setup(existing: dict | None = None, path: Path = CONFIG_PATH) -> dict:
    """Interactive setup that prompts for config values and writes the file."""
    print("cfi-ai setup")
    print("=" * 40)
    print()

    proj = existing or {}
    proj_section = proj.get("project", {})
    model_section = proj.get("model", {})

    project_id = _prompt("GCP project ID", proj_section.get("id", ""))
    if not project_id:
        print("Error: project ID is required.", file=sys.stderr)
        sys.exit(1)

    location = _prompt("Vertex AI location", proj_section.get("location", "global"))
    model_name = _prompt("Model", model_section.get("name", "gemini-3-flash-preview"))
    max_tokens_str = _prompt("Max tokens", str(model_section.get("max_tokens", 8192)))
    max_context_tokens_str = _prompt(
        "Max context tokens (0 = disable cap)",
        str(model_section.get("max_context_tokens", 128_000)),
    )

    # Preserve any unknown top-level sections (e.g. [grounding]) the user may
    # have added manually — only [project] and [model] are overwritten.
    data: dict = dict(existing) if existing else {}
    data["project"] = {"id": project_id, "location": location}
    data["model"] = {
        "name": model_name,
        "max_tokens": int(max_tokens_str),
        "max_context_tokens": int(max_context_tokens_str),
    }
    notifications = data.get("notifications", {})
    data["notifications"] = {
        "popup_enabled": bool(notifications.get("popup_enabled", False)),
        "sound_enabled": bool(notifications.get("sound_enabled", False)),
    }
    _write_toml(path, data)
    print(f"\nConfig written to {path}")
    return data


@dataclass(frozen=True)
class Config:
    project: str
    location: str
    model: str
    max_tokens: int
    max_context_tokens: int = 128_000
    context_cache: bool = True
    grounding_open_browser: bool = False
    grounding_enabled: bool = True
    bugreport_enabled: bool = True
    bugreport_repo: str = "jmiranda3838/cfi-ai"
    bugreport_dry_run: bool = False
    notifications_popup_enabled: bool = False
    notifications_sound_enabled: bool = False

    def validate(self) -> None:
        """Fail fast on known invalid model/location combinations."""
        err = check_model_location(self.model, self.location)
        if err is not None:
            print(
                f"Error: {err}\n"
                "Run 'cfi-ai --setup', set GOOGLE_CLOUD_LOCATION=global, or edit "
                "~/.config/cfi-ai/config.toml.",
                file=sys.stderr,
            )
            sys.exit(1)

    @classmethod
    def from_env(cls) -> "Config":
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not project:
            print("Error: GOOGLE_CLOUD_PROJECT environment variable is required.", file=sys.stderr)
            sys.exit(1)
        model_name = os.environ.get("CFI_AI_MODEL", "gemini-3-flash-preview")
        if model_name in _DEPRECATED_MODELS:
            print(
                f"Warning: CFI_AI_MODEL='{model_name}' is deprecated (sunset June 2026). "
                f"Consider switching to '{_DEPRECATED_MODELS[model_name]}'.",
                file=sys.stderr,
            )
        config = cls(
            project=project,
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
            model=model_name,
            max_tokens=int(os.environ.get("CFI_AI_MAX_TOKENS", "8192")),
            max_context_tokens=_parse_int_env(
                os.environ.get("CFI_AI_MAX_CONTEXT_TOKENS"), 128_000
            ),
            context_cache=os.environ.get("CFI_AI_CONTEXT_CACHE", "1") not in ("0", "false"),
            grounding_open_browser=_parse_bool_env(
                os.environ.get("CFI_AI_GROUNDING_OPEN_BROWSER"), False
            ),
            grounding_enabled=_parse_bool_env(
                os.environ.get("CFI_AI_GROUNDING_ENABLED"), True
            ),
            bugreport_enabled=_parse_bool_env(
                os.environ.get("CFI_AI_BUGREPORT_ENABLED"), True
            ),
            bugreport_repo=os.environ.get("CFI_AI_BUGREPORT_REPO") or "jmiranda3838/cfi-ai",
            bugreport_dry_run=_parse_bool_env(
                os.environ.get("CFI_AI_BUGREPORT_DRY_RUN"), False
            ),
            notifications_popup_enabled=_parse_bool_env(
                os.environ.get("CFI_AI_NOTIFICATIONS_POPUP_ENABLED"), False
            ),
            notifications_sound_enabled=_parse_bool_env(
                os.environ.get("CFI_AI_NOTIFICATIONS_SOUND_ENABLED"), False
            ),
        )
        config.validate()
        return config

    @classmethod
    def load(cls, run_setup: bool = False, config_path: Path = CONFIG_PATH) -> "Config":
        """Load config from file, with env var overrides. Triggers setup if needed."""
        file_data = _load_config_file(config_path)

        if run_setup or file_data is None:
            file_data = _run_first_time_setup(existing=file_data, path=config_path)

        proj = file_data.get("project", {})
        model = file_data.get("model", {})

        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or proj.get("id", "")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION") or proj.get("location", "global")
        model_name = os.environ.get("CFI_AI_MODEL") or model.get("name", "gemini-3-flash-preview")

        # ── Auto-migrate deprecated models from config file ─────────
        model_from_env = os.environ.get("CFI_AI_MODEL")
        if not model_from_env and model_name in _DEPRECATED_MODELS:
            replacement = _DEPRECATED_MODELS[model_name]
            old_model = model_name
            model_name = replacement

            location_from_env = os.environ.get("GOOGLE_CLOUD_LOCATION")
            if replacement in _GLOBAL_ONLY_MODELS and location != "global" and not location_from_env:
                location = "global"

            file_data.setdefault("model", {})["name"] = model_name
            file_data.setdefault("project", {})["location"] = location
            _write_toml(config_path, file_data)

            print(
                f"Notice: Model '{old_model}' is deprecated (sunset June 2026). "
                f"Your config has been updated to '{model_name}'"
                + (f" with location='global'" if location == "global" else "")
                + f".\nEdit {config_path} or set CFI_AI_MODEL to override.",
                file=sys.stderr,
            )

        max_tokens = int(
            os.environ.get("CFI_AI_MAX_TOKENS") or model.get("max_tokens", 8192)
        )
        max_context_tokens = _parse_int_env(
            os.environ.get("CFI_AI_MAX_CONTEXT_TOKENS"),
            int(model.get("max_context_tokens", 128_000)),
        )

        if not project:
            print("Error: GCP project ID is not configured.", file=sys.stderr)
            print("Run 'cfi-ai --setup' or set GOOGLE_CLOUD_PROJECT.", file=sys.stderr)
            sys.exit(1)

        context_cache = os.environ.get("CFI_AI_CONTEXT_CACHE", "1") not in ("0", "false")

        grounding = file_data.get("grounding", {})
        env_open_browser = os.environ.get("CFI_AI_GROUNDING_OPEN_BROWSER")
        if env_open_browser is not None:
            grounding_open_browser = _parse_bool_env(env_open_browser, False)
        else:
            grounding_open_browser = bool(grounding.get("open_browser", False))

        env_grounding_enabled = os.environ.get("CFI_AI_GROUNDING_ENABLED")
        if env_grounding_enabled is not None:
            grounding_enabled = _parse_bool_env(env_grounding_enabled, True)
        else:
            grounding_enabled = bool(grounding.get("enabled", True))

        bugreport = file_data.get("bugreport", {})
        env_bugreport_enabled = os.environ.get("CFI_AI_BUGREPORT_ENABLED")
        if env_bugreport_enabled is not None:
            bugreport_enabled = _parse_bool_env(env_bugreport_enabled, True)
        else:
            bugreport_enabled = bool(bugreport.get("enabled", True))
        bugreport_repo = (
            os.environ.get("CFI_AI_BUGREPORT_REPO")
            or bugreport.get("repo")
            or "jmiranda3838/cfi-ai"
        )
        bugreport_dry_run = _parse_bool_env(
            os.environ.get("CFI_AI_BUGREPORT_DRY_RUN"), False
        )

        notifications = file_data.get("notifications", {})
        env_notifications_popup = os.environ.get("CFI_AI_NOTIFICATIONS_POPUP_ENABLED")
        if env_notifications_popup is not None:
            notifications_popup_enabled = _parse_bool_env(
                env_notifications_popup, False
            )
        else:
            notifications_popup_enabled = bool(
                notifications.get("popup_enabled", False)
            )
        env_notifications_sound = os.environ.get("CFI_AI_NOTIFICATIONS_SOUND_ENABLED")
        if env_notifications_sound is not None:
            notifications_sound_enabled = _parse_bool_env(
                env_notifications_sound, False
            )
        else:
            notifications_sound_enabled = bool(
                notifications.get("sound_enabled", False)
            )

        config = cls(
            project=project,
            location=location,
            model=model_name,
            max_tokens=max_tokens,
            max_context_tokens=max_context_tokens,
            context_cache=context_cache,
            grounding_open_browser=grounding_open_browser,
            grounding_enabled=grounding_enabled,
            bugreport_enabled=bugreport_enabled,
            bugreport_repo=bugreport_repo,
            bugreport_dry_run=bugreport_dry_run,
            notifications_popup_enabled=notifications_popup_enabled,
            notifications_sound_enabled=notifications_sound_enabled,
        )
        config.validate()
        return config


def persist_notifications_settings(
    config: Config,
    *,
    config_path: Path | None = None,
) -> None:
    """Persist only the notifications section while preserving other config."""
    path = config_path or CONFIG_PATH
    data = _load_config_file(path) or {}
    data["notifications"] = {
        "popup_enabled": config.notifications_popup_enabled,
        "sound_enabled": config.notifications_sound_enabled,
    }
    _write_toml(path, data)
