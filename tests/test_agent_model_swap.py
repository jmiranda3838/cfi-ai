"""Tests for the /model swap branch and cleanup lifecycle in agent.py."""

from unittest.mock import MagicMock as MM, patch

from cfi_ai.agent import _run_main_loop, run_agent_loop
from cfi_ai.client import CacheManager
from cfi_ai.cost_tracker import CostTracker
from cfi_ai.maps import MapResult
from cfi_ai.ui import UserInput


def _drive_one_swap(
    *,
    switch_model: str,
    config: MM,
    mock_cache_manager: MM | None,
    cost_tracker: CostTracker,
) -> tuple[MM, MM]:
    """Drive a single /model invocation through _run_main_loop and return
    (mock_client, mock_ui) for assertions. The map dispatch is stubbed to
    return MapResult(switch_model=...) directly so the test isolates the
    swap-branch logic in agent.py from the map handler (covered separately
    in test_model_map.py)."""
    mock_client = MM()
    mock_client.model = cost_tracker.model

    mock_ui = MM()
    mock_ui.get_input.side_effect = [UserInput(text="/model"), None]

    mock_workspace = MM()

    with patch(
        "cfi_ai.agent.dispatch_map",
        return_value=MapResult(handled=True, switch_model=switch_model),
    ):
        _run_main_loop(
            client=mock_client,
            ui=mock_ui,
            workspace=mock_workspace,
            system_prompt="sys",
            config=config,
            messages=[],
            api_tools=MM(),
            cache_manager=mock_cache_manager,
            session_store=MM(),
            cost_tracker=cost_tracker,
        )

    # The /model branch hits `continue`, so stream_response must NOT fire.
    mock_client.stream_response.assert_not_called()
    return mock_client, mock_ui


def test_model_swap_with_cache_enabled_rebuilds_caches():
    """Happy path: tear down old caches, swap model, mutate cost_tracker in
    place, and rebuild a fresh cache manager bound to the new model."""
    config = MM()
    config.context_cache = True
    config.location = "global"

    mock_cache_manager = MM(spec=CacheManager)
    cost_tracker = CostTracker(model="gemini-3-flash-preview")

    new_cache_manager = MM(spec=CacheManager)
    with patch(
        "cfi_ai.agent.CacheManager", return_value=new_cache_manager
    ) as cache_ctor, patch(
        "cfi_ai.agent._create_session_caches"
    ) as create_caches, patch(
        "cfi_ai.agent.check_model_location", return_value=None
    ):
        mock_client, _ = _drive_one_swap(
            switch_model="gemini-3.1-pro-preview",
            config=config,
            mock_cache_manager=mock_cache_manager,
            cost_tracker=cost_tracker,
        )

    mock_cache_manager.delete_all.assert_called_once_with()
    mock_client.set_model.assert_called_once_with("gemini-3.1-pro-preview")
    assert cost_tracker.model == "gemini-3.1-pro-preview"
    cache_ctor.assert_called_once_with(
        mock_client.genai_client, "gemini-3.1-pro-preview"
    )
    create_caches.assert_called_once()
    # new manager attached to the client so the outer try/finally cleans up.
    mock_client.set_cache_manager.assert_called_once_with(new_cache_manager)


def test_model_swap_with_cache_disabled_skips_rebuild():
    """When context caching is off, teardown + swap still happen but no new
    CacheManager is constructed and the local reference is rebound to None."""
    config = MM()
    config.context_cache = False
    config.location = "global"

    mock_cache_manager = MM(spec=CacheManager)
    cost_tracker = CostTracker(model="gemini-3-flash-preview")

    with patch("cfi_ai.agent.CacheManager") as cache_ctor, patch(
        "cfi_ai.agent._create_session_caches"
    ) as create_caches, patch(
        "cfi_ai.agent.check_model_location", return_value=None
    ):
        mock_client, _ = _drive_one_swap(
            switch_model="gemini-3.1-pro-preview",
            config=config,
            mock_cache_manager=mock_cache_manager,
            cost_tracker=cost_tracker,
        )

    mock_cache_manager.delete_all.assert_called_once_with()
    mock_client.set_model.assert_called_once_with("gemini-3.1-pro-preview")
    assert cost_tracker.model == "gemini-3.1-pro-preview"
    cache_ctor.assert_not_called()
    create_caches.assert_not_called()
    mock_client.set_cache_manager.assert_not_called()


def test_model_swap_rejected_when_location_incompatible():
    """check_model_location returning an error message must abort the swap
    BEFORE any teardown — caches stay live and the client stays on the old
    model."""
    config = MM()
    config.context_cache = True
    config.location = "us-central1"

    mock_cache_manager = MM(spec=CacheManager)
    cost_tracker = CostTracker(model="gemini-3-flash-preview")

    with patch(
        "cfi_ai.agent.check_model_location",
        return_value="Model 'X' requires Vertex AI location 'global'.",
    ), patch("cfi_ai.agent.CacheManager") as cache_ctor, patch(
        "cfi_ai.agent._create_session_caches"
    ) as create_caches:
        mock_client, mock_ui = _drive_one_swap(
            switch_model="gemini-3.1-pro-preview",
            config=config,
            mock_cache_manager=mock_cache_manager,
            cost_tracker=cost_tracker,
        )

    mock_ui.print_error.assert_called_once()
    err_text = mock_ui.print_error.call_args[0][0]
    assert "global" in err_text
    assert "gemini-3.1-pro-preview" in err_text

    mock_cache_manager.delete_all.assert_not_called()
    mock_client.set_model.assert_not_called()
    assert cost_tracker.model == "gemini-3-flash-preview"
    cache_ctor.assert_not_called()
    create_caches.assert_not_called()


class _ClientStub:
    def __init__(self) -> None:
        self.genai_client = MM()
        self.cache_manager = None

    def set_cache_manager(self, manager: CacheManager) -> None:
        self.cache_manager = manager


def test_run_agent_loop_cleans_up_live_cache_manager_after_reauth_and_swap():
    """Shutdown must delete the live cache manager, not the stale pre-reauth one."""
    client = _ClientStub()
    ui = MM()
    workspace = MM()

    config = MM()
    config.model = "gemini-3-flash-preview"
    config.max_context_tokens = 128_000
    config.grounding_enabled = False
    config.context_cache = True

    initial_cache_manager = MM(spec=CacheManager)
    swapped_cache_manager = MM(spec=CacheManager)

    def _simulate_main_loop(
        live_client,
        _ui,
        _workspace,
        _system_prompt,
        _config,
        _messages,
        _api_tools,
        cache_manager,
        _session_store,
        _cost_tracker,
    ) -> None:
        assert live_client is client
        assert cache_manager is initial_cache_manager
        # Simulate the reauth -> /model path rebinding the client's cache manager.
        live_client.set_cache_manager(swapped_cache_manager)

    with patch("cfi_ai.agent.SessionStore") as session_store_cls, patch(
        "cfi_ai.agent.tools.get_api_tools", return_value=[]
    ), patch(
        "cfi_ai.agent.CacheManager", return_value=initial_cache_manager
    ), patch(
        "cfi_ai.agent._create_session_caches"
    ), patch(
        "cfi_ai.agent._run_main_loop", side_effect=_simulate_main_loop
    ), patch(
        "cfi_ai.maps.get_map_descriptions", return_value={}
    ):
        session_store_cls.prune_expired.return_value = None
        session_store_cls.return_value = MM()
        run_agent_loop(client, ui, workspace, "sys", config)

    swapped_cache_manager.delete_all.assert_called_once_with()
    initial_cache_manager.delete_all.assert_not_called()
