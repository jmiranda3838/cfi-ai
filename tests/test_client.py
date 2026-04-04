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
