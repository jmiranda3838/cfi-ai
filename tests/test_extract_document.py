"""Tests for the extract_document tool."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pymupdf
import pytest

from cfi_ai.tools.extract_document import ExtractDocumentTool
from cfi_ai.workspace import Workspace


def _make_pdf(path: Path, text: str) -> None:
    """Create a real PDF with the given text using pymupdf."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_definition():
    defn = ExtractDocumentTool().definition()
    assert defn.name == "extract_document"
    assert "path" in defn.input_schema["required"]
    assert "PDF" in defn.description


def test_not_mutating():
    assert ExtractDocumentTool().mutating is False


def test_file_not_found(tmp_path):
    ws = Workspace(str(tmp_path))
    result = ExtractDocumentTool().execute(ws, path="missing.pdf")
    assert "Error" in result
    assert "not a file" in result


def test_not_a_pdf(tmp_path):
    (tmp_path / "notes.txt").write_text("hello")
    ws = Workspace(str(tmp_path))
    result = ExtractDocumentTool().execute(ws, path="notes.txt")
    assert "Error" in result
    assert "not a PDF" in result


def test_workspace_escape(tmp_path):
    ws = Workspace(str(tmp_path))
    result = ExtractDocumentTool().execute(ws, path="../outside.pdf")
    assert "Error" in result


def test_text_extraction_success(tmp_path):
    pdf = tmp_path / "doc.pdf"
    long_text = "This is a test document with enough text to exceed the minimum threshold for extraction."
    _make_pdf(pdf, long_text)
    ws = Workspace(str(tmp_path))
    result = ExtractDocumentTool().execute(ws, path="doc.pdf")
    assert "Extracted from doc.pdf" in result
    assert "chars" in result
    assert "test document" in result


def test_text_extraction_short_text(tmp_path):
    """Short text is returned as-is (no threshold gate)."""
    pdf = tmp_path / "short.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    mock_module = MagicMock()
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Short"
    mock_doc.__iter__ = lambda self: iter([mock_page])
    mock_module.open.return_value = mock_doc

    with patch.dict(sys.modules, {"pymupdf": mock_module}):
        result = ExtractDocumentTool().execute(Workspace(str(tmp_path)), path="short.pdf")
    assert "Extracted from short.pdf" in result
    assert "Short" in result


def test_text_extraction_empty(tmp_path):
    """Empty extraction suggests using attach_path."""
    pdf = tmp_path / "blank.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    mock_module = MagicMock()
    mock_doc = MagicMock()
    mock_doc.__iter__ = lambda self: iter([])
    mock_module.open.return_value = mock_doc

    with patch.dict(sys.modules, {"pymupdf": mock_module}):
        result = ExtractDocumentTool().execute(Workspace(str(tmp_path)), path="blank.pdf")
    assert "No text extracted" in result
    assert "attach_path" in result


def test_text_extraction_whitespace_only(tmp_path):
    """Whitespace-only extraction suggests using attach_path."""
    pdf = tmp_path / "ws.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    mock_module = MagicMock()
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "   \n  \n  "
    mock_doc.__iter__ = lambda self: iter([mock_page])
    mock_module.open.return_value = mock_doc

    with patch.dict(sys.modules, {"pymupdf": mock_module}):
        result = ExtractDocumentTool().execute(Workspace(str(tmp_path)), path="ws.pdf")
    assert "No text extracted" in result
    assert "attach_path" in result


def test_pymupdf_import_error(tmp_path):
    """When pymupdf is unavailable, suggests attach_path."""
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    with patch.dict(sys.modules, {"pymupdf": None}):
        result = ExtractDocumentTool().execute(Workspace(str(tmp_path)), path="scan.pdf")
    assert "PyMuPDF" in result
    assert "attach_path" in result


def test_pymupdf_exception(tmp_path):
    """When pymupdf.open raises, suggests attach_path."""
    pdf = tmp_path / "corrupt.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    mock_module = MagicMock()
    mock_module.open.side_effect = RuntimeError("corrupt file")

    with patch.dict(sys.modules, {"pymupdf": mock_module}):
        result = ExtractDocumentTool().execute(Workspace(str(tmp_path)), path="corrupt.pdf")
    assert "extraction failed" in result
    assert "attach_path" in result


def test_absolute_path(tmp_path):
    """Absolute path bypasses workspace.validate_path()."""
    pdf = tmp_path / "outside" / "doc.pdf"
    pdf.parent.mkdir()
    long_text = "This document lives outside the workspace root and should still be accessible via absolute path."
    _make_pdf(pdf, long_text)

    # Workspace points somewhere else entirely
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    ws = Workspace(str(ws_dir))

    result = ExtractDocumentTool().execute(ws, path=str(pdf))
    assert "Extracted from doc.pdf" in result
    assert "chars" in result
