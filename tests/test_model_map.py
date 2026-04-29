"""Tests for the /model slash map handler."""

from unittest.mock import MagicMock, patch

from cfi_ai.config import ACTIVE_MODELS
from cfi_ai.maps.model import handle_model
from cfi_ai.workspace import Workspace


def _make_ui(current_model: str | None) -> MagicMock:
    ui = MagicMock()
    if current_model is None:
        ui.cost_tracker = None
    else:
        ui.cost_tracker = MagicMock()
        ui.cost_tracker.model = current_model
    return ui


def _make_config(location: str) -> MagicMock:
    config = MagicMock()
    config.location = location
    return config


def test_handle_model_cancelled(tmp_path):
    """Esc out of the picker -> handled=True with no swap requested."""
    ui = _make_ui("gemini-3-flash-preview")
    ui.prompt_model_select.return_value = None
    ws = Workspace(str(tmp_path))
    store = MagicMock()
    config = _make_config("global")

    result = handle_model(None, ui, ws, store, config)

    assert result.handled is True
    assert result.switch_model is None
    assert result.error is None
    ui.prompt_model_select.assert_called_once_with(
        list(ACTIVE_MODELS), current="gemini-3-flash-preview"
    )
    ui.print_info.assert_called_once()
    assert "cancel" in ui.print_info.call_args[0][0].lower()


def test_handle_model_no_op_when_selected_equals_current(tmp_path):
    """Picking the already-active model -> handled=True, no swap."""
    ui = _make_ui("gemini-3-flash-preview")
    ui.prompt_model_select.return_value = "gemini-3-flash-preview"
    ws = Workspace(str(tmp_path))
    store = MagicMock()
    config = _make_config("global")

    result = handle_model(None, ui, ws, store, config)

    assert result.handled is True
    assert result.switch_model is None
    ui.print_info.assert_called_once()
    assert "already" in ui.print_info.call_args[0][0].lower()


def test_handle_model_returns_switch_model_on_real_swap(tmp_path):
    """Picking a different model -> MapResult.switch_model carries the new model
    so the agent loop's swap branch can act on it."""
    ui = _make_ui("gemini-3-flash-preview")
    ui.prompt_model_select.return_value = "gemini-3.1-pro-preview"
    ws = Workspace(str(tmp_path))
    store = MagicMock()
    config = _make_config("global")

    result = handle_model(None, ui, ws, store, config)

    assert result.handled is True
    assert result.switch_model == "gemini-3.1-pro-preview"
    assert result.error is None


def test_handle_model_with_no_cost_tracker_passes_current_none(tmp_path):
    """Defensive: if the UI has no cost_tracker yet, current must be None."""
    ui = _make_ui(None)
    ui.prompt_model_select.return_value = None
    ws = Workspace(str(tmp_path))
    store = MagicMock()
    config = _make_config("global")

    handle_model(None, ui, ws, store, config)

    ui.prompt_model_select.assert_called_once_with(list(ACTIVE_MODELS), current=None)


def test_handle_model_filters_incompatible_models_for_regional_sessions(tmp_path):
    """Regional sessions should only see choices that pass location checks."""
    ui = _make_ui("gemini-2.5-flash")
    ui.prompt_model_select.return_value = None
    ws = Workspace(str(tmp_path))
    store = MagicMock()
    config = _make_config("us-central1")

    compatible_model = ACTIVE_MODELS[0]

    def _check(model: str, location: str) -> str | None:
        assert location == "us-central1"
        return None if model == compatible_model else "requires global"

    with patch("cfi_ai.maps.model.check_model_location", side_effect=_check) as mock_check:
        handle_model(None, ui, ws, store, config)

    ui.prompt_model_select.assert_called_once_with([compatible_model], current="gemini-2.5-flash")
    assert mock_check.call_count == len(ACTIVE_MODELS)


def test_handle_model_short_circuits_when_no_models_fit_location(tmp_path):
    """If nothing is switchable from this Vertex location, don't show a dead-end picker."""
    ui = _make_ui("gemini-2.5-flash")
    ws = Workspace(str(tmp_path))
    store = MagicMock()
    config = _make_config("us-central1")

    with patch(
        "cfi_ai.maps.model.check_model_location",
        return_value="Model requires Vertex AI location 'global'.",
    ):
        result = handle_model(None, ui, ws, store, config)

    assert result.handled is True
    assert result.switch_model is None
    ui.prompt_model_select.assert_not_called()
    ui.print_info.assert_called_once()
    msg = ui.print_info.call_args[0][0]
    assert "compatible models" in msg
    assert "us-central1" in msg


def test_model_map_is_registered():
    """Importing maps must register /model so the dispatcher can find it."""
    from cfi_ai.maps import MAPS, get_map_descriptions

    assert "model" in MAPS
    assert "model" in get_map_descriptions()
