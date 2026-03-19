from pathlib import Path

from google.genai import types

from cfi_ai.tools.base import BaseTool, ToolDefinition

_MIN_TEXT_LENGTH = 50

_EXTRACTION_PROMPT = """\
Extract all text and data from this document as markdown.
For forms: indicate checked/unchecked status for checkboxes.
For handwritten responses: transcribe accurately. Mark illegible text as [illegible].
Preserve the document's structure and field labels."""

_FLASH_MODEL = "gemini-3.1-flash-lite-preview"


class ExtractDocumentTool(BaseTool):
    name = "extract_document"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Extract text and data from a PDF document. Returns content as markdown. "
                "Uses text extraction for digital PDFs; falls back to vision for "
                "scanned/handwritten forms."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the PDF file (absolute or relative to workspace).",
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

        if target.suffix.lower() != ".pdf":
            return f"Error: '{target.name}' is not a PDF file."

        # Try text extraction with PyMuPDF
        try:
            import pymupdf
            doc = pymupdf.open(str(target))
            text = "\n\n".join(page.get_text() for page in doc)
            doc.close()
        except ImportError:
            text = ""
        except Exception:
            text = ""

        if len(text.strip()) >= _MIN_TEXT_LENGTH:
            return f"Extracted from {target.name} ({len(text)} chars):\n\n{text}"

        # Fall back to Gemini vision for scanned/handwritten forms
        if client is None:
            if text.strip():
                return f"Extracted from {target.name} ({len(text)} chars):\n\n{text}"
            return "Error: extract_document requires an API client for scanned PDFs (not available in plan mode)."

        try:
            data = target.read_bytes()
        except PermissionError:
            return f"Error: permission denied reading '{raw}'."

        parts = [
            types.Part.from_bytes(data=data, mime_type="application/pdf"),
            types.Part.from_text(text=_EXTRACTION_PROMPT),
        ]

        try:
            extracted = client.generate_content(
                parts,
                model=_FLASH_MODEL,
                max_output_tokens=65536,
            )
        except Exception as e:
            return f"Error: document extraction failed: {e}"

        return f"Extracted from {target.name} ({len(extracted)} chars):\n\n{extracted}"
