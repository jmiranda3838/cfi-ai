import re
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


def _resolve_input_path(raw: str, workspace) -> tuple[Path | None, str | None]:
    """Try to resolve a user-supplied path string to a real file.

    Handles three real-world inputs the model is likely to pass:
      1. A clean path that already exists.
      2. A shell-escaped path (e.g. 'Screenshot\\ 2026-04-06.png') that the
         model forgot to unescape before calling the tool.
      3. A path wrapped in matched single or double quotes.

    Returns (resolved_path, None) on success, or (None, error_message)
    on failure. Relative paths are still routed through Workspace.validate_path
    so workspace-escape protection is preserved.
    """
    candidates: list[str] = []
    s = raw.strip()

    # Strip a single layer of matched surrounding quotes.
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1]

    candidates.append(s)
    # Conservatively unescape only shell-meaningful characters that the user
    # is likely to have escaped when pasting a path (whitespace, quotes,
    # parens, brackets, ampersands, etc.). Crucially, we do NOT touch
    # backslashes followed by alphanumerics — that would corrupt
    # Windows-style paths like 'C:\\Users\\name'.
    if "\\" in s:
        unescaped = re.sub(r"\\([ \t'\"()\[\],\-&;|<>$#`!*?])", r"\1", s)
        if unescaped != s:
            candidates.append(unescaped)

    last_err: str | None = None
    for cand in candidates:
        p = Path(cand).expanduser()
        try:
            if p.is_absolute():
                target = p.resolve()
            else:
                target = workspace.validate_path(str(p))
        except ValueError as e:
            last_err = str(e)
            continue
        if target.is_file():
            return target, None

    return None, last_err


class AttachPathTool(BaseTool):
    name = "attach_path"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Load a file into the conversation context. Works with text files, "
                "audio (mp3, wav, m4a, etc.), images (png, jpg, gif, webp), and PDFs. "
                "Accepts an absolute path to any file the user can read on this machine "
                "(including ~/Desktop, /tmp, /var/folders/...) or a path relative to the "
                "workspace. Backslash-escaped spaces in paths are handled automatically — "
                "do not refuse a path just because it lives outside the workspace. "
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

    def execute(self, workspace, client=None, **kwargs) -> str | tuple[str, list[types.Part]]:
        raw = kwargs.get("path")
        if not raw:
            return (
                "Error: attach_path requires a 'path' argument (string). "
                "Re-emit the call with the path you want to load."
            )
        target, err = _resolve_input_path(raw, workspace)
        if target is None:
            if err is not None:
                return f"Error: {err}"
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
