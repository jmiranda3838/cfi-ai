from cfi_ai.tools.read_audio import ReadAudioTool
from cfi_ai.workspace import Workspace


def test_read_audio_relative_path(tmp_path):
    audio_file = tmp_path / "session.mp3"
    audio_data = b"\xff\xfb\x90\x00" + b"\x00" * 100
    audio_file.write_bytes(audio_data)
    ws = Workspace(str(tmp_path))
    result = ReadAudioTool().execute(ws, path="session.mp3")
    assert isinstance(result, tuple)
    text, parts = result
    assert "session.mp3" in text
    assert "audio/mp3" in text
    assert len(parts) == 1


def test_read_audio_absolute_path(tmp_path):
    audio_file = tmp_path / "recording.m4a"
    audio_data = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 50
    audio_file.write_bytes(audio_data)
    ws = Workspace(str(tmp_path / "other"))
    (tmp_path / "other").mkdir()
    result = ReadAudioTool().execute(ws, path=str(audio_file))
    assert isinstance(result, tuple)
    text, parts = result
    assert "recording.m4a" in text
    assert "audio/mp4" in text


def test_read_audio_unsupported_format(tmp_path):
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")
    ws = Workspace(str(tmp_path))
    result = ReadAudioTool().execute(ws, path="doc.pdf")
    assert isinstance(result, str)
    assert "unsupported audio format" in result


def test_read_audio_missing_file(tmp_path):
    ws = Workspace(str(tmp_path))
    result = ReadAudioTool().execute(ws, path="nonexistent.mp3")
    assert isinstance(result, str)
    assert "not a file" in result


def test_read_audio_inline_part(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_data = b"RIFF" + b"\x00" * 40
    audio_file.write_bytes(audio_data)
    ws = Workspace(str(tmp_path))
    result = ReadAudioTool().execute(ws, path="test.wav")
    assert isinstance(result, tuple)
    text, parts = result
    assert len(parts) == 1
    part = parts[0]
    assert part.inline_data is not None
    assert part.inline_data.mime_type == "audio/wav"
    assert part.inline_data.data == audio_data
