"""Tests for completed-turn notifications in the agent loop."""

from unittest.mock import MagicMock, patch

from google.genai import types

from cfi_ai.agent import _run_main_loop
from cfi_ai.config import Config
from cfi_ai.cost_tracker import CostTracker
from cfi_ai.maps import MapResult
from cfi_ai.tools import END_TURN_TOOL_NAME
from cfi_ai.ui import UserInput


class _StreamResultStub:
    def __init__(
        self,
        *,
        parts: list[types.Part] | None = None,
        function_calls: list | None = None,
        request_id: str = "req-1",
    ) -> None:
        self.parts = parts or []
        self.coalesced_parts = self.parts
        self.function_calls = function_calls or []
        self.grounding_metadata = None
        self.usage_metadata = None
        self.request_id = request_id

    def text_chunks(self):
        return iter(())

    def log_completion(self) -> None:
        return None


def _make_config() -> Config:
    return Config(
        project="p",
        location="global",
        model="gemini-3-flash-preview",
        max_tokens=8192,
        grounding_enabled=False,
        notifications_popup_enabled=True,
        notifications_sound_enabled=False,
    )


def _make_ui(inputs: list[UserInput | None], *, streamed_text: list | None = None) -> MagicMock:
    ui = MagicMock()
    ui.get_input.side_effect = inputs
    ui.stream_markdown.side_effect = streamed_text or [""]
    return ui


def test_notifies_once_on_normal_completed_turn():
    config = _make_config()
    client = MagicMock()
    completed = _StreamResultStub(parts=[types.Part.from_text(text="Done.")])
    client.stream_response.side_effect = [completed, completed]
    ui = _make_ui([UserInput(text="hello"), None], streamed_text=["Done.", "Done."])
    session_store = MagicMock()

    with patch("cfi_ai.agent.notify_turn_complete") as mock_notify:
        _run_main_loop(
            client=client,
            ui=ui,
            workspace=MagicMock(),
            system_prompt="sys",
            config=config,
            messages=[],
            api_tools=[],
            cache_manager=None,
            session_store=session_store,
            cost_tracker=CostTracker(model=config.model),
        )

    mock_notify.assert_called_once_with(config)


def test_notifies_once_on_tool_only_completed_turn():
    config = _make_config()
    client = MagicMock()
    end_turn_fc = MagicMock()
    end_turn_fc.name = END_TURN_TOOL_NAME
    end_turn_fc.args = {}
    client.stream_response.return_value = _StreamResultStub(
        parts=[types.Part.from_text(text="")],
        function_calls=[end_turn_fc],
    )
    ui = _make_ui([UserInput(text="hello"), None], streamed_text=[""])
    session_store = MagicMock()

    with patch("cfi_ai.agent.notify_turn_complete") as mock_notify:
        _run_main_loop(
            client=client,
            ui=ui,
            workspace=MagicMock(),
            system_prompt="sys",
            config=config,
            messages=[],
            api_tools=[],
            cache_manager=None,
            session_store=session_store,
            cost_tracker=CostTracker(model=config.model),
        )

    mock_notify.assert_called_once_with(config)


def test_does_not_notify_on_cancelled_stream():
    config = _make_config()
    client = MagicMock()
    client.stream_response.return_value = _StreamResultStub(
        parts=[types.Part.from_text(text="partial")],
    )
    ui = _make_ui([UserInput(text="hello"), None], streamed_text=[KeyboardInterrupt()])
    session_store = MagicMock()

    with patch("cfi_ai.agent.notify_turn_complete") as mock_notify:
        _run_main_loop(
            client=client,
            ui=ui,
            workspace=MagicMock(),
            system_prompt="sys",
            config=config,
            messages=[],
            api_tools=[],
            cache_manager=None,
            session_store=session_store,
            cost_tracker=CostTracker(model=config.model),
        )

    mock_notify.assert_not_called()


def test_does_not_notify_on_api_error():
    config = _make_config()
    client = MagicMock()
    client.stream_response.side_effect = RuntimeError("boom")
    ui = _make_ui([UserInput(text="hello"), None])
    session_store = MagicMock()

    with patch("cfi_ai.agent.notify_turn_complete") as mock_notify:
        _run_main_loop(
            client=client,
            ui=ui,
            workspace=MagicMock(),
            system_prompt="sys",
            config=config,
            messages=[],
            api_tools=[],
            cache_manager=None,
            session_store=session_store,
            cost_tracker=CostTracker(model=config.model),
        )

    mock_notify.assert_not_called()


def test_does_not_notify_on_empty_turn_continuation():
    config = _make_config()
    client = MagicMock()
    empty = _StreamResultStub(parts=[], function_calls=[])
    client.stream_response.side_effect = [empty, empty, empty]
    ui = _make_ui([UserInput(text="hello"), None], streamed_text=["", "", ""])
    session_store = MagicMock()

    with patch("cfi_ai.agent.notify_turn_complete") as mock_notify:
        _run_main_loop(
            client=client,
            ui=ui,
            workspace=MagicMock(),
            system_prompt="sys",
            config=config,
            messages=[],
            api_tools=[],
            cache_manager=None,
            session_store=session_store,
            cost_tracker=CostTracker(model=config.model),
        )

    mock_notify.assert_not_called()


def test_does_not_notify_on_handled_non_model_slash_map():
    config = _make_config()
    client = MagicMock()
    ui = _make_ui([UserInput(text="/help"), None])
    session_store = MagicMock()

    with patch(
        "cfi_ai.agent.dispatch_map",
        return_value=MapResult(handled=True),
    ), patch("cfi_ai.agent.notify_turn_complete") as mock_notify:
        _run_main_loop(
            client=client,
            ui=ui,
            workspace=MagicMock(),
            system_prompt="sys",
            config=config,
            messages=[],
            api_tools=[],
            cache_manager=None,
            session_store=session_store,
            cost_tracker=CostTracker(model=config.model),
        )

    client.stream_response.assert_not_called()
    mock_notify.assert_not_called()


def test_updated_config_from_map_applies_to_next_turn_notification():
    config = _make_config()
    updated = Config(
        project=config.project,
        location=config.location,
        model=config.model,
        max_tokens=config.max_tokens,
        grounding_enabled=config.grounding_enabled,
        notifications_popup_enabled=False,
        notifications_sound_enabled=True,
    )
    client = MagicMock()
    completed = _StreamResultStub(parts=[types.Part.from_text(text="Done.")])
    client.stream_response.side_effect = [completed, completed]
    ui = _make_ui(
        [UserInput(text="/notify"), UserInput(text="hello"), None],
        streamed_text=["Done.", "Done."],
    )
    session_store = MagicMock()

    with patch(
        "cfi_ai.agent.dispatch_map",
        return_value=MapResult(handled=True, updated_config=updated),
    ), patch("cfi_ai.agent.notify_turn_complete") as mock_notify:
        _run_main_loop(
            client=client,
            ui=ui,
            workspace=MagicMock(),
            system_prompt="sys",
            config=config,
            messages=[],
            api_tools=[],
            cache_manager=None,
            session_store=session_store,
            cost_tracker=CostTracker(model=config.model),
        )

    mock_notify.assert_called_once_with(updated)
