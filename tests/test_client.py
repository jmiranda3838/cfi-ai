"""Tests for client streaming behavior."""


def test_map_mode_raises_max_tokens():
    """Map mode should use at least 65536 max_output_tokens."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai") as mock_genai:
        client = Client(mock_config)
        mock_stream = MM()
        mock_genai.Client.return_value.models.generate_content_stream.return_value = mock_stream

        client.stream_response(
            messages=[], system="test", tools=MM(), mode="map"
        )

        call_kwargs = mock_genai.Client.return_value.models.generate_content_stream.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.max_output_tokens == 65536


def test_normal_mode_keeps_configured_tokens():
    """Normal mode should use the configured max_tokens value."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai") as mock_genai:
        client = Client(mock_config)
        mock_stream = MM()
        mock_genai.Client.return_value.models.generate_content_stream.return_value = mock_stream

        client.stream_response(
            messages=[], system="test", tools=MM(), mode="normal"
        )

        call_kwargs = mock_genai.Client.return_value.models.generate_content_stream.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.max_output_tokens == 8192


def test_stream_response_uses_cached_content():
    """When a cache exists, stream_response should use cached_content and omit system/tools."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client, CacheManager
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai") as mock_genai:
        client = Client(mock_config)
        mock_stream = MM()
        mock_genai.Client.return_value.models.generate_content_stream.return_value = mock_stream

        # Set up cache manager with a cache
        cache_mgr = MM(spec=CacheManager)
        cache_mgr.get_cache_name.return_value = "projects/p/cachedContents/abc"
        client.set_cache_manager(cache_mgr)

        client.stream_response(
            messages=[], system="test-system", tools=MM(), mode="normal"
        )

        call_kwargs = mock_genai.Client.return_value.models.generate_content_stream.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.cached_content == "projects/p/cachedContents/abc"
        assert config_arg.system_instruction is None
        assert config_arg.tools is None


def test_stream_response_fallback_on_no_cache():
    """Without a cache manager, stream_response passes system/tools inline."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai") as mock_genai:
        client = Client(mock_config)
        mock_stream = MM()
        mock_genai.Client.return_value.models.generate_content_stream.return_value = mock_stream

        tools_arg = MM()
        client.stream_response(
            messages=[], system="test-system", tools=tools_arg, mode="normal"
        )

        call_kwargs = mock_genai.Client.return_value.models.generate_content_stream.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.system_instruction == "test-system"
        assert config_arg.tools == [tools_arg]
        assert config_arg.cached_content is None


def test_stream_response_fallback_on_cache_error():
    """When cached call fails, should retry without cache and invalidate."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client, CacheManager
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai") as mock_genai:
        client = Client(mock_config)
        mock_stream = MM()
        gen_stream = mock_genai.Client.return_value.models.generate_content_stream
        # First call (cached) fails, second (fallback) succeeds
        gen_stream.side_effect = [RuntimeError("cache expired"), mock_stream]

        cache_mgr = MM(spec=CacheManager)
        cache_mgr.get_cache_name.return_value = "cached-name"
        client.set_cache_manager(cache_mgr)

        result = client.stream_response(
            messages=[], system="test-system", tools=MM(), mode="normal"
        )

        # Should have called generate_content_stream twice
        assert gen_stream.call_count == 2
        # Cache should have been invalidated
        cache_mgr.invalidate.assert_called_once_with("normal")
        # Second call should use inline system/tools
        second_call = gen_stream.call_args
        config_arg = second_call.kwargs.get("config") or second_call[1].get("config")
        assert config_arg.system_instruction == "test-system"


def test_plan_mode_uses_plan_cache_key():
    """Plan mode should use 'plan' cache key."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client, CacheManager
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai") as mock_genai:
        client = Client(mock_config)
        mock_stream = MM()
        mock_genai.Client.return_value.models.generate_content_stream.return_value = mock_stream

        cache_mgr = MM(spec=CacheManager)
        cache_mgr.get_cache_name.return_value = "plan-cache-name"
        client.set_cache_manager(cache_mgr)

        client.stream_response(
            messages=[], system="test-system", tools=MM(), mode="plan"
        )

        cache_mgr.get_cache_name.assert_called_with("plan")


def test_stream_result_captures_usage_metadata():
    """StreamResult should capture usage_metadata from streaming chunks."""
    from unittest.mock import MagicMock as MM
    from cfi_ai.client import StreamResult

    chunk1 = MM()
    chunk1.candidates = [MM()]
    chunk1.candidates[0].content.parts = [MM(text="hello", function_call=None)]
    chunk1.candidates[0].finish_reason = None
    chunk1.usage_metadata = None

    chunk2 = MM()
    chunk2.candidates = [MM()]
    chunk2.candidates[0].content.parts = [MM(text=" world", function_call=None)]
    chunk2.candidates[0].finish_reason = "STOP"
    usage = MM()
    usage.prompt_token_count = 100
    usage.cached_content_token_count = 50
    usage.candidates_token_count = 10
    usage.total_token_count = 110
    chunk2.usage_metadata = usage

    stream = iter([chunk1, chunk2])
    sr = StreamResult(stream, request_id="test")

    # Consume the stream
    text = "".join(sr.text_chunks())
    assert text == "hello world"
    assert sr.usage_metadata is usage
