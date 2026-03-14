import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "cfi-ai" / "config.toml"


def _load_config_file(path: Path = CONFIG_PATH) -> dict | None:
    """Read config TOML file. Returns None if missing or invalid."""
    try:
        return tomllib.loads(path.read_text())
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return None


def _write_toml(path: Path, data: dict) -> None:
    """Write a simple nested dict as TOML (strings and ints only)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        for key, val in values.items():
            if isinstance(val, int):
                lines.append(f"{key} = {val}")
            else:
                lines.append(f'{key} = "{val}"')
        lines.append("")
    path.write_text("\n".join(lines))


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
    model_name = _prompt("Model", model_section.get("name", "gemini-2.5-flash"))
    max_tokens_str = _prompt("Max tokens", str(model_section.get("max_tokens", 8192)))

    data = {
        "project": {"id": project_id, "location": location},
        "model": {"name": model_name, "max_tokens": int(max_tokens_str)},
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

    @classmethod
    def from_env(cls) -> "Config":
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not project:
            print("Error: GOOGLE_CLOUD_PROJECT environment variable is required.", file=sys.stderr)
            sys.exit(1)
        return cls(
            project=project,
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
            model=os.environ.get("CFI_AI_MODEL", "gemini-2.5-flash"),
            max_tokens=int(os.environ.get("CFI_AI_MAX_TOKENS", "8192")),
        )

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
        model_name = os.environ.get("CFI_AI_MODEL") or model.get("name", "gemini-2.5-flash")
        max_tokens = int(
            os.environ.get("CFI_AI_MAX_TOKENS") or model.get("max_tokens", 8192)
        )

        if not project:
            print("Error: GCP project ID is not configured.", file=sys.stderr)
            print("Run 'cfi-ai --setup' or set GOOGLE_CLOUD_PROJECT.", file=sys.stderr)
            sys.exit(1)

        return cls(
            project=project,
            location=location,
            model=model_name,
            max_tokens=max_tokens,
        )
