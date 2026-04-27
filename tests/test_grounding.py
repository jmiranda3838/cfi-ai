"""Tests for _render_grounding_sources and _write_search_suggestions in agent.py."""

from unittest.mock import MagicMock as MM, patch

from cfi_ai.agent import (
    _render_grounding_sources,
    _write_search_suggestions,
)


def _make_chunk(uri: str, title: str | None = None) -> MM:
    chunk = MM()
    chunk.web = MM()
    chunk.web.uri = uri
    chunk.web.title = title
    return chunk


def _make_support(indices: list[int]) -> MM:
    s = MM()
    s.grounding_chunk_indices = indices
    return s


def _make_stream_result(
    chunks: list,
    supports: list | None = None,
    search_entry_point=None,
    web_search_queries: list[str] | None = None,
) -> MM:
    sr = MM()
    gm = MM()
    gm.grounding_chunks = chunks
    gm.grounding_supports = supports
    gm.search_entry_point = search_entry_point
    gm.web_search_queries = web_search_queries
    sr.grounding_metadata = gm
    return sr


def test_sparse_citations_preserve_idx_plus_one_numbering():
    """Sparse citations [0, 2] render as [1] and [3], NOT compactly renumbered to [1] [2]."""
    chunks = [_make_chunk("u0", "T0"), _make_chunk("u1", "T1"), _make_chunk("u2", "T2")]
    sr = _make_stream_result(chunks=chunks, supports=[_make_support([0, 2])])
    ui = MM()

    _render_grounding_sources(ui, sr, open_browser=False)

    ui.print_info.assert_called_once()
    msg = ui.print_info.call_args.args[0]
    assert "[1] T0 — u0" in msg
    assert "[3] T2 — u2" in msg
    assert "u1" not in msg
    assert "[2]" not in msg


def test_fallback_when_grounding_supports_empty():
    """When grounding_supports is empty, fall back to listing all chunks with idx+1 labels."""
    chunks = [_make_chunk("a"), _make_chunk("b"), _make_chunk("c")]
    sr = _make_stream_result(chunks=chunks, supports=[])
    ui = MM()

    _render_grounding_sources(ui, sr, open_browser=False)

    ui.print_info.assert_called_once()
    msg = ui.print_info.call_args.args[0]
    assert "[1] a — a" in msg
    assert "[2] b — b" in msg
    assert "[3] c — c" in msg


def test_no_grounding_metadata_does_nothing():
    """When grounding_metadata is None, the helper is a no-op."""
    sr = MM()
    sr.grounding_metadata = None
    ui = MM()

    with patch("cfi_ai.agent.webbrowser.open") as mock_open:
        _render_grounding_sources(ui, sr, open_browser=True)

    ui.print_info.assert_not_called()
    mock_open.assert_not_called()


def test_web_search_queries_render_above_sources():
    """gm.web_search_queries appears above the Sources block as auditable disclosure."""
    chunks = [_make_chunk("u0", "T0")]
    sr = _make_stream_result(
        chunks=chunks,
        supports=[_make_support([0])],
        web_search_queries=["DSM-5 latest version", "narrative therapy unique outcomes"],
    )
    ui = MM()

    _render_grounding_sources(ui, sr, open_browser=False)

    ui.print_info.assert_called_once()
    msg = ui.print_info.call_args.args[0]
    assert "Web searches:" in msg
    assert "- DSM-5 latest version" in msg
    assert "- narrative therapy unique outcomes" in msg
    assert "Sources:" in msg
    # Web searches block must come before Sources block
    assert msg.index("Web searches:") < msg.index("Sources:")


def test_open_browser_false_writes_file_but_skips_browser(tmp_path, monkeypatch):
    """With open_browser=False, the HTML is still written to disk and the file URI
    appears in the citations block, but webbrowser.open is NOT called."""
    fake_path = tmp_path / "cfi-ai-search-suggestions.html"
    monkeypatch.setattr("cfi_ai.agent._SEARCH_SUGGESTIONS_PATH", fake_path)

    sep = MM()
    sep.rendered_content = "<html>suggestions</html>"
    chunks = [_make_chunk("u0")]
    sr = _make_stream_result(
        chunks=chunks, supports=[_make_support([0])], search_entry_point=sep
    )
    ui = MM()

    with patch("cfi_ai.agent.webbrowser.open") as mock_open:
        _render_grounding_sources(ui, sr, open_browser=False)

    mock_open.assert_not_called()
    assert fake_path.exists()
    assert fake_path.read_text(encoding="utf-8") == "<html>suggestions</html>"

    msg = ui.print_info.call_args.args[0]
    assert "Suggestions UI:" in msg
    assert fake_path.as_uri() in msg


def test_open_browser_true_opens_tab(tmp_path, monkeypatch):
    """With open_browser=True, webbrowser.open is called with the file URI."""
    fake_path = tmp_path / "cfi-ai-search-suggestions.html"
    monkeypatch.setattr("cfi_ai.agent._SEARCH_SUGGESTIONS_PATH", fake_path)

    sep = MM()
    sep.rendered_content = "<html>suggestions</html>"
    chunks = [_make_chunk("u0")]
    sr = _make_stream_result(
        chunks=chunks, supports=[_make_support([0])], search_entry_point=sep
    )
    ui = MM()

    with patch("cfi_ai.agent.webbrowser.open") as mock_open:
        _render_grounding_sources(ui, sr, open_browser=True)

    mock_open.assert_called_once_with(fake_path.as_uri())
    assert fake_path.exists()
    assert fake_path.read_text(encoding="utf-8") == "<html>suggestions</html>"


def test_no_search_entry_point_no_uri_line(tmp_path, monkeypatch):
    """When search_entry_point is None, no Suggestions UI line is rendered and no
    file is written, regardless of open_browser flag."""
    fake_path = tmp_path / "cfi-ai-search-suggestions.html"
    monkeypatch.setattr("cfi_ai.agent._SEARCH_SUGGESTIONS_PATH", fake_path)

    chunks = [_make_chunk("u0", "T0")]
    sr = _make_stream_result(
        chunks=chunks, supports=[_make_support([0])], search_entry_point=None
    )
    ui = MM()

    with patch("cfi_ai.agent.webbrowser.open") as mock_open:
        _render_grounding_sources(ui, sr, open_browser=True)

    mock_open.assert_not_called()
    assert not fake_path.exists()
    msg = ui.print_info.call_args.args[0]
    assert "Suggestions UI:" not in msg
    assert "[1] T0 — u0" in msg


def test_write_search_suggestions_swallows_write_errors(monkeypatch):
    """If file write fails, _write_search_suggestions logs and returns None
    without raising — grounding shouldn't break a session."""
    gm = MM()
    gm.search_entry_point = MM()
    gm.search_entry_point.rendered_content = "<html>x</html>"

    mock_path = MM()
    mock_path.write_text.side_effect = OSError("disk full")
    monkeypatch.setattr("cfi_ai.agent._SEARCH_SUGGESTIONS_PATH", mock_path)

    # Should not raise
    result = _write_search_suggestions(gm, open_browser=True)
    assert result is None
