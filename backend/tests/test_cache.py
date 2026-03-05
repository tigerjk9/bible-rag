"""Tests for cache functionality."""

import pytest
from cache import CacheClient


@pytest.mark.unit
def test_cache_client_initialization(mock_redis):
    """Test cache client initializes correctly."""
    cache = CacheClient(redis_url="redis://localhost:6379/0")
    assert cache.redis_url == "redis://localhost:6379/0"


@pytest.mark.unit
def test_generate_cache_key():
    """Test cache key generation is consistent and normalized."""
    cache = CacheClient()

    # Same inputs should produce same key
    key1 = cache.generate_cache_key("test query", ["NIV", "ESV"], {"testament": "NT"})
    key2 = cache.generate_cache_key("test query", ["ESV", "NIV"], {"testament": "NT"})
    assert key1 == key2, "Cache keys should be identical for same inputs regardless of order"

    # Case-insensitive queries
    key3 = cache.generate_cache_key("Test Query", ["NIV"], None)
    key4 = cache.generate_cache_key("test query", ["NIV"], None)
    assert key3 == key4, "Cache keys should be case-insensitive"

    # Different inputs produce different keys
    key5 = cache.generate_cache_key("different query", ["NIV"], None)
    assert key1 != key5, "Different queries should produce different keys"


@pytest.mark.unit
def test_cache_results(mock_redis):
    """Test caching search results."""
    cache = CacheClient()
    cache._client = mock_redis

    cache_key = "test_key_123"
    results = {
        "query_time_ms": 150,
        "results": [{"verse": "Genesis 1:1"}],
        "search_metadata": {"total_results": 1},
    }

    success = cache.cache_results(cache_key, results, "test query")
    assert success is True

    # Verify setex was called
    assert mock_redis.setex.called


@pytest.mark.unit
def test_get_cached_results(mock_redis):
    """Test retrieving cached results."""
    import json

    cache = CacheClient()
    cache._client = mock_redis

    cached_data = {
        "query_time_ms": 100,
        "results": [{"verse": "John 3:16"}],
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    result = cache.get_cached_results("test_key")
    assert result is not None
    assert result["query_time_ms"] == 100
    assert len(result["results"]) == 1


@pytest.mark.unit
def test_cache_embedding(mock_redis):
    """Test caching embeddings."""
    cache = CacheClient()
    cache._client = mock_redis

    text = "test text"
    embedding = [0.1, 0.2, 0.3, 0.4] * 256  # 1024 dimensions

    success = cache.cache_embedding(text, embedding)
    assert success is True
    assert mock_redis.setex.called


@pytest.mark.unit
def test_get_cached_embedding(mock_redis):
    """Test retrieving cached embeddings."""
    import json

    cache = CacheClient()
    cache._client = mock_redis

    embedding = [0.1] * 1024
    mock_redis.get.return_value = json.dumps(embedding)

    result = cache.get_cached_embedding("test text")
    assert result is not None
    assert len(result) == 1024


@pytest.mark.unit
def test_is_connected_success(mock_redis):
    """Test cache connection check when connected."""
    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.ping.return_value = True

    assert cache.is_connected() is True


@pytest.mark.unit
def test_is_connected_failure(mock_redis):
    """Test cache connection check when disconnected."""
    import redis

    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.ping.side_effect = redis.ConnectionError("Connection failed")

    assert cache.is_connected() is False


@pytest.mark.unit
def test_clear_search_cache(mock_redis):
    """Test clearing search cache."""
    cache = CacheClient()
    cache._client = mock_redis

    mock_redis.keys.side_effect = [
        ["search:key1", "search:key2"],  # search keys
        ["stats:key1", "stats:key2"],    # stats keys
    ]
    mock_redis.delete.return_value = 4

    deleted = cache.clear_search_cache()
    assert deleted == 4


@pytest.mark.unit
def test_get_cache_stats(mock_redis):
    """Test retrieving cache statistics."""
    cache = CacheClient()
    cache._client = mock_redis

    mock_redis.info.return_value = {
        "used_memory_human": "1.5M",
        "uptime_in_seconds": 3600,
    }
    mock_redis.keys.return_value = ["search:1", "search:2"]

    stats = cache.get_cache_stats()
    assert stats["connected"] is True
    assert stats["used_memory"] == "1.5M"
    assert stats["cached_searches"] == 2


# --- Error path tests ---

@pytest.mark.unit
def test_get_cached_results_connection_error_returns_none(mock_redis):
    """get_cached_results() returns None when Redis raises ConnectionError."""
    import redis

    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.get.side_effect = redis.ConnectionError("down")

    result = cache.get_cached_results("some_key")
    assert result is None


@pytest.mark.unit
def test_cache_results_connection_error_returns_false(mock_redis):
    """cache_results() returns False when Redis raises ConnectionError."""
    import redis

    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.setex.side_effect = redis.ConnectionError("down")

    result = cache.cache_results("key", {"results": []}, "query")
    assert result is False


@pytest.mark.unit
def test_get_cached_embedding_connection_error_returns_none(mock_redis):
    """get_cached_embedding() returns None on Redis error."""
    import redis

    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.get.side_effect = redis.ConnectionError("down")

    result = cache.get_cached_embedding("test text")
    assert result is None


@pytest.mark.unit
def test_cache_embedding_connection_error_returns_false(mock_redis):
    """cache_embedding() returns False on Redis error."""
    import redis

    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.setex.side_effect = redis.ConnectionError("down")

    result = cache.cache_embedding("text", [0.1] * 1024)
    assert result is False


# --- Verse cache tests ---

@pytest.mark.unit
def test_generate_verse_cache_key_consistent():
    """generate_verse_cache_key() returns same key for same inputs."""
    cache = CacheClient()
    key1 = cache.generate_verse_cache_key("Genesis", 1, 1, ["NIV", "ESV"])
    key2 = cache.generate_verse_cache_key("Genesis", 1, 1, ["ESV", "NIV"])
    assert key1 == key2


@pytest.mark.unit
def test_generate_verse_cache_key_normalizes_book():
    """generate_verse_cache_key() normalizes book name case."""
    cache = CacheClient()
    key1 = cache.generate_verse_cache_key("genesis", 1, 1)
    key2 = cache.generate_verse_cache_key("Genesis", 1, 1)
    assert key1 == key2


@pytest.mark.unit
def test_generate_verse_cache_key_varies_with_flags():
    """generate_verse_cache_key() produces different keys for different flags."""
    cache = CacheClient()
    key1 = cache.generate_verse_cache_key("John", 3, 16, include_original=True)
    key2 = cache.generate_verse_cache_key("John", 3, 16, include_original=False)
    assert key1 != key2


@pytest.mark.unit
def test_get_cached_verse_success(mock_redis):
    """get_cached_verse() returns dict when cache hit."""
    import json

    cache = CacheClient()
    cache._client = mock_redis
    verse_data = {"reference": {"book": "John", "chapter": 3, "verse": 16}}
    mock_redis.get.return_value = json.dumps(verse_data)

    result = cache.get_cached_verse("verse_key")
    assert result is not None
    assert result["reference"]["book"] == "John"


@pytest.mark.unit
def test_get_cached_verse_returns_none_on_miss(mock_redis):
    """get_cached_verse() returns None when cache miss."""
    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.get.return_value = None

    result = cache.get_cached_verse("verse_key")
    assert result is None


@pytest.mark.unit
def test_get_cached_verse_returns_none_on_error(mock_redis):
    """get_cached_verse() returns None on Redis error."""
    import redis

    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.get.side_effect = redis.ConnectionError("down")

    result = cache.get_cached_verse("verse_key")
    assert result is None


@pytest.mark.unit
def test_cache_verse_success(mock_redis):
    """cache_verse() returns True on success."""
    cache = CacheClient()
    cache._client = mock_redis

    verse_data = {"reference": {"book": "John", "chapter": 3, "verse": 16}}
    result = cache.cache_verse("verse_key", verse_data)
    assert result is True
    assert mock_redis.setex.called


@pytest.mark.unit
def test_cache_verse_returns_false_on_error(mock_redis):
    """cache_verse() returns False on Redis error."""
    import redis

    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.setex.side_effect = redis.ConnectionError("down")

    result = cache.cache_verse("verse_key", {"reference": {}})
    assert result is False


@pytest.mark.unit
def test_get_cache_stats_disconnected(mock_redis):
    """get_cache_stats() returns disconnected status on error."""
    import redis

    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.info.side_effect = redis.ConnectionError("down")

    stats = cache.get_cache_stats()
    assert stats["connected"] is False


@pytest.mark.unit
def test_clear_embedding_cache(mock_redis):
    """clear_embedding_cache() deletes embedding keys."""
    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.keys.return_value = ["embedding:abc", "embedding:def"]
    mock_redis.delete.return_value = 2

    deleted = cache.clear_embedding_cache()
    assert deleted == 2


@pytest.mark.unit
def test_clear_search_cache_empty(mock_redis):
    """clear_search_cache() returns 0 when no keys exist."""
    cache = CacheClient()
    cache._client = mock_redis
    mock_redis.keys.side_effect = [[], []]

    deleted = cache.clear_search_cache()
    assert deleted == 0
