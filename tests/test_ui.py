from unittest.mock import patch

from prompt_toolkit.document import Document

from cfi_ai.ui import PlanApproval, SlashMapCompleter, UI


def _get_completions(completer, text):
    doc = Document(text, len(text))
    return list(completer.get_completions(doc, None))


def test_completer_yields_on_slash():
    c = SlashMapCompleter()
    c.set_maps({"help": "Show help", "intake": "Process intake"})
    completions = _get_completions(c, "/")
    names = [comp.text for comp in completions]
    assert "help" in names
    assert "intake" in names


def test_completer_filters_by_prefix():
    c = SlashMapCompleter()
    c.set_maps({"help": "Show help", "intake": "Process intake"})
    completions = _get_completions(c, "/in")
    names = [comp.text for comp in completions]
    assert names == ["intake"]


def test_completer_empty_after_space():
    c = SlashMapCompleter()
    c.set_maps({"intake": "Process intake"})
    completions = _get_completions(c, "/intake ")
    assert completions == []


def test_completer_no_completions_without_slash():
    c = SlashMapCompleter()
    c.set_maps({"help": "Show help", "intake": "Process intake"})
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
    """Test prompt_plan_approval() interactive menu."""

    def test_bypass(self, tmp_path):
        ui, _ = _make_ui(tmp_path)
        ui._run_plan_approval_app = lambda: PlanApproval.BYPASS
        assert ui.prompt_plan_approval() == PlanApproval.BYPASS

    def test_approve(self, tmp_path):
        ui, _ = _make_ui(tmp_path)
        ui._run_plan_approval_app = lambda: PlanApproval.APPROVE
        assert ui.prompt_plan_approval() == PlanApproval.APPROVE

    def test_reject(self, tmp_path):
        ui, _ = _make_ui(tmp_path)
        ui._run_plan_approval_app = lambda: PlanApproval.REJECT
        assert ui.prompt_plan_approval() == PlanApproval.REJECT

    def test_eof_returns_reject(self, tmp_path):
        from unittest.mock import Mock
        ui, _ = _make_ui(tmp_path)
        ui._run_plan_approval_app = Mock(side_effect=EOFError)
        assert ui.prompt_plan_approval() == PlanApproval.REJECT

    def test_keyboard_interrupt_propagates(self, tmp_path):
        import pytest
        from unittest.mock import Mock
        ui, _ = _make_ui(tmp_path)
        ui._run_plan_approval_app = Mock(side_effect=KeyboardInterrupt)
        with pytest.raises(KeyboardInterrupt):
            ui.prompt_plan_approval()


def test_approval_options_covers_all_enum_values():
    from cfi_ai.ui import _APPROVAL_OPTIONS, PlanApproval
    option_values = {opt[0] for opt in _APPROVAL_OPTIONS}
    assert option_values == set(PlanApproval)


class TestPromptApproval:
    """Test prompt_approval() — the y/n confirmation for mutating tool calls."""

    def test_passes_multiline_false_even_when_session_polluted(self, tmp_path):
        """Regression: prompt_toolkit's PromptSession.prompt() permanently
        mutates session.multiline. A prior multiline interview question can
        leave session.multiline=True; prompt_approval must explicitly pass
        multiline=False so Enter submits instead of inserting a newline."""
        ui, session = _make_ui(tmp_path)
        # Simulate a prior multiline call having flipped session state
        session.multiline = True
        session.prompt.return_value = "y"

        assert ui.prompt_approval() is True

        _, kwargs = session.prompt.call_args
        assert kwargs.get("multiline") is False

    def test_yes_inputs(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        for ans in ("", "y", "Y", "yes", "YES"):
            session.prompt.return_value = ans
            assert ui.prompt_approval() is True

    def test_no_inputs(self, tmp_path):
        ui, session = _make_ui(tmp_path)
        for ans in ("n", "no", "nope", "anything else"):
            session.prompt.return_value = ans
            assert ui.prompt_approval() is False

    def test_uses_approval_key_bindings_not_chat(self, tmp_path):
        """Regression: prompt_approval() must use _approval_key_bindings(),
        not _chat_key_bindings(). The chat bindings exit Escape with result='',
        and the ('', 'y', 'yes') check would treat that as YES — silently
        approving a mutation. Patch the helper to a sentinel and assert it's
        the value passed to session.prompt."""
        from unittest.mock import patch as _patch
        ui, session = _make_ui(tmp_path)
        session.prompt.return_value = "y"
        sentinel = object()
        with _patch("cfi_ai.ui._approval_key_bindings", return_value=sentinel) as helper:
            ui.prompt_approval()
        helper.assert_called_once()
        _, kwargs = session.prompt.call_args
        assert kwargs.get("key_bindings") is sentinel

    def test_escape_does_not_approve(self, tmp_path):
        """Companion to the binding-wiring test: when the Escape handler
        raises EOFError (which is what _approval_key_bindings does), the
        function returns False, NOT True via the ('', ...) check."""
        ui, session = _make_ui(tmp_path)
        session.prompt.side_effect = EOFError
        assert ui.prompt_approval() is False

    def test_keyboard_interrupt_propagates(self, tmp_path):
        import pytest
        ui, session = _make_ui(tmp_path)
        session.prompt.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            ui.prompt_approval()


class TestGetInput:
    """Test get_input() — the main chat prompt."""

    def test_uses_multiline_true(self, tmp_path):
        """Regression: get_input() must pass multiline=True so pasted multi-line
        content remains visible. Before this fix, multiline=False caused the
        single-line renderer to hide everything except the line under the cursor
        after a paste, making previously-typed text disappear from view (even
        though it was still in the buffer and got submitted to the model)."""
        ui, session = _make_ui(tmp_path)
        session.prompt.return_value = "hello"

        result = ui.get_input()
        assert result is not None
        assert result.text == "hello"

        _, kwargs = session.prompt.call_args
        assert kwargs.get("multiline") is True, \
            f"get_input() must pass multiline=True (got {kwargs.get('multiline')!r})"

    def test_chat_key_bindings_enter_submits(self):
        """Chat prompt must bind Enter to validate_and_handle (submit), not
        the multiline default of inserting a newline. Otherwise users would
        have to press Alt+Enter to submit single-line messages — a UX regression."""
        from unittest.mock import MagicMock
        from prompt_toolkit.keys import Keys
        from cfi_ai.ui import _chat_key_bindings

        kb = _chat_key_bindings()
        # prompt-toolkit normalizes "enter" to Keys.ControlM internally, so look
        # up by enum value rather than by string.
        bindings = kb.get_bindings_for_keys((Keys.ControlM,))
        assert len(bindings) >= 1, "Enter must be bound on the chat key bindings"

        event = MagicMock()
        bindings[0].handler(event)
        event.current_buffer.validate_and_handle.assert_called_once()

    def test_chat_key_bindings_alt_enter_inserts_newline(self):
        """Chat prompt must bind Alt+Enter (Escape, Enter) to insert a literal
        newline so users can compose intentional multi-line messages."""
        from unittest.mock import MagicMock
        from prompt_toolkit.keys import Keys
        from cfi_ai.ui import _chat_key_bindings

        kb = _chat_key_bindings()
        # Alt+Enter is the Escape-prefix sequence (Keys.Escape, Keys.ControlM).
        bindings = kb.get_bindings_for_keys((Keys.Escape, Keys.ControlM))
        assert len(bindings) >= 1, "Alt+Enter must be bound on the chat key bindings"

        event = MagicMock()
        bindings[0].handler(event)
        event.current_buffer.insert_text.assert_called_once_with("\n")

    def test_chat_key_bindings_preserves_existing(self):
        """Existing bindings (Escape cancel, Ctrl+D disabled, Shift+Tab plan
        toggle) must still resolve to handlers after adding the new ones."""
        from prompt_toolkit.keys import Keys
        from cfi_ai.ui import _chat_key_bindings

        kb = _chat_key_bindings()
        assert kb.get_bindings_for_keys((Keys.Escape,)), "Escape must still be bound"
        assert kb.get_bindings_for_keys((Keys.ControlD,)), "Ctrl+D must still be bound"
        assert kb.get_bindings_for_keys((Keys.BackTab,)), "Shift+Tab must still be bound"
