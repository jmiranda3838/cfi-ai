from cfi_ai.tools.base import BaseTool, ToolDefinition


class ListFilesTool(BaseTool):
    name = "list_files"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="List files and directories at a given path relative to the workspace root. Returns names with '/' suffix for directories.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path within the workspace. Use '.' for the root.",
                        "default": ".",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "If true, list files recursively (max 500 entries).",
                        "default": False,
                    },
                },
                "required": [],
            },
        )

    def execute(self, workspace, **kwargs) -> str:
        rel = kwargs.get("path", ".")
        recursive = kwargs.get("recursive", False)
        target = workspace.validate_path(rel)
        if not target.is_dir():
            return f"Error: '{rel}' is not a directory."

        entries: list[str] = []
        if recursive:
            for item in sorted(target.rglob("*")):
                if any(p.startswith(".") for p in item.relative_to(workspace.root).parts):
                    continue
                rel_path = item.relative_to(workspace.root)
                suffix = "/" if item.is_dir() else ""
                entries.append(f"{rel_path}{suffix}")
                if len(entries) >= 500:
                    entries.append("... (truncated at 500 entries)")
                    break
        else:
            for item in sorted(target.iterdir()):
                if item.name.startswith("."):
                    continue
                suffix = "/" if item.is_dir() else ""
                entries.append(f"{item.name}{suffix}")

        return "\n".join(entries) if entries else "(empty directory)"
