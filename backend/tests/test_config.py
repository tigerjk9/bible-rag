"""Tests for application configuration."""

import pytest
from unittest.mock import patch


@pytest.mark.unit
def test_get_settings_returns_settings_instance():
    """Test get_settings returns a Settings object."""
    from config import get_settings, Settings

    settings = get_settings()
    assert isinstance(settings, Settings)


@pytest.mark.unit
def test_get_settings_is_cached():
    """Test get_settings returns the same object on repeated calls (lru_cache)."""
    from config import get_settings

    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


@pytest.mark.unit
def test_default_embedding_dimension():
    """Test that embedding dimension defaults to 1024."""
    from config import get_settings

    assert get_settings().embedding_dimension == 1024


@pytest.mark.unit
def test_default_embedding_mode():
    """Test that embedding_mode defaults to 'local'."""
    from config import get_settings

    assert get_settings().embedding_mode == "local"


@pytest.mark.unit
def test_default_cache_ttl():
    """Test that cache_ttl defaults to 86400 (24 hours)."""
    from config import get_settings

    assert get_settings().cache_ttl == 86400


@pytest.mark.unit
def test_default_max_results():
    """Test default max_results_default value."""
    from config import get_settings

    assert get_settings().max_results_default == 10


@pytest.mark.unit
def test_default_rrf_k():
    """Test that rrf_k defaults to 60."""
    from config import get_settings

    assert get_settings().rrf_k == 60


@pytest.mark.unit
def test_default_reranker_model():
    """Test that reranker model defaults to expected model."""
    from config import get_settings

    assert get_settings().reranker_model == "BAAI/bge-reranker-v2-m3"


@pytest.mark.unit
def test_env_override_database_url():
    """Test that DATABASE_URL env var overrides default."""
    from config import Settings

    # Create a new Settings instance (not from cache) with env override
    with patch.dict("os.environ", {"DATABASE_URL": "postgresql://custom:pass@host/db"}):
        s = Settings()
        assert s.database_url == "postgresql://custom:pass@host/db"


@pytest.mark.unit
def test_env_override_gemini_api_key():
    """Test that GEMINI_API_KEY env var is picked up."""
    from config import Settings

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-gemini-key"}):
        s = Settings()
        assert s.gemini_api_key == "test-gemini-key"


@pytest.mark.unit
def test_batching_disabled_by_default():
    """Test that batching is disabled by default."""
    from config import get_settings

    assert get_settings().enable_batching is False


@pytest.mark.unit
def test_hybrid_search_enabled_by_default():
    """Test that hybrid search is enabled by default."""
    from config import get_settings

    assert get_settings().enable_hybrid_search is True


@pytest.mark.unit
def test_reranking_enabled_by_default():
    """Test that reranking is enabled by default."""
    from config import get_settings

    assert get_settings().enable_reranking is True
