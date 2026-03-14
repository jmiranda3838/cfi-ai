from unittest.mock import MagicMock, patch

from cfi_ai.commands.intake import (
    _AudioInput,
    _TextInput,
    _get_audio_mime_type,
    _resolve_input,
    handle_intake,
    _build_existing_clients_section,
)
from cfi_ai.workspace import Workspace

from pathlib import Path


# --- _get_audio_mime_type tests ---

def test_get_audio_mime_type_mp3():
    assert _get_audio_mime_type(Path("session.mp3")) == "audio/mp3"


def test_get_audio_mime_type_wav():
    assert _get_audio_mime_type(Path("session.wav")) == "audio/wav"


def test_get_audio_mime_type_m4a():
    assert _get_audio_mime_type(Path("session.m4a")) == "audio/mp4"


def test_get_audio_mime_type_txt_returns_none():
    assert _get_audio_mime_type(Path("session.txt")) is None


def test_get_audio_mime_type_case_insensitive():
    assert _get_audio_mime_type(Path("session.MP3")) == "audio/mp3"
    assert _get_audio_mime_type(Path("session.Wav")) == "audio/wav"


def test_get_audio_mime_type_no_extension():
    assert _get_audio_mime_type(Path("session")) is None


# --- _resolve_input tests ---

def test_resolve_input_text_file(tmp_path):
    transcript_file = tmp_path / "session.txt"
    transcript_file.write_text("Client discussed anxiety symptoms.")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = _resolve_input("session.txt", ui, ws)
    assert isinstance(result, _TextInput)
    assert result.text == "Client discussed anxiety symptoms."


def test_resolve_input_audio_file(tmp_path):
    audio_file = tmp_path / "session.mp3"
    audio_data = b"\xff\xfb\x90\x00" + b"\x00" * 100  # fake mp3 bytes
    audio_file.write_bytes(audio_data)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = _resolve_input("session.mp3", ui, ws)
    assert isinstance(result, _AudioInput)
    assert result.mime_type == "audio/mp3"
    assert result.data == audio_data
    assert result.filename == "session.mp3"


def test_resolve_input_missing_file(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = _resolve_input("nonexistent.txt", ui, ws)
    assert result is None
    ui.print_error.assert_called_once()


def test_resolve_input_absolute_path_audio(tmp_path):
    """Absolute path to an audio file outside the workspace resolves correctly."""
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    audio_file = external_dir / "recording.m4a"
    audio_data = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 50
    audio_file.write_bytes(audio_data)
    ui = MagicMock()
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    ws = Workspace(str(ws_dir))
    result = _resolve_input(str(audio_file), ui, ws)
    assert isinstance(result, _AudioInput)
    assert result.mime_type == "audio/mp4"
    assert result.data == audio_data


def test_resolve_input_absolute_path_text(tmp_path):
    """Absolute path to a text file outside the workspace resolves correctly."""
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    text_file = external_dir / "session.txt"
    text_file.write_text("External transcript content.")
    ui = MagicMock()
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    ws = Workspace(str(ws_dir))
    result = _resolve_input(str(text_file), ui, ws)
    assert isinstance(result, _TextInput)
    assert result.text == "External transcript content."


def test_resolve_input_absolute_path_missing(tmp_path):
    """Absolute path to a nonexistent file returns None with error."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = _resolve_input("/tmp/nonexistent_intake_file.txt", ui, ws)
    assert result is None
    ui.print_error.assert_called_once()


def test_resolve_input_path_escape(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = _resolve_input("../../etc/passwd", ui, ws)
    assert result is None
    ui.print_error.assert_called_once()


def test_resolve_input_interactive_paste(tmp_path):
    ui = MagicMock()
    ui.prompt_multiline.return_value = "This is pasted transcript text.\nWith multiple lines."
    ws = Workspace(str(tmp_path))
    result = _resolve_input(None, ui, ws)
    assert isinstance(result, _TextInput)
    assert result.text == "This is pasted transcript text.\nWith multiple lines."


def test_resolve_input_interactive_text_file(tmp_path):
    transcript_file = tmp_path / "session.txt"
    transcript_file.write_text("Transcript from file via interactive.")
    ui = MagicMock()
    ui.prompt_multiline.return_value = "session.txt"
    ws = Workspace(str(tmp_path))
    result = _resolve_input(None, ui, ws)
    assert isinstance(result, _TextInput)
    assert result.text == "Transcript from file via interactive."


def test_resolve_input_interactive_audio_file(tmp_path):
    audio_file = tmp_path / "recording.m4a"
    audio_data = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 50
    audio_file.write_bytes(audio_data)
    ui = MagicMock()
    ui.prompt_multiline.return_value = "recording.m4a"
    ws = Workspace(str(tmp_path))
    result = _resolve_input(None, ui, ws)
    assert isinstance(result, _AudioInput)
    assert result.mime_type == "audio/mp4"
    assert result.data == audio_data


def test_resolve_input_cancelled(tmp_path):
    ui = MagicMock()
    ui.prompt_multiline.return_value = None
    ws = Workspace(str(tmp_path))
    result = _resolve_input(None, ui, ws)
    assert result is None
    ui.print_info.assert_called()


def test_resolve_input_empty_input(tmp_path):
    ui = MagicMock()
    ui.prompt_multiline.return_value = "   "
    ws = Workspace(str(tmp_path))
    result = _resolve_input(None, ui, ws)
    assert result is None


# --- _build_existing_clients_section tests ---

def test_existing_clients_none(tmp_path):
    ws = Workspace(str(tmp_path))
    section = _build_existing_clients_section(ws)
    assert "No existing clients" in section


def test_existing_clients_with_data(tmp_path):
    client_dir = tmp_path / "clients" / "jane-doe"
    (client_dir / "profile").mkdir(parents=True)
    (client_dir / "profile" / "current.md").write_text("# Jane Doe profile")
    ws = Workspace(str(tmp_path))
    section = _build_existing_clients_section(ws)
    assert "jane-doe" in section
    assert "Jane Doe profile" in section


# --- handle_intake integration tests ---

def test_handle_intake_from_file(tmp_path):
    transcript_file = tmp_path / "session.txt"
    transcript_file.write_text("Session transcript content here.")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.txt", ui, ws)
    assert result.message is not None
    assert "Session transcript content here." in result.message
    assert result.handled is False
    assert result.parts is None


def test_handle_intake_audio_file(tmp_path):
    audio_file = tmp_path / "session.mp3"
    audio_data = b"\xff\xfb\x90\x00" + b"\x00" * 100
    audio_file.write_bytes(audio_data)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.mp3", ui, ws)
    assert result.parts is not None
    assert len(result.parts) == 2
    assert result.message is None
    # First part is the text prompt
    assert result.parts[0].text is not None
    assert "session.mp3" in result.parts[0].text
    # Second part is the audio data
    assert result.parts[1].inline_data is not None
    assert result.parts[1].inline_data.mime_type == "audio/mp3"


def test_handle_intake_text_still_works(tmp_path):
    """Regression: text flow still returns CommandResult(message=...)."""
    transcript_file = tmp_path / "notes.txt"
    transcript_file.write_text("Client presented with low mood.")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("notes.txt", ui, ws)
    assert result.message is not None
    assert result.parts is None
    assert "Client presented with low mood." in result.message


def test_handle_intake_cancelled(tmp_path):
    ui = MagicMock()
    ui.prompt_multiline.return_value = None
    ws = Workspace(str(tmp_path))
    result = handle_intake(None, ui, ws)
    assert result.handled is True
    assert result.message is None
    assert result.parts is None


def test_handle_intake_message_structure(tmp_path):
    transcript_file = tmp_path / "session.txt"
    transcript_file.write_text("Test transcript.")
    (tmp_path / "clients" / "existing-client" / "profile").mkdir(parents=True)
    (tmp_path / "clients" / "existing-client" / "profile" / "current.md").write_text("Profile data")
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = handle_intake("session.txt", ui, ws)
    msg = result.message
    # Should contain the transcript
    assert "<transcript>" in msg
    assert "Test transcript." in msg
    assert "</transcript>" not in msg or "</transcript>" in msg  # just check delimiters
    # Should contain existing clients info
    assert "existing-client" in msg
    # Should contain workflow instructions
    assert "Intake Assessment" in msg
    assert "Treatment Plan" in msg
    # Should contain today's date
    import datetime
    assert datetime.date.today().isoformat() in msg
