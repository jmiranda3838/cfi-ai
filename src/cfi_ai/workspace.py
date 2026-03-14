import os
from pathlib import Path


class Workspace:
    def __init__(self, path: str | None = None):
        self.root = Path(path or os.getcwd()).resolve()

    def validate_path(self, requested: str) -> Path:
        """Resolve a path and ensure it stays within the workspace root."""
        resolved = (self.root / requested).resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"Path escapes workspace: {requested}")
        return resolved

    def summary(self) -> str:
        """Generate a top-level listing and project type hints for the system prompt."""
        entries: list[str] = []
        try:
            for item in sorted(self.root.iterdir()):
                if item.name.startswith("."):
                    continue
                suffix = "/" if item.is_dir() else ""
                entries.append(f"  {item.name}{suffix}")
        except PermissionError:
            entries.append("  (permission denied)")

        listing = "\n".join(entries) if entries else "  (empty directory)"

        project_hints: list[str] = []
        markers = {
            "pyproject.toml": "Python (pyproject.toml)",
            "package.json": "Node.js",
            "Cargo.toml": "Rust",
            "go.mod": "Go",
            "Makefile": "Make",
        }
        for filename, label in markers.items():
            if (self.root / filename).exists():
                project_hints.append(label)

        hint_line = f"Detected project type(s): {', '.join(project_hints)}" if project_hints else ""
        parts = [f"Workspace: {self.root}", f"Contents:\n{listing}"]
        if hint_line:
            parts.append(hint_line)
        return "\n".join(parts)
