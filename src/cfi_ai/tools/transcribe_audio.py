from pathlib import Path

from google.genai import types

from cfi_ai.tools.base import BaseTool, ToolDefinition

_AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac", ".aiff", ".webm"}

_AUDIO_MIME_TYPES: dict[str, str] = {
    ".mp3": "audio/mp3", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".aac": "audio/aac", ".ogg": "audio/ogg", ".flac": "audio/flac",
    ".aiff": "audio/aiff", ".webm": "audio/webm",
}

_TRANSCRIPTION_PROMPT = """\
Transcribe this clinical therapy session audio verbatim.

Rules:
- Use speaker labels (e.g., "Therapist:", "Client:")
- Include timestamps at natural breaks, e.g., [0:05:23]
- Capture dialogue faithfully including filler words (um, uh, like)
- Note significant pauses in brackets, e.g., [pause]
- Note emotional tone where clinically relevant, e.g., [voice breaking]
- Do not summarize, omit, or add commentary"""

_FLASH_MODEL = "gemini-3.1-flash-lite-preview"


class TranscribeAudioTool(BaseTool):
    name = "transcribe_audio"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Transcribe an audio file to text via a focused API call. "
                "Returns the transcript with speaker labels and timestamps."
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

    def execute(self, workspace, client=None, **kwargs) -> str:
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
        if ext not in _AUDIO_EXTENSIONS:
            return f"Error: '{target.name}' is not a supported audio file. Supported: {', '.join(sorted(_AUDIO_EXTENSIONS))}"

        if client is None:
            return "Error: transcribe_audio requires an API client (not available in plan mode)."

        try:
            data = target.read_bytes()
        except PermissionError:
            return f"Error: permission denied reading '{raw}'."

        mime_type = _AUDIO_MIME_TYPES.get(ext, "audio/mpeg")

        parts = [
            types.Part.from_bytes(data=data, mime_type=mime_type),
            types.Part.from_text(text=_TRANSCRIPTION_PROMPT),
        ]

        try:
            transcript = client.generate_content(
                parts,
                model=_FLASH_MODEL,
                max_output_tokens=65536,
            )
        except Exception as e:
            return f"Error: transcription failed: {e}"

        return f"Transcript of {target.name} ({len(transcript)} chars):\n\n{transcript}"
