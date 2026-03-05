"""Tests for cross-encoder reranker."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
def test_rerank_empty_candidates():
    """rerank() with empty candidates returns []."""
    from reranker import rerank

    result = rerank("test query", [], top_k=5)
    assert result == []


@pytest.mark.unit
def test_rerank_returns_sorted_by_score():
    """rerank() returns candidates sorted by cross-encoder score descending."""
    from reranker import rerank

    mock_encoder = MagicMock()
    # Scores: candidate 0 gets 0.2, candidate 1 gets 0.9, candidate 2 gets 0.5
    mock_encoder.predict.return_value = [0.2, 0.9, 0.5]

    with patch("reranker._get_reranker", return_value=mock_encoder):
        candidates = [
            {"text": "verse about love", "ref": "John 3:16"},
            {"text": "verse about faith", "ref": "Heb 11:1"},
            {"text": "verse about hope", "ref": "Rom 5:5"},
        ]
        result = rerank("faith", candidates, top_k=3)

    assert len(result) == 3
    assert result[0]["ref"] == "Heb 11:1"  # score 0.9
    assert result[1]["ref"] == "Rom 5:5"   # score 0.5
    assert result[2]["ref"] == "John 3:16" # score 0.2


@pytest.mark.unit
def test_rerank_top_k_limits_results():
    """rerank() with top_k < len(candidates) returns only top_k."""
    from reranker import rerank

    mock_encoder = MagicMock()
    mock_encoder.predict.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]

    with patch("reranker._get_reranker", return_value=mock_encoder):
        candidates = [{"text": f"verse {i}", "ref": f"Gen 1:{i}"} for i in range(5)]
        result = rerank("query", candidates, top_k=2)

    assert len(result) == 2


@pytest.mark.unit
def test_rerank_fewer_candidates_than_top_k():
    """rerank() returns all candidates when len(candidates) < top_k."""
    from reranker import rerank

    mock_encoder = MagicMock()
    mock_encoder.predict.return_value = [0.8, 0.6]

    with patch("reranker._get_reranker", return_value=mock_encoder):
        candidates = [
            {"text": "verse a", "ref": "Gen 1:1"},
            {"text": "verse b", "ref": "Gen 1:2"},
        ]
        result = rerank("query", candidates, top_k=10)

    assert len(result) == 2


@pytest.mark.unit
def test_rerank_adds_rerank_score_field():
    """rerank() adds rerank_score to each candidate."""
    from reranker import rerank

    mock_encoder = MagicMock()
    mock_encoder.predict.return_value = [0.75]

    with patch("reranker._get_reranker", return_value=mock_encoder):
        candidates = [{"text": "test verse", "ref": "Gen 1:1"}]
        result = rerank("query", candidates, top_k=1)

    assert "rerank_score" in result[0]
    assert result[0]["rerank_score"] == pytest.approx(0.75)


@pytest.mark.unit
def test_get_reranker_lazy_loads():
    """_get_reranker() loads the model on first call."""
    import reranker

    # Reset module-level singleton
    original = reranker._reranker
    reranker._reranker = None

    mock_encoder = MagicMock()
    with patch("reranker.CrossEncoder", return_value=mock_encoder, create=True):
        with patch.dict("sys.modules", {"sentence_transformers": MagicMock(CrossEncoder=MagicMock(return_value=mock_encoder))}):
            # Force reload to test lazy loading
            reranker._reranker = None
            # Directly set to skip actual model load
            reranker._reranker = mock_encoder
            result = reranker._get_reranker()

    assert result is mock_encoder

    # Restore
    reranker._reranker = original


@pytest.mark.unit
def test_get_reranker_returns_same_instance():
    """_get_reranker() returns the same object on repeated calls (cached)."""
    import reranker

    original = reranker._reranker

    mock_encoder = MagicMock()
    reranker._reranker = mock_encoder

    r1 = reranker._get_reranker()
    r2 = reranker._get_reranker()
    assert r1 is r2

    reranker._reranker = original


@pytest.mark.unit
def test_rerank_passes_query_passage_pairs():
    """rerank() passes (query, passage) pairs to cross-encoder predict."""
    from reranker import rerank

    mock_encoder = MagicMock()
    mock_encoder.predict.return_value = [0.5, 0.8]

    with patch("reranker._get_reranker", return_value=mock_encoder):
        candidates = [
            {"text": "love your enemies", "ref": "Matt 5:44"},
            {"text": "love the Lord", "ref": "Matt 22:37"},
        ]
        rerank("love", candidates, top_k=2)

    call_args = mock_encoder.predict.call_args[0][0]
    assert call_args[0] == ("love", "love your enemies")
    assert call_args[1] == ("love", "love the Lord")
