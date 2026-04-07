"""Tests for CacheManager context caching lifecycle."""

from unittest.mock import MagicMock as MM, patch

import pytest

from cfi_ai.client import CacheManager

# Patch CreateCachedContentConfig to avoid pydantic validation on mock tools
_PATCH_CONFIG = patch("cfi_ai.client.types.CreateCachedContentConfig", MM)


def _make_genai_client():
    """Return a mock genai.Client with a caches attribute."""
    return MM()


def test_create_stores_name():
    genai = _make_genai_client()
    cache_obj = MM()
    cache_obj.name = "projects/p/locations/l/cachedContents/abc"
    cache_obj.usage_metadata.total_token_count = 2500
    genai.caches.create.return_value = cache_obj

    mgr = CacheManager(genai, model="gemini-3-flash-preview")
    with _PATCH_CONFIG:
        mgr.create_cache("normal", system="sys prompt", tools=MM())

    assert mgr.get_cache_name("normal") == cache_obj.name
    genai.caches.create.assert_called_once()


def test_unknown_key_returns_none():
    mgr = CacheManager(_make_genai_client(), model="m")
    assert mgr.get_cache_name("nonexistent") is None


def test_create_failure_propagates():
    genai = _make_genai_client()
    genai.caches.create.side_effect = RuntimeError("API error")

    mgr = CacheManager(genai, model="m")
    with _PATCH_CONFIG:
        with pytest.raises(RuntimeError, match="API error"):
            mgr.create_cache("normal", system="s", tools=MM())

    assert mgr.get_cache_name("normal") is None


def test_invalidate_removes_key():
    genai = _make_genai_client()
    cache_obj = MM()
    cache_obj.name = "cache-123"
    cache_obj.usage_metadata.total_token_count = 100
    genai.caches.create.return_value = cache_obj

    mgr = CacheManager(genai, model="m")
    with _PATCH_CONFIG:
        mgr.create_cache("normal", system="s", tools=MM())
    assert mgr.get_cache_name("normal") == "cache-123"

    mgr.invalidate("normal")
    assert mgr.get_cache_name("normal") is None


def test_invalidate_all_clears_all_state():
    genai = _make_genai_client()
    cache1 = MM()
    cache1.name = "cache-1"
    cache1.usage_metadata.total_token_count = 100
    cache2 = MM()
    cache2.name = "cache-2"
    cache2.usage_metadata.total_token_count = 200
    genai.caches.create.side_effect = [cache1, cache2]

    mgr = CacheManager(genai, model="m")
    with _PATCH_CONFIG:
        mgr.create_cache("normal", system="s", tools=MM())
        mgr.create_cache("plan", system="s2", tools=MM())

    mgr.invalidate_all()

    assert mgr.get_cache_name("normal") is None
    assert mgr.get_cache_name("plan") is None
    # Crucial: does NOT call server-side delete (server already expired them)
    genai.caches.delete.assert_not_called()
    # And shutdown's delete_all() must be a no-op afterward
    mgr.delete_all()
    genai.caches.delete.assert_not_called()


def test_delete_all_calls_delete():
    genai = _make_genai_client()
    cache1 = MM()
    cache1.name = "cache-1"
    cache1.usage_metadata.total_token_count = 100
    cache2 = MM()
    cache2.name = "cache-2"
    cache2.usage_metadata.total_token_count = 200
    genai.caches.create.side_effect = [cache1, cache2]

    mgr = CacheManager(genai, model="m")
    with _PATCH_CONFIG:
        mgr.create_cache("normal", system="s", tools=MM())
        mgr.create_cache("plan", system="s2", tools=MM())

    mgr.delete_all()

    assert genai.caches.delete.call_count == 2
    genai.caches.delete.assert_any_call(name="cache-1")
    genai.caches.delete.assert_any_call(name="cache-2")
    assert mgr.get_cache_name("normal") is None
    assert mgr.get_cache_name("plan") is None


def test_delete_all_handles_errors():
    genai = _make_genai_client()
    cache1 = MM()
    cache1.name = "cache-1"
    cache1.usage_metadata.total_token_count = 100
    cache2 = MM()
    cache2.name = "cache-2"
    cache2.usage_metadata.total_token_count = 200
    genai.caches.create.side_effect = [cache1, cache2]

    mgr = CacheManager(genai, model="m")
    with _PATCH_CONFIG:
        mgr.create_cache("normal", system="s", tools=MM())
        mgr.create_cache("plan", system="s2", tools=MM())

    # First delete fails, second should still be called
    genai.caches.delete.side_effect = [RuntimeError("fail"), None]

    mgr.delete_all()  # should not raise
    assert genai.caches.delete.call_count == 2


def test_reset_clears_and_updates_client():
    old_genai = _make_genai_client()
    cache_obj = MM()
    cache_obj.name = "old-cache"
    cache_obj.usage_metadata.total_token_count = 100
    old_genai.caches.create.return_value = cache_obj

    mgr = CacheManager(old_genai, model="m")
    with _PATCH_CONFIG:
        mgr.create_cache("normal", system="s", tools=MM())

    new_genai = _make_genai_client()
    mgr.reset(new_genai)

    # Old cache should have been deleted
    old_genai.caches.delete.assert_called_once_with(name="old-cache")
    # State should be cleared
    assert mgr.get_cache_name("normal") is None
    # New cache creation should use new client
    new_cache = MM()
    new_cache.name = "new-cache"
    new_cache.usage_metadata.total_token_count = 100
    new_genai.caches.create.return_value = new_cache
    with _PATCH_CONFIG:
        mgr.create_cache("normal", system="s", tools=MM())
    new_genai.caches.create.assert_called_once()
    assert mgr.get_cache_name("normal") == "new-cache"
