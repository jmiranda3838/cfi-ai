from cfi_ai.tools.base import BaseTool, ToolDefinition


class EditFileTool(BaseTool):
    name = "edit_file"
    mutating = True

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description="Make a targeted search-and-replace edit to an existing file. The old_text must appear exactly once in the file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within the workspace.",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "The exact text to find in the file. Must match exactly once.",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "The text to replace old_text with.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        )

    def execute(self, workspace, **kwargs) -> str:
        rel = kwargs["path"]
        old_text = kwargs["old_text"]
        new_text = kwargs["new_text"]

        target = workspace.validate_path(rel)
        if not target.is_file():
            return f"Error: {rel} is not a file or does not exist"

        content = target.read_text()
        count = content.count(old_text)

        if count == 0:
            return f"Error: old_text not found in {rel}"
        if count > 1:
            return f"Error: old_text appears {count} times in {rel} (must be exactly once)"

        new_content = content.replace(old_text, new_text, 1)
        target.write_text(new_content)
        return f"Edited {rel}"
