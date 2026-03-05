"""Tests for Pydantic request/response schemas."""

import pytest
from datetime import datetime
from uuid import UUID
from pydantic import ValidationError


# --- SearchFilters ---

@pytest.mark.unit
def test_search_filters_valid_testament_ot():
    from schemas import SearchFilters
    f = SearchFilters(testament="OT")
    assert f.testament == "OT"


@pytest.mark.unit
def test_search_filters_valid_testament_nt():
    from schemas import SearchFilters
    f = SearchFilters(testament="NT")
    assert f.testament == "NT"


@pytest.mark.unit
def test_search_filters_valid_testament_both():
    from schemas import SearchFilters
    f = SearchFilters(testament="both")
    assert f.testament == "both"


@pytest.mark.unit
def test_search_filters_invalid_testament():
    from schemas import SearchFilters
    with pytest.raises(ValidationError):
        SearchFilters(testament="INVALID")


@pytest.mark.unit
def test_search_filters_optional_fields_default_none():
    from schemas import SearchFilters
    f = SearchFilters()
    assert f.testament is None
    assert f.genre is None
    assert f.books is None


@pytest.mark.unit
def test_search_filters_books_list():
    from schemas import SearchFilters
    f = SearchFilters(books=["Gen", "Exo", "Matt"])
    assert f.books == ["Gen", "Exo", "Matt"]


# --- ConversationTurn ---

@pytest.mark.unit
def test_conversation_turn_valid_user():
    from schemas import ConversationTurn
    turn = ConversationTurn(role="user", content="Hello")
    assert turn.role == "user"


@pytest.mark.unit
def test_conversation_turn_valid_assistant():
    from schemas import ConversationTurn
    turn = ConversationTurn(role="assistant", content="Hi there")
    assert turn.role == "assistant"


@pytest.mark.unit
def test_conversation_turn_invalid_role():
    from schemas import ConversationTurn
    with pytest.raises(ValidationError):
        ConversationTurn(role="system", content="You are a bot")


@pytest.mark.unit
def test_conversation_turn_content_too_long():
    from schemas import ConversationTurn
    with pytest.raises(ValidationError):
        ConversationTurn(role="user", content="x" * 2001)


# --- SearchRequest ---

@pytest.mark.unit
def test_search_request_valid_minimal():
    from schemas import SearchRequest
    req = SearchRequest(query="love", translations=["NIV"])
    assert req.query == "love"
    assert req.translations == ["NIV"]
    assert req.max_results == 10  # default
    assert req.include_original is False  # default


@pytest.mark.unit
def test_search_request_empty_query_rejected():
    from schemas import SearchRequest
    with pytest.raises(ValidationError):
        SearchRequest(query="", translations=["NIV"])


@pytest.mark.unit
def test_search_request_query_too_long():
    from schemas import SearchRequest
    with pytest.raises(ValidationError):
        SearchRequest(query="x" * 501, translations=["NIV"])


@pytest.mark.unit
def test_search_request_empty_translations_rejected():
    from schemas import SearchRequest
    with pytest.raises(ValidationError):
        SearchRequest(query="love", translations=[])


@pytest.mark.unit
def test_search_request_max_results_out_of_range():
    from schemas import SearchRequest
    with pytest.raises(ValidationError):
        SearchRequest(query="love", translations=["NIV"], max_results=0)
    with pytest.raises(ValidationError):
        SearchRequest(query="love", translations=["NIV"], max_results=101)


@pytest.mark.unit
def test_search_request_invalid_search_type():
    from schemas import SearchRequest
    with pytest.raises(ValidationError):
        SearchRequest(query="love", translations=["NIV"], search_type="fuzzy")


@pytest.mark.unit
def test_search_request_valid_search_types():
    from schemas import SearchRequest
    r1 = SearchRequest(query="love", translations=["NIV"], search_type="semantic")
    r2 = SearchRequest(query="love", translations=["NIV"], search_type="keyword")
    assert r1.search_type == "semantic"
    assert r2.search_type == "keyword"


@pytest.mark.unit
def test_search_request_with_filters():
    from schemas import SearchRequest, SearchFilters
    req = SearchRequest(
        query="covenant",
        translations=["NIV"],
        filters=SearchFilters(testament="OT", genre="law"),
    )
    assert req.filters.testament == "OT"
    assert req.filters.genre == "law"


@pytest.mark.unit
def test_search_request_with_conversation_history():
    from schemas import SearchRequest, ConversationTurn
    req = SearchRequest(
        query="faith",
        translations=["NIV"],
        conversation_history=[
            ConversationTurn(role="user", content="What is faith?"),
            ConversationTurn(role="assistant", content="Faith is..."),
        ],
    )
    assert len(req.conversation_history) == 2


# --- ThemeRequest ---

@pytest.mark.unit
def test_theme_request_valid():
    from schemas import ThemeRequest
    req = ThemeRequest(theme="love", translations=["NIV"])
    assert req.theme == "love"
    assert req.testament == "both"  # default


@pytest.mark.unit
def test_theme_request_empty_theme_rejected():
    from schemas import ThemeRequest
    with pytest.raises(ValidationError):
        ThemeRequest(theme="", translations=["NIV"])


@pytest.mark.unit
def test_theme_request_invalid_testament():
    from schemas import ThemeRequest
    with pytest.raises(ValidationError):
        ThemeRequest(theme="love", translations=["NIV"], testament="INVALID")


@pytest.mark.unit
def test_theme_request_empty_translations_rejected():
    from schemas import ThemeRequest
    with pytest.raises(ValidationError):
        ThemeRequest(theme="love", translations=[])


# --- Response Models ---

@pytest.mark.unit
def test_verse_reference_minimal():
    from schemas import VerseReference
    ref = VerseReference(book="Genesis", chapter=1, verse=1)
    assert ref.book == "Genesis"
    assert ref.book_korean is None
    assert ref.testament is None


@pytest.mark.unit
def test_search_result_serialization():
    from schemas import SearchResult, VerseReference
    result = SearchResult(
        reference=VerseReference(book="John", chapter=3, verse=16),
        translations={"NIV": "For God so loved the world..."},
        relevance_score=0.95,
    )
    d = result.model_dump()
    assert d["relevance_score"] == 0.95
    assert d["translations"]["NIV"] == "For God so loved the world..."
    assert d["cross_references"] is None
    assert d["original"] is None


@pytest.mark.unit
def test_health_response_serialization():
    from schemas import HealthResponse
    resp = HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        services={"database": "healthy", "redis": "healthy"},
    )
    assert resp.status == "healthy"
    assert resp.version == "1.0.0"  # default


@pytest.mark.unit
def test_search_metadata_defaults():
    from schemas import SearchMetadata
    meta = SearchMetadata(total_results=5)
    assert meta.total_results == 5
    assert meta.cached is False
    assert meta.error is None
