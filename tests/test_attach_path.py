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


def test_absolute_with_escaped_spaces(tmp_path):
    f = tmp_path / "Screenshot 2026-04-06 at 5.15.13 PM.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
    ws = Workspace(str(tmp_path / "other"))
    (tmp_path / "other").mkdir()
    escaped = str(f).replace(" ", "\\ ")
    result = AttachPathTool().execute(ws, path=escaped)
    assert isinstance(result, tuple)
    text, _ = result
    assert "Screenshot 2026-04-06 at 5.15.13 PM.png" in text


def test_absolute_with_quoted_path(tmp_path):
    f = tmp_path / "name with spaces.txt"
    f.write_text("ok")
    ws = Workspace(str(tmp_path / "other"))
    (tmp_path / "other").mkdir()
    result = AttachPathTool().execute(ws, path=f'"{f}"')
    assert isinstance(result, str)
    assert "ok" in result


def test_relative_with_escaped_spaces(tmp_path):
    (tmp_path / "my file.txt").write_text("hi")
    ws = Workspace(str(tmp_path))
    result = AttachPathTool().execute(ws, path="my\\ file.txt")
    assert isinstance(result, str)
    assert "hi" in result


def test_absolute_with_tilde_expansion(tmp_path, monkeypatch):
    """The resolver must honor ~ expansion so the model can pass paths
    like ~/Desktop/foo.png as advertised in the tool description."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / "Desktop").mkdir()
    target = fake_home / "Desktop" / "note.txt"
    target.write_text("from home")

    monkeypatch.setenv("HOME", str(fake_home))

    ws = Workspace(str(tmp_path / "workspace"))
    (tmp_path / "workspace").mkdir()

    result = AttachPathTool().execute(ws, path="~/Desktop/note.txt")
    assert isinstance(result, str)
    assert "from home" in result


def test_backslash_in_filename_not_corrupted(tmp_path):
    """Regression: the resolver must not strip backslashes that precede
    alphanumerics — otherwise Windows-style paths like C:\\Users\\name
    would be mangled. We can't actually create C:\\... on macOS, so we
    instead verify that a path with literal '\\U' in it produces a clean
    'not a file' error referencing the original (un-mangled) string."""
    ws = Workspace(str(tmp_path))
    weird = "C:\\Users\\nobody\\file.txt"
    result = AttachPathTool().execute(ws, path=weird)
    assert isinstance(result, str)
    # The error message should still contain the original backslashes,
    # proving the resolver did not silently rewrite \U → U.
    assert "\\Users\\nobody" in result or "C:\\Users" in result
