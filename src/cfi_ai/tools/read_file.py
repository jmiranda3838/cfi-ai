from cfi_ai.tools.base import BaseTool, ToolDefinition


class ReadFileTool(BaseTool):
    name = "read_file"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="Read the contents of a file at a path relative to the workspace root. Returns the file content as text.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within the workspace.",
                    },
                },
                "required": ["path"],
            },
        )

    def execute(self, workspace, **kwargs) -> str:
        rel = kwargs["path"]
        target = workspace.validate_path(rel)
        if not target.is_file():
            return f"Error: '{rel}' is not a file or does not exist."
        try:
            content = target.read_text(errors="replace")
        except PermissionError:
            return f"Error: permission denied reading '{rel}'."
        if len(content) > 100_000:
            return content[:100_000] + "\n\n... (truncated at 100k characters)"
        return content
