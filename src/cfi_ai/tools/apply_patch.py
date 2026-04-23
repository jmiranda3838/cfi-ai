from cfi_ai.tools.base import BaseTool, ToolDefinition


class ApplyPatchTool(BaseTool):
    name = "apply_patch"
    mutating = True

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Apply one or more search-and-replace edits to an existing file. "
                "Each edit's old_text must appear exactly once unless replace_all is set. "
                "Edits are applied sequentially — later edits see the result of earlier ones. "
                "The operation is transactional: if any edit fails, no changes are written. "
                "Before patching a file you have not already read or written in this session, "
                "read its current contents so old_text matches reality."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within the workspace.",
                    },
                    "edits": {
                        "type": "array",
                        "description": "List of search-and-replace edits to apply sequentially.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "old_text": {
                                    "type": "string",
                                    "description": "Exact text to find (must appear exactly once unless replace_all is set).",
                                },
                                "new_text": {
                                    "type": "string",
                                    "description": "Text to replace old_text with.",
                                },
                                "replace_all": {
                                    "type": "boolean",
                                    "description": "Replace all occurrences of old_text (default: false, requires exactly one match).",
                                },
                            },
                            "required": ["old_text", "new_text"],
                        },
                    },
                },
                "required": ["path", "edits"],
            },
        )

    def execute(self, workspace, client=None, **kwargs) -> str:
        rel = kwargs["path"]
        edits = kwargs["edits"]

        if not edits:
            return "Error: edits array is empty"

        target = workspace.validate_path(rel)
        if not target.is_file():
            return f"Error: {rel} is not a file or does not exist"

        content = target.read_text()

        # Apply edits sequentially in memory
        total_replacements = 0
        for i, edit in enumerate(edits):
            old_text = edit.get("old_text", "")
            new_text = edit.get("new_text", "")
            replace_all = edit.get("replace_all", False)

            if not old_text:
                return f"Error: edit {i}: old_text is empty"

            count = content.count(old_text)
            if count == 0:
                return f"Error: edit {i}: old_text not found in {rel}"

            if not replace_all and count > 1:
                return f"Error: edit {i}: old_text appears {count} times in {rel} (must be exactly once)"

            if replace_all:
                content = content.replace(old_text, new_text)
            else:
                content = content.replace(old_text, new_text, 1)

            total_replacements += count

        # All edits succeeded — atomic write
        target.write_text(content)
        n = len(edits)
        return f"Applied {n} edit{'s' if n != 1 else ''} to {rel} ({total_replacements} replacement{'s' if total_replacements != 1 else ''})"
