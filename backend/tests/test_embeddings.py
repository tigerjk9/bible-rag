"""Tests for embedding module."""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock


@pytest.mark.unit
def test_embed_query_routes_to_local_mode():
    """embed_query() uses local model when embedding_mode=local."""
    mock_embedding = np.array([0.1] * 1024)

    with patch("embeddings.settings") as mock_settings:
        mock_settings.embedding_mode = "local"
        with patch("embeddings.embed_query_local", return_value=mock_embedding) as mock_local:
            from embeddings import embed_query
            result = embed_query("test query")

    mock_local.assert_called_once_with("test query")
    np.testing.assert_array_equal(result, mock_embedding)


@pytest.mark.unit
def test_embed_query_routes_to_gemini_mode():
    """embed_query() uses Gemini when embedding_mode=gemini."""
    mock_embedding = np.array([0.2] * 1024)

    with patch("embeddings.settings") as mock_settings:
        mock_settings.embedding_mode = "gemini"
        with patch("embeddings.embed_query_gemini", return_value=mock_embedding) as mock_gemini:
            from embeddings import embed_query
            result = embed_query("test query", api_key="test-key")

    mock_gemini.assert_called_once_with("test query", "test-key")
    np.testing.assert_array_equal(result, mock_embedding)


@pytest.mark.unit
def test_embed_query_gemini_requires_api_key():
    """embed_query() raises ValueError when gemini mode but no api_key."""
    with patch("embeddings.settings") as mock_settings:
        mock_settings.embedding_mode = "gemini"
        from embeddings import embed_query
        with pytest.raises(ValueError, match="Gemini API key required"):
            embed_query("test query", api_key=None)


@pytest.mark.unit
def test_embed_query_local_returns_correct_shape():
    """embed_query_local() returns a 1024-dim array."""
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([0.1] * 1024)

    with patch("embeddings._get_local_model", return_value=mock_model):
        from embeddings import embed_query_local
        result = embed_query_local("test query")

    assert result.shape == (1024,)


@pytest.mark.unit
def test_embed_query_local_uses_query_prefix():
    """embed_query_local() prepends 'query: ' to the text."""
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([0.1] * 1024)

    with patch("embeddings._get_local_model", return_value=mock_model):
        from embeddings import embed_query_local
        embed_query_local("love and peace")

    call_args = mock_model.encode.call_args[0][0]
    assert call_args == "query: love and peace"


@pytest.mark.unit
def test_embed_query_gemini_returns_correct_shape():
    """embed_query_gemini() returns a 1024-dim array from API response."""
    import sys

    mock_genai = MagicMock()
    mock_genai.embed_content.return_value = {"embedding": [0.3] * 1024}

    # embed_query_gemini does `import google.generativeai as genai` inside its body,
    # so we patch at sys.modules level to intercept that import.
    with patch.dict(sys.modules, {
        "google": MagicMock(generativeai=mock_genai),
        "google.generativeai": mock_genai,
    }):
        import embeddings as emb_mod
        result = emb_mod.embed_query_gemini("test query", "test-api-key")

    assert isinstance(result, np.ndarray)
    assert result.shape == (1024,)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_embed_query_async_returns_same_as_sync():
    """embed_query_async() returns same result as embed_query."""
    mock_embedding = np.array([0.5] * 1024)

    with patch("embeddings.embed_query", return_value=mock_embedding):
        from embeddings import embed_query_async
        result = await embed_query_async("test query")

    np.testing.assert_array_equal(result, mock_embedding)


@pytest.mark.unit
def test_get_local_model_lazy_loads():
    """_get_local_model() loads and caches the model."""
    import embeddings

    original = embeddings._local_model
    embeddings._local_model = None

    mock_model = MagicMock()
    mock_st = MagicMock()
    mock_st.SentenceTransformer.return_value = mock_model

    with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
        result = embeddings._get_local_model()

    assert result is mock_model
    assert embeddings._local_model is mock_model

    # Restore
    embeddings._local_model = original


@pytest.mark.unit
def test_get_local_model_returns_same_instance():
    """_get_local_model() returns the same cached instance on repeat calls."""
    import embeddings

    original = embeddings._local_model
    mock_model = MagicMock()
    embeddings._local_model = mock_model

    r1 = embeddings._get_local_model()
    r2 = embeddings._get_local_model()
    assert r1 is r2

    embeddings._local_model = original


@pytest.mark.unit
def test_embed_texts_returns_batch_array():
    """embed_texts() returns array of shape (n, 1024) for n texts."""
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([[0.1] * 1024, [0.2] * 1024])

    with patch("embeddings._get_local_model", return_value=mock_model):
        with patch("embeddings.settings") as mock_settings:
            mock_settings.embedding_mode = "local"
            from embeddings import embed_texts
            result = embed_texts(["text a", "text b"])

    assert result.shape[0] == 2
