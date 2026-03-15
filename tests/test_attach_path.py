import pytest

from cfi_ai.tools.attach_path import AttachPathTool
from cfi_ai.workspace import Workspace


def test_text_file(tmp_path):
    (tmp_path / "hello.txt").write_text("hello world")
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws, path="hello.txt")
    assert isinstance(result, str)
    assert "hello.txt" in result
    assert "hello world" in result
    assert "11 chars" in result


def test_text_file_absolute(tmp_path):
    f = tmp_path / "abs.txt"
    f.write_text("absolute content")
    ws = Workspace(str(tmp_path / "other"))
    (tmp_path / "other").mkdir()
    result = AttachPathTool().execute(ws, path=str(f))
    assert isinstance(result, str)
    assert "absolute content" in result


def test_audio_mp3(tmp_path):
    audio_file = tmp_path / "session.mp3"
    audio_data = b"\xff\xfb\x90\x00" + b"\x00" * 100
    audio_file.write_bytes(audio_data)
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws, path="session.mp3")
    assert isinstance(result, tuple)
    text, parts = result
    assert "session.mp3" in text
    assert "audio/mp3" in text
    assert "in context" in text
    assert len(parts) == 1
    assert parts[0].inline_data is not None
    assert parts[0].inline_data.mime_type == "audio/mp3"


def test_audio_m4a_absolute(tmp_path):
    audio_file = tmp_path / "recording.m4a"
    audio_data = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 50
    audio_file.write_bytes(audio_data)
    ws = Workspace(str(tmp_path / "other"))
    (tmp_path / "other").mkdir()
    result = AttachPathTool().execute(ws, path=str(audio_file))
    assert isinstance(result, tuple)
    text, parts = result
    assert "recording.m4a" in text
    assert "audio/mp4" in text


def test_image_png(tmp_path):
    img_file = tmp_path / "photo.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws, path="photo.png")
    assert isinstance(result, tuple)
    text, parts = result
    assert "photo.png" in text
    assert "image/png" in text
    assert len(parts) == 1


def test_image_jpg(tmp_path):
    img_file = tmp_path / "photo.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws, path="photo.jpg")
    assert isinstance(result, tuple)
    text, parts = result
    assert "image/jpeg" in text


def test_pdf(tmp_path):
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4" + b"\x00" * 50)
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws, path="doc.pdf")
    assert isinstance(result, tuple)
    text, parts = result
    assert "application/pdf" in text


def test_missing_file(tmp_path):
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws, path="nonexistent.txt")
    assert isinstance(result, str)
    assert "not a file" in result


def test_workspace_escape(tmp_path):
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws, path="../outside.txt")
    assert isinstance(result, str)
    assert "Error" in result


def test_text_truncation(tmp_path):
    (tmp_path / "big.txt").write_text("x" * 200_000)
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws, path="big.txt")
    assert isinstance(result, str)
    assert "truncated" in result
