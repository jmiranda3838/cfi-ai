from unittest.mock import patch

from prompt_toolkit.document import Document

from cfi_ai.ui import SlashCommandCompleter, PlanApproval, UI


def _get_completions(completer, text):
    doc = Document(text, len(text))
    return list(completer.get_completions(doc, None))


def test_completer_yields_on_slash():
    c = SlashCommandCompleter()
    c.set_commands({"help": "Show help", "intake": "Process intake"})
    completions = _get_completions(c, "/")
    names = [comp.text for comp in completions]
    assert "help" in names
    assert "intake" in names


def test_completer_filters_by_prefix():
    c = SlashCommandCompleter()
    c.set_commands({"help": "Show help", "intake": "Process intake"})
    completions = _get_completions(c, "/in")
    names = [comp.text for comp in completions]
    assert names == ["intake"]


def test_completer_empty_after_space():
    c = SlashCommandCompleter()
    c.set_commands({"intake": "Process intake"})
    completions = _get_completions(c, "/intake ")
    assert completions == []


def test_completer_no_completions_without_slash():
    c = SlashCommandCompleter()
    c.set_commands({"help": "Show help", "intake": "Process intake"})
    completions = _get_completions(c, "help")
    assert completions == []


def test_stream_markdown_no_visible_overflow(tmp_path):
    """stream_markdown must not use vertical_overflow='visible' (causes duplication)."""
    from unittest.mock import patch, MagicMock
    from rich.live import Live
    from cfi_ai.ui import UI

    captured_kwargs = {}
    original_live_init = Live.__init__

    def _capturing_live_init(self, *args, **kwargs):
        captured_kwargs.update(kwargs)
        original_live_init(self, *args, **kwargs)

    with patch("cfi_ai.ui.Path.home", return_value=tmp_path), \
         patch("cfi_ai.ui.PromptSession"):
        ui = UI()

    with patch.object(Live, "__init__", _capturing_live_init), \
         patch.object(Live, "__enter__", lambda self: self), \
         patch.object(Live, "__exit__", lambda *a: None), \
         patch.object(Live, "update", lambda *a: None):
        result = ui.stream_markdown(iter(["hello ", "world"]))

    assert result == "hello world"
    assert captured_kwargs.get("vertical_overflow", "ellipsis") != "visible"


def _make_ui(tmp_path):
    """Create a UI instance with mocked session."""
    with patch("cfi_ai.ui.Path.home", return_value=tmp_path), \
         patch("cfi_ai.ui.PromptSession") as mock_session_cls:
        ui = UI()
    return ui, mock_session_cls.return_value


class TestPromptPlanApproval:
    """Test prompt_plan_approval() input parsing."""

    def test_empty_returns_clear_bypass(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        session.prompt.return_value = ""
        assert ui.prompt_plan_approval() == PlanApproval.CLEAR_BYPASS

    def test_y_lower_returns_clear_bypass(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        session.prompt.return_value = "y"
        assert ui.prompt_plan_approval() == PlanApproval.CLEAR_BYPASS

    def test_y_upper_returns_clear_bypass(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        session.prompt.return_value = "Y"
        assert ui.prompt_plan_approval() == PlanApproval.CLEAR_BYPASS

    def test_b_returns_bypass(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        session.prompt.return_value = "b"
        assert ui.prompt_plan_approval() == PlanApproval.BYPASS

    def test_p_returns_permissions(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        session.prompt.return_value = "p"
        assert ui.prompt_plan_approval() == PlanApproval.PERMISSIONS

    def test_n_returns_reject(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        session.prompt.return_value = "n"
        assert ui.prompt_plan_approval() == PlanApproval.REJECT

    def test_unknown_returns_reject(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        session.prompt.return_value = "anything else"
        assert ui.prompt_plan_approval() == PlanApproval.REJECT

    def test_eof_returns_reject(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        session.prompt.side_effect = EOFError
        assert ui.prompt_plan_approval() == PlanApproval.REJECT
