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
