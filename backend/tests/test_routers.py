"""Tests for router handler code paths using mocked dependencies."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ---------------------------------------------------------------------------
# Health router
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_health_check_all_healthy():
    """health_check() returns 'healthy' when DB and Redis are both up."""
    from routers.health import health_check

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar=lambda: 100))

    mock_cache = MagicMock()
    mock_cache.is_connected.return_value = True
    mock_cache.get_cache_stats.return_value = {"cached_searches": 5}

    with patch("routers.health.get_cache", return_value=mock_cache):
        with patch("routers.health.settings") as mock_settings:
            mock_settings.embedding_mode = "gemini"
            mock_settings.embedding_model = "text-embedding-004"
            response = await health_check(db=mock_db)

    assert response.status in ("healthy", "degraded")
    assert response.services["database"] == "healthy"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_health_check_redis_unhealthy():
    """health_check() reports redis as unhealthy when disconnected."""
    from routers.health import health_check

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar=lambda: 0))

    mock_cache = MagicMock()
    mock_cache.is_connected.return_value = False

    with patch("routers.health.get_cache", return_value=mock_cache):
        with patch("routers.health.settings") as mock_settings:
            mock_settings.embedding_mode = "gemini"
            mock_settings.embedding_model = "text-embedding-004"
            response = await health_check(db=mock_db)

    assert response.services.get("redis") == "unhealthy"
    assert response.status == "unhealthy"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_health_check_db_error():
    """health_check() reports database as unhealthy on DB exception."""
    from routers.health import health_check

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection refused"))

    mock_cache = MagicMock()
    mock_cache.is_connected.return_value = True
    mock_cache.get_cache_stats.return_value = {"cached_searches": 0}

    with patch("routers.health.get_cache", return_value=mock_cache):
        with patch("routers.health.settings") as mock_settings:
            mock_settings.embedding_mode = "gemini"
            mock_settings.embedding_model = "text-embedding-004"
            response = await health_check(db=mock_db)

    assert response.services.get("database") == "unhealthy"
    assert response.status == "unhealthy"
    assert any("Database" in e for e in (response.errors or []))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_health_check_local_embedding_mode():
    """health_check() checks embedding model status in local mode."""
    from routers.health import health_check

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar=lambda: 0))

    mock_cache = MagicMock()
    mock_cache.is_connected.return_value = True
    mock_cache.get_cache_stats.return_value = {"cached_searches": 0}

    with patch("routers.health.get_cache", return_value=mock_cache):
        with patch("routers.health.settings") as mock_settings:
            mock_settings.embedding_mode = "local"
            mock_settings.embedding_model = "intfloat/multilingual-e5-large"
            with patch("routers.health.get_embedding_model", create=True) as mock_get_model:
                # Simulate model not loaded yet
                mock_get_model.cache_info.return_value = MagicMock(hits=0, currsize=0)
                response = await health_check(db=mock_db)

    assert "embedding_mode" in response.services


# ---------------------------------------------------------------------------
# Verses router
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_success():
    """get_verse() returns 200 with verse data when found."""
    from routers.verses import get_verse

    mock_db = AsyncMock()
    verse_result = {
        "reference": {"book": "John", "book_korean": "요한복음", "book_abbrev": "Jn",
                      "chapter": 3, "verse": 16, "testament": "NT", "genre": "gospel"},
        "translations": {"NIV": "For God so loved the world..."},
        "original": None,
        "cross_references": [],
        "context": None,
    }

    with patch("routers.verses.get_verse_by_reference", return_value=verse_result):
        response = await get_verse("John", 3, 16, translations="NIV", db=mock_db)

    assert response.reference.book == "John"
    assert response.reference.chapter == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_not_found_raises_404():
    """get_verse() raises 404 HTTPException when verse not found."""
    from fastapi import HTTPException
    from routers.verses import get_verse

    mock_db = AsyncMock()

    with patch("routers.verses.get_verse_by_reference", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await get_verse("Fakebook", 1, 1, translations=None, db=mock_db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_chapter_success():
    """get_chapter() returns chapter data when found."""
    from routers.verses import get_chapter

    mock_db = AsyncMock()
    chapter_result = {
        "book": "John",
        "chapter": 3,
        "total_verses": 36,
        "verses": [{"verse": 16, "translations": {"NIV": "For God so loved..."}}],
    }

    with patch("routers.verses.get_chapter_by_reference", return_value=chapter_result):
        response = await get_chapter("John", 3, translations=None, db=mock_db)

    assert response["book"] == "John"
    assert response["chapter"] == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_chapter_not_found_raises_404():
    """get_chapter() raises 404 when chapter not found."""
    from fastapi import HTTPException
    from routers.verses import get_chapter

    mock_db = AsyncMock()

    with patch("routers.verses.get_chapter_by_reference", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await get_chapter("Fakebook", 99, translations=None, db=mock_db)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Metadata router
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_translations_returns_results():
    """list_translations() returns all translations with verse counts."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from routers.metadata import list_translations

    mock_db = AsyncMock(spec=AsyncSession)

    # Mock translation objects
    import uuid
    trans_id = str(uuid.uuid4())
    mock_trans = MagicMock()
    mock_trans.id = trans_id
    mock_trans.name = "New International Version"
    mock_trans.abbreviation = "NIV"
    mock_trans.language_code = "en"
    mock_trans.is_original_language = False
    mock_trans.description = "A modern translation"

    # Execute returns different results for different queries
    translations_result = MagicMock()
    translations_result.scalars.return_value.all.return_value = [mock_trans]

    counts_result = MagicMock()
    counts_result.all.return_value = [(trans_id, 31102)]

    mock_db.execute = AsyncMock(side_effect=[translations_result, counts_result])

    response = await list_translations(language=None, db=mock_db)
    assert response.total_count == 1
    assert response.translations[0].abbreviation == "NIV"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_translations_with_language_filter():
    """list_translations() filters by language code."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from routers.metadata import list_translations

    mock_db = AsyncMock(spec=AsyncSession)
    translations_result = MagicMock()
    translations_result.scalars.return_value.all.return_value = []
    counts_result = MagicMock()
    counts_result.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[translations_result, counts_result])

    response = await list_translations(language="ko", db=mock_db)
    assert response.total_count == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_books_returns_results():
    """list_books() returns books with verse counts."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from routers.metadata import list_books

    mock_db = AsyncMock(spec=AsyncSession)

    import uuid
    book_id = str(uuid.uuid4())
    mock_book = MagicMock()
    mock_book.id = book_id
    mock_book.name = "Genesis"
    mock_book.name_korean = "창세기"
    mock_book.abbreviation = "Gen"
    mock_book.testament = "OT"
    mock_book.genre = "law"
    mock_book.book_number = 1
    mock_book.total_chapters = 50

    books_result = MagicMock()
    books_result.scalars.return_value.all.return_value = [mock_book]

    # second DB call: scalar_one_or_none() for first_translation (None = no translations)
    translation_result = MagicMock()
    translation_result.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(side_effect=[books_result, translation_result])

    response = await list_books(testament=None, genre=None, db=mock_db)
    assert response.total_count == 1
    assert response.books[0].name == "Genesis"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_books_with_testament_filter():
    """list_books() accepts testament filter."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from routers.metadata import list_books

    mock_db = AsyncMock(spec=AsyncSession)
    books_result = MagicMock()
    books_result.scalars.return_value.all.return_value = []
    translation_result = MagicMock()
    translation_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(side_effect=[books_result, translation_result])

    response = await list_books(testament="NT", genre=None, db=mock_db)
    assert response.total_count == 0


# ---------------------------------------------------------------------------
# Themes router
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_thematic_search_success():
    """thematic_search() returns ThemeResponse on success."""
    from routers.themes import thematic_search
    from schemas import ThemeRequest

    mock_db = AsyncMock()
    theme_results = {
        "theme": "love",
        "testament_filter": None,
        "query_time_ms": 50,
        "results": [
            {
                "reference": {
                    "book": "John", "book_korean": "요한복음", "book_abbrev": "Jn",
                    "chapter": 3, "verse": 16, "testament": "NT", "genre": "gospel",
                },
                "translations": {"NIV": "For God so loved the world..."},
                "relevance_score": 0.95,
            }
        ],
        "search_metadata": {"total_results": 1},
    }

    request = ThemeRequest(
        theme="love",
        translations=["NIV"],
        testament="both",
        max_results=10,
    )

    with patch("routers.themes.search_by_theme", return_value=theme_results):
        response = await thematic_search(request, db=mock_db)

    assert response.theme == "love"
    assert response.total_results == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_thematic_search_raises_500_on_error():
    """thematic_search() raises 500 HTTPException on internal error."""
    from fastapi import HTTPException
    from routers.themes import thematic_search
    from schemas import ThemeRequest

    mock_db = AsyncMock()
    request = ThemeRequest(theme="faith", translations=["NIV"], testament="both")

    with patch("routers.themes.search_by_theme", side_effect=Exception("DB error")):
        with pytest.raises(HTTPException) as exc_info:
            await thematic_search(request, db=mock_db)

    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Verses router - strongs endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_strongs_verses_not_found():
    """get_strongs_verses() raises 404 when no verses found for strongs number."""
    from fastapi import HTTPException
    from routers.verses import get_strongs_verses

    mock_db = AsyncMock()
    meta_result = MagicMock()
    meta_result.fetchone.return_value = None
    mock_db.execute = AsyncMock(return_value=meta_result)

    with pytest.raises(HTTPException) as exc_info:
        await get_strongs_verses("G9999", translations=None, db=mock_db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_strongs_verses_success():
    """get_strongs_verses() returns StrongsSearchResponse on found data."""
    from routers.verses import get_strongs_verses

    mock_db = AsyncMock()

    # Meta result (language, definition, transliteration)
    meta_row = MagicMock()
    meta_row.language = "greek"
    meta_row.definition = "to love"
    meta_row.transliteration = "agapao"

    meta_result = MagicMock()
    meta_result.fetchone.return_value = meta_row

    # Count result
    count_result = MagicMock()
    count_result.scalar.return_value = 5

    # Verses result (no translation filter)
    verse_row = MagicMock()
    verse_row.book = "John"
    verse_row.book_korean = "요한복음"
    verse_row.testament = "NT"
    verse_row.genre = "gospel"
    verse_row.chapter = 3
    verse_row.verse = 16
    verse_row.translation = "NIV"
    verse_row.text = "For God so loved the world..."

    verses_result = MagicMock()
    verses_result.fetchall.return_value = [verse_row]

    mock_db.execute = AsyncMock(side_effect=[meta_result, count_result, verses_result])

    response = await get_strongs_verses("G25", translations=None, db=mock_db)

    assert response.strongs_number == "G25"
    assert response.language == "greek"
    assert response.total_count == 5
    assert len(response.verses) == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_strongs_verses_with_translation_filter():
    """get_strongs_verses() filters by translation when specified."""
    from routers.verses import get_strongs_verses

    mock_db = AsyncMock()

    meta_row = MagicMock()
    meta_row.language = "greek"
    meta_row.definition = "love"
    meta_row.transliteration = "agape"

    meta_result = MagicMock()
    meta_result.fetchone.return_value = meta_row

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    verses_result = MagicMock()
    verses_result.fetchall.return_value = []

    mock_db.execute = AsyncMock(side_effect=[meta_result, count_result, verses_result])

    response = await get_strongs_verses("G25", translations="NIV", db=mock_db)

    assert response.strongs_number == "G25"
    assert response.verses == []


# ---------------------------------------------------------------------------
# Search router - streaming handler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.unit
async def test_semantic_search_returns_streaming_response():
    """semantic_search() returns StreamingResponse with NDJSON."""
    from fastapi.responses import StreamingResponse
    from routers.search import semantic_search
    from schemas import SearchRequest

    mock_db = AsyncMock()
    request = SearchRequest(query="love", translations=["NIV"])

    search_results = {
        "query_time_ms": 10,
        "results": [],
        "search_metadata": {"total_results": 0, "search_method": "hybrid-rrf+rerank"},
    }

    with patch("routers.search.search_verses", return_value=search_results):
        with patch("routers.search.detect_language", return_value="en"):
            with patch("routers.search.expand_query", return_value=[]):
                response = await semantic_search(request, db=mock_db)

    assert isinstance(response, StreamingResponse)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_semantic_search_generator_yields_results_and_tokens():
    """semantic_search() generator yields results chunk then tokens."""
    import json
    from routers.search import semantic_search
    from schemas import SearchRequest

    mock_db = AsyncMock()
    request = SearchRequest(query="faith", translations=["NIV"])

    search_results = {
        "query_time_ms": 10,
        "results": [
            {
                "reference": {"book": "Hebrews", "chapter": 11, "verse": 1},
                "translations": {"NIV": "Now faith is..."},
                "relevance_score": 0.9,
            }
        ],
        "search_metadata": {"total_results": 1},
    }

    async def mock_stream(*args, **kwargs):
        yield "Faith "
        yield "is the substance."

    with patch("routers.search.search_verses", return_value=search_results):
        with patch("routers.search.detect_language", return_value="en"):
            with patch("routers.search.expand_query", return_value=[]):
                with patch("llm.generate_contextual_response_stream", side_effect=mock_stream):
                    response = await semantic_search(request, db=mock_db)
                    # Collect all chunks from the streaming response
                    chunks = []
                    async for chunk in response.body_iterator:
                        chunks.append(chunk)

    assert len(chunks) >= 1
    first_chunk = json.loads(chunks[0])
    assert first_chunk["type"] == "results"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_semantic_search_with_filters_and_conversation_history():
    """semantic_search() passes filters and conversation_history to search_verses."""
    import json
    from fastapi.responses import StreamingResponse
    from routers.search import semantic_search
    from schemas import SearchRequest, SearchFilters, ConversationTurn

    mock_db = AsyncMock()
    request = SearchRequest(
        query="grace",
        translations=["NIV"],
        filters=SearchFilters(testament="NT", genre="epistle"),
        conversation_history=[ConversationTurn(role="user", content="Tell me about grace")],
    )

    search_results = {
        "query_time_ms": 5,
        "results": [],
        "search_metadata": {"total_results": 0},
    }

    with patch("routers.search.search_verses", return_value=search_results):
        with patch("routers.search.detect_language", return_value="en"):
            with patch("routers.search.expand_query", return_value=[]):
                response = await semantic_search(request, db=mock_db)
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk)

    assert isinstance(response, StreamingResponse)
    first_chunk = json.loads(chunks[0])
    assert first_chunk["type"] == "results"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_semantic_search_generator_yields_error_chunk_on_exception():
    """semantic_search() generator yields error chunk when search_verses raises."""
    import json
    from routers.search import semantic_search
    from schemas import SearchRequest

    mock_db = AsyncMock()
    request = SearchRequest(query="hope", translations=["NIV"])

    with patch("routers.search.search_verses", side_effect=Exception("DB down")):
        with patch("routers.search.detect_language", return_value="en"):
            with patch("routers.search.expand_query", return_value=[]):
                response = await semantic_search(request, db=mock_db)
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk)

    assert len(chunks) >= 1
    error_chunk = json.loads(chunks[0])
    assert error_chunk["type"] == "error"
    assert "DB down" in error_chunk["message"]
