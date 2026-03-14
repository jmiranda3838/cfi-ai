import re
from cfi_ai.tools.base import BaseTool, ToolDefinition


class SearchFilesTool(BaseTool):
    name = "search_files"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="Search for a regex pattern across files in the workspace. Returns matching lines with file paths and line numbers.",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Subdirectory to search within (relative to workspace root). Defaults to '.'.",
                        "default": ".",
                    },
                    "file_glob": {
                        "type": "string",
                        "description": "Optional glob to filter filenames (e.g. '*.py').",
                        "default": "*",
                    },
                },
                "required": ["pattern"],
            },
        )

    def execute(self, workspace, **kwargs) -> str:
        pattern_str = kwargs["pattern"]
        rel = kwargs.get("path", ".")
        file_glob = kwargs.get("file_glob", "*")
        target = workspace.validate_path(rel)

        if not target.is_dir():
            return f"Error: '{rel}' is not a directory."

        try:
            regex = re.compile(pattern_str)
        except re.error as e:
            return f"Error: invalid regex: {e}"

        results: list[str] = []
        max_results = 200

        for filepath in sorted(target.rglob(file_glob)):
            if not filepath.is_file():
                continue
            if any(p.startswith(".") for p in filepath.relative_to(workspace.root).parts):
                continue
            try:
                lines = filepath.read_text(errors="replace").splitlines()
            except (PermissionError, OSError):
                continue
            rel_path = filepath.relative_to(workspace.root)
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    results.append(f"{rel_path}:{i}: {line.rstrip()}")
                    if len(results) >= max_results:
                        results.append(f"... (truncated at {max_results} matches)")
                        return "\n".join(results)

        return "\n".join(results) if results else "No matches found."
