from pathlib import Path

from google.genai import types

from cfi_ai.tools.base import BaseTool, ToolDefinition

INLINE_MIME_TYPES: dict[str, str] = {
    # Audio
    ".mp3": "audio/mp3", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".aac": "audio/aac", ".ogg": "audio/ogg", ".flac": "audio/flac",
    ".aiff": "audio/aiff", ".webm": "audio/webm",
    # Images
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp",
    # Documents
    ".pdf": "application/pdf",
}

_MAX_TEXT = 100_000


class AttachPathTool(BaseTool):
    name = "attach_path"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Load a file into the conversation context. Works with text files, "
                "audio (mp3, wav, m4a, etc.), images (png, jpg, gif, webp), and PDFs. "
                "Accepts absolute paths or paths relative to the workspace. "
                "Binary files (audio, images, PDFs) are embedded directly for you to "
                "perceive. Text files are returned as content."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (absolute or relative to workspace).",
                    },
                },
                "required": ["path"],
            },
        )

    def execute(self, workspace, **kwargs) -> str | tuple[str, list[types.Part]]:
        raw = kwargs["path"]
        p = Path(raw)

        if p.is_absolute():
            target = p.resolve()
        else:
            try:
                target = workspace.validate_path(raw)
            except ValueError as e:
                return f"Error: {e}"

        if not target.is_file():
            return f"Error: '{raw}' is not a file or does not exist."

        ext = target.suffix.lower()
        mime_type = INLINE_MIME_TYPES.get(ext)

        if mime_type is not None:
            # Binary inline attachment
            try:
                data = target.read_bytes()
            except PermissionError:
                return f"Error: permission denied reading '{raw}'."

            size_kb = len(data) / 1024
            summary = f"Attached: {target.name} ({size_kb:.0f} KB, {mime_type}). The file is now in context."
            inline_part = types.Part.from_bytes(data=data, mime_type=mime_type)
            return (summary, [inline_part])

        # Text file
        try:
            content = target.read_text(errors="replace")
        except PermissionError:
            return f"Error: permission denied reading '{raw}'."

        if len(content) > _MAX_TEXT:
            content = content[:_MAX_TEXT] + "\n\n... (truncated at 100k characters)"

        n = len(content)
        summary = f"Read {target.name} ({n} chars)."
        return summary + "\n\n" + content
