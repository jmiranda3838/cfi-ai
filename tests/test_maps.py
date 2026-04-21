from unittest.mock import MagicMock

from cfi_ai.maps import MapResult, dispatch_map, parse_map_invocation
from cfi_ai.workspace import Workspace


# --- parse_map_invocation tests ---

def test_parse_map_invocation_not_a_map():
    assert parse_map_invocation("hello world") is None


def test_parse_map_invocation_empty():
    assert parse_map_invocation("") is None


def test_parse_map_invocation_slash_only():
    assert parse_map_invocation("/") is None


def test_parse_map_invocation_simple():
    assert parse_map_invocation("/help") == ("help", None)


def test_parse_map_invocation_with_args():
    assert parse_map_invocation("/intake transcript.txt") == ("intake", "transcript.txt")


def test_parse_map_invocation_with_spaces():
    assert parse_map_invocation("  /help  ") == ("help", None)


def test_parse_map_invocation_multi_word_args():
    assert parse_map_invocation("/intake some file path.txt") == ("intake", "some file path.txt")


def test_parse_map_invocation_absolute_path_with_text():
    # Simplified absolute path followed by description — must NOT be parsed as a map
    assert (
        parse_map_invocation(
            "/var/folders/dv/abc/Screenshot.png this is what it looks like"
        )
        is None
    )


def test_parse_map_invocation_absolute_path_only():
    assert parse_map_invocation("/Users/jonzy/file.txt") is None


def test_parse_map_invocation_macos_screenshot_repro():
    # Exact shape of the user-reported failure: macOS temporary screenshot
    # path with backslash-escaped spaces, followed by descriptive text.
    user_input = (
        "/var/folders/dv/y7w2n1t13lj5grgw5mpxqrvm0000gn/T/TemporaryItems/"
        "NSIRD_screencaptureui_498Xvu/Screenshot\\ 2026-04-06\\ at\\ 3.48.08\\ PM.png"
        " this is what it looks like"
    )
    assert parse_map_invocation(user_input) is None


# --- dispatch_map tests ---

def test_dispatch_unknown_map():
    ui = MagicMock()
    ws = Workspace("/tmp")
    result = dispatch_map("nonexistent", None, ui, ws, MagicMock())
    assert result.error is not None
    assert "Unknown map" in result.error


def test_dispatch_help():
    ui = MagicMock()
    ws = Workspace("/tmp")
    result = dispatch_map("help", None, ui, ws, MagicMock())
    assert result.handled is True
    assert result.message is None
    assert result.error is None
    ui.render_markdown.assert_called_once()


def test_dispatch_help_lists_maps():
    ui = MagicMock()
    ws = Workspace("/tmp")
    dispatch_map("help", None, ui, ws, MagicMock())
    rendered = ui.render_markdown.call_args[0][0]
    assert "/help" in rendered
    assert "/intake" in rendered


def test_dispatch_help_shows_missing_record_contracts():
    ui = MagicMock()
    ws = Workspace("/tmp")
    dispatch_map("help", None, ui, ws, MagicMock())
    rendered = ui.render_markdown.call_args[0][0]
    assert "missing records may be surfaced as findings" in rendered
    assert "requires an existing treatment plan and progress notes to generate updates" in rendered


# --- MapResult tests ---

def test_map_result_parts_default():
    result = MapResult()
    assert result.parts is None
    assert result.message is None
    assert result.handled is False
    assert result.error is None
    assert result.map_mode is False
    assert result.plan_prompt is None


# --- Clinical map dispatch: prompt loaded directly, with invocation preface ---

def test_session_dispatch_loads_prompt(tmp_path):
    """/session dispatch loads the full map prompt with map_mode=True and plan_prompt set."""
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("session", None, ui, ws, MagicMock())
    assert result.error is None
    assert result.map_mode is True
    assert result.plan_prompt is not None  # session has a plan variant
    assert "User invoked /session" in result.message
    # The prompt content itself should be loaded (not an intent shim)
    assert "Progress Note Guidance" in result.message
    assert "Resolving Client Context" in result.message


def test_session_dispatch_preserves_user_args(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("session", "jane recording.m4a", ui, ws, MagicMock())
    assert result.error is None
    assert "jane recording.m4a" in result.message


def test_session_dispatch_no_args_preface(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("session", None, ui, ws, MagicMock())
    assert "User invoked /session with no arguments" in result.message


def test_compliance_dispatch_loads_prompt(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("compliance", "jane-doe", ui, ws, MagicMock())
    assert result.error is None
    assert result.map_mode is True
    assert result.plan_prompt is None  # compliance has no plan variant
    assert "User invoked /compliance" in result.message
    assert "jane-doe" in result.message
    assert "Compliance Report" in result.message


def test_tp_review_dispatch_loads_prompt(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("tp-review", "bob", ui, ws, MagicMock())
    assert result.error is None
    assert result.map_mode is True
    assert result.plan_prompt is None
    assert "User invoked /tp-review" in result.message
    assert "bob" in result.message
    assert "Treatment Plan Review Summary" in result.message


def test_wa_dispatch_loads_prompt(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("wellness-assessment", "carol wa-scan.pdf", ui, ws, MagicMock())
    assert result.error is None
    assert result.map_mode is True
    assert result.plan_prompt is None
    assert "User invoked /wellness-assessment" in result.message
    assert "carol wa-scan.pdf" in result.message
    assert "GD Score" in result.message or "GD score" in result.message


def test_intake_dispatch_loads_prompt(tmp_path):
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    result = dispatch_map("intake", "session.mp3", ui, ws, MagicMock())
    assert result.error is None
    assert result.map_mode is True
    assert result.plan_prompt is not None  # intake has a plan variant
    assert "User invoked /intake" in result.message
    assert "session.mp3" in result.message
    assert "Processing Intake Inputs" in result.message


def test_clinical_maps_do_not_preload_clients(tmp_path):
    """Dispatched prompts do not contain a pre-loaded `Available clients:` line."""
    (tmp_path / "clients" / "alice").mkdir(parents=True)
    (tmp_path / "clients" / "bob").mkdir(parents=True)
    ui = MagicMock()
    ws = Workspace(str(tmp_path))
    for name in ("session", "compliance", "tp-review", "wellness-assessment", "intake"):
        result = dispatch_map(name, None, ui, ws, MagicMock())
        assert "Available clients:" not in result.message, f"{name} leaked client list"
        assert "[MAP:" not in result.message, f"{name} still emits [MAP:] marker"
