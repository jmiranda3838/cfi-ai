"""Tests for ``cfi_ai.main`` helpers."""

from cfi_ai.config import Config
from cfi_ai.main import _apply_model_override


def test_apply_model_override_preserves_all_fields():
    """dataclasses.replace must preserve every Config field except the model.

    This gates against the old manual ``Config(...)`` rebuild which silently
    dropped newly-added fields (e.g. ``bugreport_repo``, ``bugreport_dry_run``)
    back to their defaults.
    """
    original = Config(
        project="p",
        location="global",
        model="old-model",
        max_tokens=8192,
        max_context_tokens=64_000,
        context_cache=False,
        grounding_open_browser=True,
        grounding_enabled=False,
        bugreport_enabled=True,
        bugreport_repo="org/repo",
        bugreport_dry_run=True,
    )
    new = _apply_model_override(original, "new-model")

    assert new.model == "new-model"
    # Every other field must survive unchanged.
    assert new.project == original.project
    assert new.location == original.location
    assert new.max_tokens == original.max_tokens
    assert new.max_context_tokens == original.max_context_tokens
    assert new.context_cache == original.context_cache
    assert new.grounding_open_browser == original.grounding_open_browser
    assert new.grounding_enabled == original.grounding_enabled
    assert new.bugreport_enabled == original.bugreport_enabled
    assert new.bugreport_repo == original.bugreport_repo
    assert new.bugreport_dry_run == original.bugreport_dry_run
