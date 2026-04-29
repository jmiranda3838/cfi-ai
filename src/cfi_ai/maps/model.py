"""The /model slash map — switch the active Gemini model for this session."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cfi_ai.config import ACTIVE_MODELS, check_model_location
from cfi_ai.maps import MapResult, register_map

if TYPE_CHECKING:
    from cfi_ai.config import Config
    from cfi_ai.sessions import SessionStore
    from cfi_ai.ui import UI
    from cfi_ai.workspace import Workspace


def _compatible_models(location: str | None) -> list[str]:
    """Return the /model picker choices valid for the current Vertex location."""
    if location is None:
        return list(ACTIVE_MODELS)
    return [
        model
        for model in ACTIVE_MODELS
        if check_model_location(model, location) is None
    ]


@register_map(
    "model",
    description="Switch the active Gemini model for this session",
)
def handle_model(
    args: str | None,
    ui: UI,
    workspace: Workspace,
    session_store: SessionStore,
    config: Config | None = None,
) -> MapResult:
    current = ui.cost_tracker.model if ui.cost_tracker else None
    location = config.location if config is not None else None
    compatible_models = _compatible_models(location)
    if not compatible_models:
        if location is None:
            ui.print_info("No compatible models are available for this session.")
        else:
            ui.print_info(
                f"No compatible models are available for Vertex AI location '{location}'."
            )
        return MapResult(handled=True)
    selected = ui.prompt_model_select(compatible_models, current=current)
    if selected is None:
        ui.print_info("Model switch cancelled.")
        return MapResult(handled=True)
    if selected == current:
        ui.print_info(f"Already using {selected}.")
        return MapResult(handled=True)
    return MapResult(handled=True, switch_model=selected)
