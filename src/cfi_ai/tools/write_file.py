from cfi_ai.tools.base import BaseTool, ToolDefinition


class WriteFileTool(BaseTool):
    name = "write_file"
    mutating = True

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Create a new file at a path relative to the workspace root. "
                "Creates parent directories if needed. "
                "Cannot overwrite existing files — use apply_patch to edit existing files."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path for the new file within the workspace.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file.",
                    },
                },
                "required": ["path", "content"],
            },
        )

    def execute(self, workspace, **kwargs) -> str:
        rel = kwargs["path"]
        content = kwargs["content"]
        target = workspace.validate_path(rel)
        if target.is_file():
            return f"Error: {rel} already exists. Use apply_patch to edit existing files."
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Wrote {len(content)} characters to {rel}"
