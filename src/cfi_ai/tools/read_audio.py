from pathlib import Path

from google.genai import types

from cfi_ai.tools.base import BaseTool, ToolDefinition

AUDIO_EXTENSIONS: dict[str, str] = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aiff": "audio/aiff",
    ".webm": "audio/webm",
}

_SUPPORTED_LIST = ", ".join(sorted(AUDIO_EXTENSIONS))


class ReadAudioTool(BaseTool):
    name = "read_audio"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Read an audio file and make its contents available for processing. "
                "Accepts absolute paths or paths relative to the workspace. "
                f"Supports: {_SUPPORTED_LIST}."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the audio file (absolute or relative to workspace).",
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

        mime_type = AUDIO_EXTENSIONS.get(target.suffix.lower())
        if mime_type is None:
            return (
                f"Error: unsupported audio format '{target.suffix}'. "
                f"Supported: {_SUPPORTED_LIST}."
            )

        try:
            data = target.read_bytes()
        except PermissionError:
            return f"Error: permission denied reading '{raw}'."

        summary = f"Audio file loaded: {target.name} ({len(data) / 1024:.0f} KB, {mime_type})"
        inline_part = types.Part.from_bytes(data=data, mime_type=mime_type)
        return (summary, [inline_part])
