from prompt_toolkit.document import Document

from cfi_ai.ui import SlashCommandCompleter


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
