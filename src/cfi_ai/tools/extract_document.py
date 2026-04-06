from pathlib import Path

from cfi_ai.tools.base import BaseTool, ToolDefinition


class ExtractDocumentTool(BaseTool):
    name = "extract_document"
    mutating = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=(
                "Extract text from a PDF using PyMuPDF. Best for digital/typed PDFs. "
                "If the result is incomplete (e.g., form labels without responses), "
                "use attach_path instead to load the PDF visually."
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

        try:
            import pymupdf
            doc = pymupdf.open(str(target))
            text = "\n\n".join(page.get_text() for page in doc)
            doc.close()
        except ImportError:
            return (
                f"PyMuPDF is not installed. Use attach_path(path='{raw}') "
                "to load this PDF visually instead."
            )
        except Exception:
            return (
                f"Text extraction failed for {target.name}. "
                f"Use attach_path(path='{raw}') to load it visually instead."
            )

        if not text.strip():
            return (
                f"No text extracted from {target.name}. This may be a scanned or "
                f"image-based PDF — use attach_path(path='{raw}') to load it visually."
            )

        return f"Extracted from {target.name} ({len(text)} chars):\n\n{text}"
