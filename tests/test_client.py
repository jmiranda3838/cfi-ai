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
            messages=[], system="test", tools=[MM()], mode="map"
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
            messages=[], system="test", tools=[MM()], mode="normal"
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
            messages=[], system="test-system", tools=[MM()], mode="normal"
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

        tools_arg = [MM(), MM()]
        client.stream_response(
            messages=[], system="test-system", tools=tools_arg, mode="normal"
        )

        call_kwargs = mock_genai.Client.return_value.models.generate_content_stream.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_arg.system_instruction == "test-system"
        assert config_arg.tools == tools_arg
        assert config_arg.cached_content is None


def test_stream_response_fallback_on_generic_cached_call_error():
    """Non-cache-expiry errors during a cached call should invalidate the cache
    and fall back to a non-cached call. Real `Cache content N is expired` errors
    take a different path (re-raise) — see test_stream_response_reraises_on_real_cache_expired_error."""
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
        # First call (cached) fails with a generic error (not the cache-expired
        # signature), second (fallback) succeeds.
        gen_stream.side_effect = [RuntimeError("transient network blip"), mock_stream]

        cache_mgr = MM(spec=CacheManager)
        cache_mgr.get_cache_name.return_value = "cached-name"
        client.set_cache_manager(cache_mgr)

        result = client.stream_response(
            messages=[], system="test-system", tools=[MM()], mode="normal"
        )

        # Should have called generate_content_stream twice
        assert gen_stream.call_count == 2
        # Cache should have been invalidated
        cache_mgr.invalidate.assert_called_once_with("normal")
        # Second call should use inline system/tools
        second_call = gen_stream.call_args
        config_arg = second_call.kwargs.get("config") or second_call[1].get("config")
        assert config_arg.system_instruction == "test-system"


def test_stream_response_reraises_on_real_cache_expired_error():
    """Real `Cache content N is expired` errors should invalidate the cache and
    re-raise (so the agent loop can refresh both caches and retry the request)."""
    import pytest
    from unittest.mock import patch, MagicMock as MM
    from google.genai import errors as genai_errors
    from cfi_ai.client import Client, CacheManager
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    expired = genai_errors.ClientError(
        code=400,
        response_json={
            "error": {
                "code": 400,
                "status": "INVALID_ARGUMENT",
                "message": "Cache content 1 is expired.",
            }
        },
    )

    with patch("cfi_ai.client.genai") as mock_genai:
        client = Client(mock_config)
        gen_stream = mock_genai.Client.return_value.models.generate_content_stream
        # Only one entry — the call should re-raise, not fall back.
        gen_stream.side_effect = [expired]

        cache_mgr = MM(spec=CacheManager)
        cache_mgr.get_cache_name.return_value = "cached-name"
        client.set_cache_manager(cache_mgr)

        with pytest.raises(genai_errors.ClientError):
            client.stream_response(
                messages=[], system="test-system", tools=MM(), mode="normal"
            )

        # No fallback attempted — only the cached call ran.
        assert gen_stream.call_count == 1
        # Cache was invalidated before the re-raise.
        cache_mgr.invalidate.assert_called_once_with("normal")


def test_stream_result_captures_usage_metadata():
    """StreamResult should capture usage_metadata from streaming chunks."""
    from unittest.mock import MagicMock as MM
    from cfi_ai.client import StreamResult

    chunk1 = MM()
    chunk1.candidates = [MM()]
    chunk1.candidates[0].content.parts = [MM(text="hello", function_call=None)]
    chunk1.candidates[0].finish_reason = None
    chunk1.candidates[0].grounding_metadata = None
    chunk1.usage_metadata = None

    chunk2 = MM()
    chunk2.candidates = [MM()]
    chunk2.candidates[0].content.parts = [MM(text=" world", function_call=None)]
    chunk2.candidates[0].finish_reason = "STOP"
    chunk2.candidates[0].grounding_metadata = None
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


def test_coalesced_parts_merges_adjacent_text_parts():
    """Regression for issue #77 Turn 36: when Gemini streams a long answer
    as many small text deltas, the stored representation should collapse
    them into a single text part rather than preserving N fragments."""
    from cfi_ai.client import StreamResult
    from google.genai import types

    sr = StreamResult(iter([]), request_id="test")
    sr._parts = [
        types.Part(text="Hel"),
        types.Part(text="lo "),
        types.Part(text="world"),
    ]
    merged = sr.coalesced_parts
    assert len(merged) == 1
    assert merged[0].text == "Hello world"


def test_coalesced_parts_preserves_non_text_boundaries():
    """Adjacent text parts merge, but function_call and other part types
    must stay as separate parts and break the coalescing run."""
    from cfi_ai.client import StreamResult
    from google.genai import types

    sr = StreamResult(iter([]), request_id="test")
    sr._parts = [
        types.Part(text="before "),
        types.Part(text="call "),
        types.Part(function_call=types.FunctionCall(name="write_file", args={})),
        types.Part(text="after "),
        types.Part(text="call"),
    ]
    merged = sr.coalesced_parts
    assert len(merged) == 3
    assert merged[0].text == "before call "
    assert merged[1].function_call is not None
    assert merged[1].function_call.name == "write_file"
    assert merged[2].text == "after call"


def test_coalesced_parts_does_not_merge_thought_into_text():
    """A thought=True text part carries different semantics than ordinary
    model output; merging the two would lose the reasoning distinction."""
    from cfi_ai.client import StreamResult
    from google.genai import types

    sr = StreamResult(iter([]), request_id="test")
    sr._parts = [
        types.Part(text="reasoning bit", thought=True),
        types.Part(text="normal "),
        types.Part(text="answer"),
    ]
    merged = sr.coalesced_parts
    assert len(merged) == 2
    assert merged[0].thought is True
    assert merged[0].text == "reasoning bit"
    assert merged[1].text == "normal answer"
    assert not getattr(merged[1], "thought", None)


def test_coalesced_parts_empty_when_no_parts():
    from cfi_ai.client import StreamResult

    sr = StreamResult(iter([]), request_id="test")
    assert sr.coalesced_parts == []


def test_set_model_updates_model_property():
    """set_model should update the active model exposed by the .model property."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai"):
        client = Client(mock_config)
        assert client.model == "gemini-2.5-flash"

        client.set_model("gemini-3-flash-preview")
        assert client.model == "gemini-3-flash-preview"


def test_set_model_clears_cache_manager():
    """Caches are bound to the previous model, so set_model must drop the local
    cache_manager reference. Pairing a new model with a stale cache manager
    would otherwise route the next call through a cache built for the old model."""
    from unittest.mock import patch, MagicMock as MM
    from cfi_ai.client import Client, CacheManager
    from cfi_ai.config import Config

    mock_config = MM(spec=Config)
    mock_config.project = "test-project"
    mock_config.location = "us-central1"
    mock_config.model = "gemini-2.5-flash"
    mock_config.max_tokens = 8192

    with patch("cfi_ai.client.genai"):
        client = Client(mock_config)
        cache_mgr = MM(spec=CacheManager)
        client.set_cache_manager(cache_mgr)
        assert client.cache_manager is cache_mgr

        client.set_model("gemini-3-flash-preview")
        assert client.cache_manager is None
