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
                "By default, rejects existing files — pass overwrite=true to replace an existing file entirely. "
                "For targeted edits to specific sections, use apply_patch instead."
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
                    "overwrite": {
                        "type": "boolean",
                        "description": "If true, overwrite the file if it already exists. Default: false.",
                    },
                },
                "required": ["path", "content"],
            },
        )

    def execute(self, workspace, client=None, **kwargs) -> str:
        rel = kwargs.get("path")
        if "content" not in kwargs:
            return (
                "Error: write_file requires both 'path' and 'content' arguments. "
                "Missing: content. Re-emit the call with both arguments."
            )
        if not rel:
            return (
                "Error: write_file requires both 'path' and 'content' arguments. "
                "Missing: path. Re-emit the call with both arguments."
            )
        content = kwargs["content"]
        overwrite = kwargs.get("overwrite", False)
        target = workspace.validate_path(rel)
        if target.is_file() and not overwrite:
            return f"Error: {rel} already exists. Use overwrite=true to replace it, or apply_patch to edit specific sections."
        already_exists = target.is_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        action = "Overwrote" if already_exists else "Wrote"
        return f"{action} {len(content)} characters to {rel}"
