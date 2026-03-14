from cfi_ai.tools.base import BaseTool, ToolDefinition


class WriteFileTool(BaseTool):
    name = "write_file"
    mutating = True

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="Write content to a file at a path relative to the workspace root. Creates parent directories if needed. Overwrites existing files.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path for the file within the workspace.",
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
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Wrote {len(content)} characters to {rel}"
