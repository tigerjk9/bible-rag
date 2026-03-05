"""Tests for search functionality."""

import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np

# Capture the real fulltext_search_verses BEFORE any conftest fixture patches it.
# conftest starts patches during fixture setup (after module collection), so
# this module-level import always gets the unpatched original.
from search import fulltext_search_verses as _real_fulltext_fn

@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_verses_no_translations(test_db):
    """Test search with invalid translations returns empty results."""
    from search import search_verses

    with patch("search.embed_query_async") as mock_embed:
        mock_embed.return_value = np.array([0.1] * 1024)

        results = await search_verses(
            db=test_db,
            query="test query",
            translations=["INVALID"],
            max_results=10,
            use_cache=False,
        )

        assert results["search_metadata"]["total_results"] == 0
        assert "error" in results["search_metadata"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_cross_references_empty(test_db, sample_verse):
    """Test getting cross-references for verse with none."""
    from search import get_cross_references

    refs = await get_cross_references(test_db, uuid.UUID(sample_verse.id))
    assert refs == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_cross_references_with_data(test_db, sample_verse, sample_nt_book, sample_translation):
    """Test getting cross-references when they exist."""
    from tests.conftest import Verse, CrossReference
    from search import get_cross_references

    # Create a related verse - commit it first before referencing in cross_ref
    related_verse = Verse(
        id=str(uuid.uuid4()),
        translation_id=sample_translation.id,
        book_id=sample_nt_book.id,
        chapter=5,
        verse=44,
        text="But I say to you, Love your enemies.",
    )
    test_db.add(related_verse)
    await test_db.flush()  # Ensure verse exists before creating cross-reference
    # flush works in async session too if autocommit is false

    # Create cross-reference
    cross_ref = CrossReference(
        id=str(uuid.uuid4()),
        verse_id=sample_verse.id,
        related_verse_id=related_verse.id,
        relationship_type="parallel",
        confidence=0.95,
    )
    test_db.add(cross_ref)
    await test_db.commit()
    await test_db.refresh(related_verse)

    refs = await get_cross_references(test_db, uuid.UUID(sample_verse.id), limit=10)
    assert len(refs) == 1
    assert refs[0]["relationship"] == "parallel"
    assert refs[0]["book"] == "Matthew"
    assert refs[0]["chapter"] == 5
    assert refs[0]["verse"] == 44
    assert refs[0]["confidence"] == 0.95


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_original_words_none(test_db, sample_verse):
    """Test getting original words when none exist."""
    from search import get_original_words

    result = await get_original_words(test_db, uuid.UUID(sample_verse.id))
    assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_original_words_with_data(test_db, sample_verse):
    """Test getting original words when they exist."""
    from tests.conftest import OriginalWord
    from search import get_original_words

    # Add some Greek words
    words_data = [
        {
            "word": "ἐν",
            "transliteration": "en",
            "strongs": "G1722",
            "definition": "in, on, among",
            "word_order": 1,
        },
        {
            "word": "ἀρχῇ",
            "transliteration": "archē",
            "strongs": "G746",
            "definition": "beginning, origin",
            "word_order": 2,
        },
    ]

    for word_data in words_data:
        word = OriginalWord(
            id=str(uuid.uuid4()),
            verse_id=sample_verse.id,
            word=word_data["word"],
            language="greek",
            strongs_number=word_data["strongs"],
            transliteration=word_data["transliteration"],
            definition=word_data["definition"],
            morphology=None,
            word_order=word_data["word_order"],
        )
        test_db.add(word)
    await test_db.commit()

    result = await get_original_words(test_db, uuid.UUID(sample_verse.id))
    assert result is not None
    assert result["language"] == "greek"
    assert len(result["words"]) == 2
    assert result["words"][0]["strongs"] == "G1722"
    assert result["words"][1]["word"] == "ἀρχῇ"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_by_reference_book_not_found(test_db):
    """Test getting verse with invalid book name."""
    from search import get_verse_by_reference

    result = await get_verse_by_reference(
        db=test_db,
        book="NonexistentBook",
        chapter=1,
        verse=1,
    )
    assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_by_reference_success(test_db, sample_book, sample_translation, sample_verse):
    """Test getting verse by reference successfully."""
    from search import get_verse_by_reference

    # Ensure data is committed before searching
    await test_db.commit()

    result = await get_verse_by_reference(
        db=test_db,
        book="Genesis",
        chapter=1,
        verse=1,
        translations=["TEV"],
        include_original=False,
        include_cross_refs=False,  # Don't include cross-refs to avoid extra queries
    )

    assert result is not None
    assert result["reference"]["book"] == "Genesis"
    assert result["reference"]["chapter"] == 1
    assert result["reference"]["verse"] == 1
    assert "TEV" in result["translations"]
    assert "In the beginning" in result["translations"]["TEV"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_by_reference_korean_name(test_db, sample_book, sample_translation, sample_verse):
    """Test getting verse using Korean book name."""
    from search import get_verse_by_reference

    # Ensure data is committed
    await test_db.commit()

    result = await get_verse_by_reference(
        db=test_db,
        book="창세기",
        chapter=1,
        verse=1,
        include_original=False,
        include_cross_refs=False,
    )

    assert result is not None
    assert result["reference"]["book"] == "Genesis"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_by_reference_abbreviation(test_db, sample_book, sample_translation, sample_verse):
    """Test getting verse using book abbreviation."""
    from search import get_verse_by_reference

    # Ensure data is committed
    await test_db.commit()

    result = await get_verse_by_reference(
        db=test_db,
        book="Gen",
        chapter=1,
        verse=1,
        include_original=False,
        include_cross_refs=False,
    )

    assert result is not None
    assert result["reference"]["book"] == "Genesis"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_context(test_db, sample_book, sample_translation):
    """Test getting verse context (previous/next verses)."""
    from tests.conftest import Verse
    from search import get_verse_context

    # Create multiple verses
    verses = []
    for i in range(1, 4):
        verse = Verse(
            id=str(uuid.uuid4()),
            translation_id=sample_translation.id,
            book_id=sample_book.id,
            chapter=1,
            verse=i,
            text=f"This is verse {i}.",
        )
        test_db.add(verse)
        verses.append(verse)
    await test_db.commit()

    # Refresh verses to ensure they're properly loaded
    for v in verses:
        await test_db.refresh(v)

    # Get context for verse 2 - convert book_id string to UUID
    context = await get_verse_context(test_db, uuid.UUID(sample_book.id), 1, 2)

    assert context["previous"] is not None
    assert context["previous"]["verse"] == 1
    prev_texts = context["previous"]["translations"]
    assert any("This is verse 1" in t for t in prev_texts.values())

    assert context["next"] is not None
    assert context["next"]["verse"] == 3
    next_texts = context["next"]["translations"]
    assert any("This is verse 3" in t for t in next_texts.values())


@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_by_theme(test_db, sample_translation):
    """Test thematic search."""
    from search import search_by_theme

    # We need to mock await search_verses (which is an async function)
    # Patching async functions requires returning a coroutine or AsyncMock
    # Or we can patch search_verses directly.
    # Since search_by_theme calls await search_verses, the mock must be awaitable.
    
    with patch("search.search_verses") as mock_search:
        # Configure mock to be awaitable
        async def mock_async_search(**kwargs):
            return {
                "query_time_ms": 100,
                "results": [],
                "search_metadata": {"total_results": 0},
            }
        
        mock_search.side_effect = mock_async_search

        results = await search_by_theme(
            db=test_db,
            theme="love",
            translations=["TEV"],
            testament="NT",
            max_results=20,
        )

        assert "theme" in results
        assert results["theme"] == "love"
        assert "testament_filter" in results
        assert results["testament_filter"] == "NT"

        # Verify search_verses was called
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["filters"]["testament"] == "NT"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_by_theme_both_testaments(test_db, sample_translation):
    """Test thematic search with 'both' testament filter."""
    from search import search_by_theme

    with patch("search.search_verses") as mock_search:
        async def mock_async_search(**kwargs):
            return {
                "query_time_ms": 100,
                "results": [],
                "search_metadata": {"total_results": 0},
            }
        mock_search.side_effect = mock_async_search

        results = await search_by_theme(
            db=test_db,
            theme="faith",
            translations=["TEV"],
            testament="both",
            max_results=20,
        )

        # 'both' should result in no testament filter
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["filters"] == {}


# --- rrf_merge tests ---

@pytest.mark.unit
def test_rrf_merge_single_list_preserves_order():
    """rrf_merge() with single ranked list preserves descending order."""
    from search import rrf_merge

    ranked = [("Gen 1:1", 0.9), ("John 3:16", 0.8), ("Ps 23:1", 0.7)]
    result = rrf_merge([(ranked, 1.0)])

    # First result should have highest rrf score
    keys = [r[0] for r in result]
    assert keys[0] == "Gen 1:1"
    assert keys[1] == "John 3:16"
    assert keys[2] == "Ps 23:1"


@pytest.mark.unit
def test_rrf_merge_empty_input():
    """rrf_merge() with empty ranked lists returns []."""
    from search import rrf_merge

    result = rrf_merge([([], 1.0)])
    assert result == []


@pytest.mark.unit
def test_rrf_merge_two_lists_overlap():
    """rrf_merge() with overlapping results combines their scores."""
    from search import rrf_merge

    list1 = [("John 3:16", 0.9), ("Gen 1:1", 0.7)]
    list2 = [("Gen 1:1", 0.95), ("Ps 23:1", 0.6)]

    result = rrf_merge([(list1, 1.0), (list2, 1.0)])

    result_keys = {r[0] for r in result}
    assert "John 3:16" in result_keys
    assert "Gen 1:1" in result_keys
    assert "Ps 23:1" in result_keys

    # Gen 1:1 appears in both lists so should rank higher than items only in one
    gen_score = next(s for k, s in result if k == "Gen 1:1")
    ps_score = next(s for k, s in result if k == "Ps 23:1")
    john_score = next(s for k, s in result if k == "John 3:16")

    # Gen 1:1 is rank 2 in list1 and rank 1 in list2
    # Ps 23:1 is rank 2 in list2 only
    # So Gen 1:1 score > Ps 23:1 score
    assert gen_score > ps_score


@pytest.mark.unit
def test_rrf_merge_weighted():
    """rrf_merge() applies weight to each list's contribution."""
    from search import rrf_merge

    list1 = [("A", 0.9)]  # weight 2.0
    list2 = [("B", 0.9)]  # weight 1.0

    result = rrf_merge([(list1, 2.0), (list2, 1.0)])

    # A (weight 2.0) should score higher than B (weight 1.0) at same rank
    a_score = next(s for k, s in result if k == "A")
    b_score = next(s for k, s in result if k == "B")
    assert a_score > b_score


@pytest.mark.unit
def test_rrf_merge_returns_sorted_descending():
    """rrf_merge() output is sorted by score descending."""
    from search import rrf_merge

    ranked = [("A", 0.9), ("B", 0.7), ("C", 0.5)]
    result = rrf_merge([(ranked, 1.0)])

    scores = [s for _, s in result]
    assert scores == sorted(scores, reverse=True)


# --- get_chapter_by_reference tests ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_chapter_by_reference_invalid_book(test_db):
    """get_chapter_by_reference() returns None for unknown book."""
    from search import get_chapter_by_reference

    result = await get_chapter_by_reference(test_db, "NonexistentBook", 1)
    assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_chapter_by_reference_success(test_db, sample_book, sample_translation):
    """get_chapter_by_reference() returns chapter data for valid input."""
    from tests.conftest import Verse
    from search import get_chapter_by_reference

    # Add several verses
    for i in range(1, 4):
        v = Verse(
            id=str(uuid.uuid4()),
            translation_id=sample_translation.id,
            book_id=sample_book.id,
            chapter=1,
            verse=i,
            text=f"Verse text {i}",
        )
        test_db.add(v)
    await test_db.commit()

    result = await get_chapter_by_reference(test_db, "Genesis", 1, translations=["TEV"])

    assert result is not None
    assert result["reference"]["book"] == "Genesis"
    assert result["reference"]["chapter"] == 1
    assert len(result["verses"]) == 3
    assert result["verses"][0]["verse"] == 1
    assert "TEV" in result["verses"][0]["translations"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_chapter_by_reference_no_verses(test_db, sample_book, sample_translation):
    """get_chapter_by_reference() returns None when chapter has no verses."""
    from search import get_chapter_by_reference

    # No verses committed yet for chapter 99
    result = await get_chapter_by_reference(test_db, "Genesis", 99, translations=["TEV"])
    assert result is None


# --- search_verses early paths (no DB required) ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_verses_returns_cached_result():
    """search_verses() returns cached result without hitting DB."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import search_verses

    mock_db = AsyncMock()
    cached_response = {
        "query_time_ms": 10,
        "results": [{"reference": {"book": "John"}}],
        "search_metadata": {"total_results": 1, "cached": False},
    }

    mock_cache = MagicMock()
    mock_cache.generate_cache_key.return_value = "key123"
    mock_cache.get_cached_results.return_value = cached_response

    with patch("search.get_cache", return_value=mock_cache):
        result = await search_verses(mock_db, "love", ["NIV"], use_cache=True)

    assert result["results"][0]["reference"]["book"] == "John"
    assert result.get("cached") is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_verses_no_translations_found():
    """search_verses() returns empty when no valid translations in DB."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import search_verses

    mock_db = AsyncMock()

    # DB returns empty translations list
    translations_result = MagicMock()
    translations_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=translations_result)

    mock_cache = MagicMock()
    mock_cache.generate_cache_key.return_value = "key123"
    mock_cache.get_cached_results.return_value = None

    with patch("search.get_cache", return_value=mock_cache):
        result = await search_verses(mock_db, "love", ["NOTREAL"], use_cache=True)

    assert result["results"] == []
    assert "error" in result["search_metadata"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_verses_fulltext_fallback_when_no_embeddings():
    """search_verses() uses fulltext when _has_embeddings is False."""
    from unittest.mock import AsyncMock, MagicMock, patch
    import search as search_module
    from search import search_verses

    mock_db = AsyncMock()

    # Translation found in DB
    mock_trans = MagicMock()
    mock_trans.id = "trans-uuid"
    mock_trans.abbreviation = "NIV"
    translations_result = MagicMock()
    translations_result.scalars.return_value.all.return_value = [mock_trans]
    mock_db.execute = AsyncMock(return_value=translations_result)

    mock_cache = MagicMock()
    mock_cache.generate_cache_key.return_value = "key123"
    mock_cache.get_cached_results.return_value = None

    fulltext_response = {
        "query_time_ms": 5,
        "results": [],
        "search_metadata": {"total_results": 0, "search_method": "full-text"},
    }

    original_val = search_module._has_embeddings
    try:
        search_module._has_embeddings = False
        with patch("search.get_cache", return_value=mock_cache):
            with patch("search.fulltext_search_verses", return_value=fulltext_response):
                result = await search_verses(mock_db, "grace", ["NIV"], use_cache=False)
    finally:
        search_module._has_embeddings = original_val

    assert result["search_metadata"]["search_method"] == "full-text"


# --- _fill_verse_gaps ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_fill_verse_gaps_returns_unchanged_if_less_than_two_results():
    """_fill_verse_gaps() returns results unchanged when fewer than 2 results."""
    from unittest.mock import AsyncMock
    from search import _fill_verse_gaps

    mock_db = AsyncMock()
    result = await _fill_verse_gaps(mock_db, [], [], {})
    assert result == []

    single = [{"reference": {"book": "John", "chapter": 3, "verse": 16}}]
    result2 = await _fill_verse_gaps(mock_db, single, [], {})
    assert result2 == single


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fill_verse_gaps_no_gap_returns_unchanged():
    """_fill_verse_gaps() returns unchanged when no gaps of exactly 1 exist."""
    from unittest.mock import AsyncMock
    from search import _fill_verse_gaps

    mock_db = AsyncMock()
    results = [
        {
            "reference": {"book": "John", "chapter": 3, "verse": 1},
            "relevance_score": 0.9,
        },
        {
            "reference": {"book": "John", "chapter": 3, "verse": 4},  # gap of 3 → not filled
            "relevance_score": 0.8,
        },
    ]

    filled = await _fill_verse_gaps(mock_db, results, [], {})
    assert len(filled) == 2  # unchanged


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fill_verse_gaps_fills_single_verse_gap():
    """_fill_verse_gaps() fetches and inserts the missing verse."""
    from unittest.mock import AsyncMock, MagicMock
    from search import _fill_verse_gaps
    import uuid

    trans_id = str(uuid.uuid4())
    translation_map = {trans_id: "NIV"}

    mock_verse = MagicMock()
    mock_verse.id = str(uuid.uuid4())
    mock_verse.text = "Gap verse text."
    mock_verse.chapter = 3
    mock_verse.verse = 2
    mock_verse.translation_id = trans_id

    mock_book = MagicMock()
    mock_book.name = "John"
    mock_book.name_korean = "요한복음"
    mock_book.abbreviation = "Jn"
    mock_book.testament = "NT"
    mock_book.genre = "gospel"

    mock_translation = MagicMock()
    mock_translation.abbreviation = "NIV"

    gap_rows = [(mock_verse, mock_translation, mock_book)]

    mock_db = AsyncMock()
    gap_result = MagicMock()
    gap_result.all.return_value = gap_rows
    mock_db.execute = AsyncMock(return_value=gap_result)

    results = [
        {
            "reference": {"book": "John", "chapter": 3, "verse": 1},
            "relevance_score": 0.9,
            "verse_id": str(uuid.uuid4()),
        },
        {
            "reference": {"book": "John", "chapter": 3, "verse": 3},
            "relevance_score": 0.8,
            "verse_id": str(uuid.uuid4()),
        },
    ]

    filled = await _fill_verse_gaps(mock_db, results, [trans_id], translation_map)
    # The gap at verse 2 should now be filled
    assert len(filled) == 3
    verses_in_filled = [r["reference"]["verse"] for r in filled]
    assert 2 in verses_in_filled


# --- fulltext_search_verses ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_fulltext_search_verses_empty_results():
    """fulltext_search_verses() returns empty results when DB returns no rows."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import fulltext_search_verses
    import time

    mock_db = AsyncMock()
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=empty_result)

    mock_cache = MagicMock()
    mock_cache.cache_results.return_value = True

    with patch("search.get_cache", return_value=mock_cache):
        result = await fulltext_search_verses(
            db=mock_db,
            query="love",
            translation_ids=["trans-id"],
            translation_map={"trans-id": "NIV"},
            max_results=10,
            filters=None,
            include_original=False,
            include_cross_refs=False,
            use_cache=True,
            cache_key="test_key",
            start_time=time.time(),
        )

    assert result["results"] == []
    assert result["search_metadata"]["search_method"] == "full-text"
    assert result["search_metadata"]["total_results"] == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fulltext_search_verses_with_filters():
    """fulltext_search_verses() applies testament/genre filters without error."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import fulltext_search_verses
    import time

    mock_db = AsyncMock()
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=empty_result)

    mock_cache = MagicMock()

    with patch("search.get_cache", return_value=mock_cache):
        result = await fulltext_search_verses(
            db=mock_db,
            query="grace",
            translation_ids=["trans-id"],
            translation_map={"trans-id": "NIV"},
            max_results=5,
            filters={"testament": "NT", "genre": "epistle"},
            include_original=False,
            include_cross_refs=False,
            use_cache=False,
            cache_key="key",
            start_time=time.time(),
        )

    assert result["results"] == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fulltext_search_verses_with_matching_rows():
    """fulltext_search_verses() groups rows by verse reference."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import fulltext_search_verses
    import time
    import uuid

    book_id = str(uuid.uuid4())
    trans_id = str(uuid.uuid4())

    mock_row = MagicMock()
    mock_row.book_id = book_id
    mock_row.chapter = 3
    mock_row.verse = 16
    mock_row.book_name = "John"
    mock_row.book_name_korean = "요한복음"
    mock_row.book_abbrev = "Jn"
    mock_row.testament = "NT"
    mock_row.genre = "gospel"
    mock_row.rank = 0.85
    mock_row.verse_id = str(uuid.uuid4())
    mock_row.translation_id = trans_id
    mock_row.text = "For God so loved the world..."

    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.fetchall.return_value = [mock_row]
    mock_db.execute = AsyncMock(return_value=result_mock)

    mock_cache = MagicMock()

    import search as _search_mod
    # Get the real function even if conftest patched the module attribute
    _real_fulltext = _search_mod.fulltext_search_verses.__wrapped__ if hasattr(
        _search_mod.fulltext_search_verses, '__wrapped__') else None

    with patch("search.get_cache", return_value=mock_cache):
        with patch("search.get_cross_references", new=AsyncMock(return_value=[])):
            result = await _real_fulltext_fn(
                db=mock_db,
                query="love",
                translation_ids=[trans_id],
                translation_map={trans_id: "NIV"},
                max_results=10,
                filters=None,
                include_original=False,
                include_cross_refs=False,
                use_cache=False,
                cache_key="key",
                start_time=time.time(),
            )

    assert len(result["results"]) == 1
    assert result["results"][0]["reference"]["book"] == "John"


# --- get_verse_by_reference with include_original and include_cross_refs ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_by_reference_with_cross_refs_and_original(test_db, sample_book, sample_translation, sample_verse):
    """get_verse_by_reference() fetches cross-refs and original data when requested."""
    from search import get_verse_by_reference
    from unittest.mock import patch, AsyncMock

    with patch("search.get_cross_references", new=AsyncMock(return_value=[])):
        with patch("search.get_original_words", new=AsyncMock(return_value=None)):
            with patch("search.get_verse_context", new=AsyncMock(return_value=None)):
                result = await get_verse_by_reference(
                    db=test_db,
                    book="Genesis",
                    chapter=1,
                    verse=1,
                    include_original=True,
                    include_cross_refs=True,
                )

    assert result is not None
    assert "cross_references" in result
    assert "original" in result


# --- get_chapter_by_reference with include_original ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_chapter_by_reference_with_include_original(test_db, sample_book, sample_translation, sample_verse):
    """get_chapter_by_reference() fetches original language when include_original=True."""
    from search import get_chapter_by_reference

    with patch("search.get_original_words", new=AsyncMock(return_value={"words": []})):
        result = await get_chapter_by_reference(
            db=test_db,
            book="Genesis",
            chapter=1,
            translations=["TEV"],
            include_original=True,
        )

    assert result is not None
    assert "verses" in result
    # Each verse should have original field
    if result["verses"]:
        assert "original" in result["verses"][0]


# --- search_verses embedding failure path ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_verses_embedding_fails_returns_error():
    """search_verses() returns error dict when embedding fails."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import search_verses
    import search as search_module

    mock_db = AsyncMock()

    mock_trans = MagicMock()
    mock_trans.id = "trans-uuid"
    mock_trans.abbreviation = "NIV"
    translations_result = MagicMock()
    translations_result.scalars.return_value.all.return_value = [mock_trans]
    mock_db.execute = AsyncMock(return_value=translations_result)

    mock_cache = MagicMock()
    mock_cache.generate_cache_key.return_value = "key"
    mock_cache.get_cached_results.return_value = None

    original_val = search_module._has_embeddings
    try:
        search_module._has_embeddings = True  # Force semantic path

        with patch("search.get_cache", return_value=mock_cache):
            with patch("search.embed_query_async", side_effect=Exception("embedding model down")):
                result = await search_verses(mock_db, "faith", ["NIV"], use_cache=False)
    finally:
        search_module._has_embeddings = original_val

    # Should return an error result
    assert "results" in result


# --- fulltext inner branches with books filter ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_fulltext_search_verses_with_books_filter():
    """fulltext_search_verses() applies books filter in SQL."""
    from unittest.mock import AsyncMock, MagicMock, patch
    import time

    mock_db = AsyncMock()
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=empty_result)

    mock_cache = MagicMock()

    with patch("search.get_cache", return_value=mock_cache):
        result = await _real_fulltext_fn(
            db=mock_db,
            query="love",
            translation_ids=["trans-id"],
            translation_map={"trans-id": "NIV"},
            max_results=10,
            filters={"books": ["Gen", "Jn"]},  # books filter
            include_original=False,
            include_cross_refs=False,
            use_cache=False,
            cache_key="key",
            start_time=time.time(),
        )

    assert result["results"] == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fulltext_search_verses_with_enrichments_and_caching():
    """fulltext_search_verses() calls cross-refs/original and caches when results exist."""
    from unittest.mock import AsyncMock, MagicMock, patch
    import time
    import uuid

    book_id = str(uuid.uuid4())
    trans_id = str(uuid.uuid4())
    verse_id = str(uuid.uuid4())

    mock_row = MagicMock()
    mock_row.book_id = book_id
    mock_row.chapter = 3
    mock_row.verse = 16
    mock_row.book_name = "John"
    mock_row.book_name_korean = "요한복음"
    mock_row.book_abbrev = "Jn"
    mock_row.testament = "NT"
    mock_row.genre = "gospel"
    mock_row.rank = 0.85
    mock_row.verse_id = verse_id
    mock_row.translation_id = trans_id
    mock_row.text = "For God so loved the world..."

    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.fetchall.return_value = [mock_row]
    mock_db.execute = AsyncMock(return_value=result_mock)

    mock_cache = MagicMock()

    with patch("cache.get_cache", return_value=mock_cache):
        with patch("search.get_cross_references", new=AsyncMock(return_value=[{"book": "Romans"}])):
            with patch("search.get_original_words", new=AsyncMock(return_value={"language": "greek"})):
                result = await _real_fulltext_fn(
                    db=mock_db,
                    query="love",
                    translation_ids=[trans_id],
                    translation_map={trans_id: "NIV"},
                    max_results=10,
                    filters=None,
                    include_original=True,
                    include_cross_refs=True,
                    use_cache=True,
                    cache_key="test_cache_key",
                    start_time=time.time(),
                )

    assert len(result["results"]) == 1
    assert "cross_references" in result["results"][0]
    assert "original" in result["results"][0]
    mock_cache.cache_results.assert_called_once()


# --- get_verse_by_reference cache hit and verse not found ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_by_reference_cache_hit():
    """get_verse_by_reference() returns cached verse without DB query."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import get_verse_by_reference

    mock_db = AsyncMock()
    cached_verse = {"reference": {"book": "John", "chapter": 3, "verse": 16}}

    mock_cache = MagicMock()
    mock_cache.generate_verse_cache_key.return_value = "verse_key"
    mock_cache.get_cached_verse.return_value = cached_verse

    with patch("search.get_cache", return_value=mock_cache):
        result = await get_verse_by_reference(
            db=mock_db,
            book="John",
            chapter=3,
            verse=16,
            use_cache=True,
        )

    assert result == cached_verse
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_verse_by_reference_verse_not_found(test_db, sample_book):
    """get_verse_by_reference() returns None when verse not in database."""
    from search import get_verse_by_reference

    # Book exists (sample_book) but chapter 999 does not
    await test_db.commit()
    result = await get_verse_by_reference(
        db=test_db,
        book="Genesis",
        chapter=999,
        verse=1,
        use_cache=False,
    )

    assert result is None


# --- _vector_search internal function ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_vector_search_returns_empty_when_no_rows():
    """_vector_search() returns [] when DB returns no matching rows."""
    from unittest.mock import AsyncMock, MagicMock
    from search import _vector_search
    import numpy as np

    mock_db = AsyncMock()
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []
    # First execute: SET ivfflat.probes; Second execute: actual query
    mock_db.execute = AsyncMock(side_effect=[MagicMock(), empty_result])

    query_embedding = np.array([0.1] * 1024)
    result = await _vector_search(mock_db, query_embedding, ["trans-id"], None, 0.5, 10)

    assert result == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_vector_search_returns_results():
    """_vector_search() parses rows into (ref_key, similarity, row_data) tuples."""
    from unittest.mock import AsyncMock, MagicMock
    from search import _vector_search
    import numpy as np
    import uuid

    book_id = str(uuid.uuid4())
    verse_id = str(uuid.uuid4())
    trans_id = str(uuid.uuid4())

    mock_row = MagicMock()
    mock_row.book_id = book_id
    mock_row.chapter = 3
    mock_row.verse = 16
    mock_row.verse_id = verse_id
    mock_row.text = "For God so loved the world"
    mock_row.translation_id = trans_id
    mock_row.similarity = 0.92
    mock_row.book_name = "John"
    mock_row.book_name_korean = "요한복음"
    mock_row.book_abbrev = "Jn"
    mock_row.testament = "NT"
    mock_row.genre = "gospel"

    result_mock = MagicMock()
    result_mock.fetchall.return_value = [mock_row]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[MagicMock(), result_mock])

    query_embedding = np.array([0.1] * 1024)
    result = await _vector_search(mock_db, query_embedding, [trans_id], None, 0.5, 10)

    assert len(result) == 1
    ref_key, similarity, row_data = result[0]
    assert ref_key == f"{book_id}:3:16"
    assert similarity == pytest.approx(0.92)
    assert row_data["book_name"] == "John"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_vector_search_with_filters():
    """_vector_search() applies testament, genre, and books filters."""
    from unittest.mock import AsyncMock, MagicMock
    from search import _vector_search
    import numpy as np

    mock_db = AsyncMock()
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []
    mock_db.execute = AsyncMock(side_effect=[MagicMock(), empty_result])

    query_embedding = np.array([0.1] * 1024)
    filters = {"testament": "NT", "genre": "gospel", "books": ["Jn", "Matt"]}
    result = await _vector_search(mock_db, query_embedding, ["trans-id"], filters, 0.5, 10)

    assert result == []
    # Verify execute was called twice (SET + actual query)
    assert mock_db.execute.call_count == 2


# --- _fulltext_search (internal pipeline function) ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_fulltext_search_internal_empty_results():
    """_fulltext_search() returns [] when DB returns no rows."""
    from unittest.mock import AsyncMock, MagicMock
    from search import _fulltext_search

    mock_db = AsyncMock()
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=empty_result)

    result = await _fulltext_search(mock_db, "love", ["trans-id"], None, 10)
    assert result == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fulltext_search_internal_with_results():
    """_fulltext_search() parses rows into (ref_key, rank, row_data) tuples."""
    from unittest.mock import AsyncMock, MagicMock
    from search import _fulltext_search
    import uuid

    book_id = str(uuid.uuid4())
    verse_id = str(uuid.uuid4())
    trans_id = str(uuid.uuid4())

    mock_row = MagicMock()
    mock_row.book_id = book_id
    mock_row.chapter = 5
    mock_row.verse = 44
    mock_row.verse_id = verse_id
    mock_row.text = "Love your enemies"
    mock_row.translation_id = trans_id
    mock_row.rank = 0.75
    mock_row.book_name = "Matthew"
    mock_row.book_name_korean = "마태복음"
    mock_row.book_abbrev = "Matt"
    mock_row.testament = "NT"
    mock_row.genre = "gospel"

    result_mock = MagicMock()
    result_mock.fetchall.return_value = [mock_row]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await _fulltext_search(mock_db, "love enemies", [trans_id], None, 10)

    assert len(result) == 1
    ref_key, rank, row_data = result[0]
    assert ref_key == f"{book_id}:5:44"
    assert rank == pytest.approx(0.75)
    assert row_data["book_name"] == "Matthew"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fulltext_search_internal_with_filters():
    """_fulltext_search() builds SQL with testament/genre/books filters."""
    from unittest.mock import AsyncMock, MagicMock
    from search import _fulltext_search

    mock_db = AsyncMock()
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []
    mock_db.execute = AsyncMock(return_value=empty_result)

    filters = {"testament": "OT", "genre": "law", "books": ["Gen", "Exo"]}
    result = await _fulltext_search(mock_db, "creation", ["trans-id"], filters, 5)

    assert result == []
    mock_db.execute.assert_called_once()


# --- search_verses full semantic pipeline ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_verses_semantic_pipeline_with_results():
    """search_verses() runs full hybrid retrieval pipeline when embeddings present."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import search_verses
    import search as search_module
    import numpy as np
    import uuid

    mock_db = AsyncMock()

    trans_id = str(uuid.uuid4())
    mock_trans = MagicMock()
    mock_trans.id = trans_id
    mock_trans.abbreviation = "NIV"

    translations_result = MagicMock()
    translations_result.scalars.return_value.all.return_value = [mock_trans]

    # Extra translations fetch for each verse
    mock_verse_obj = MagicMock()
    mock_verse_obj.text = "For God so loved..."
    mock_verse_obj.translation_id = trans_id
    mock_trans_obj = MagicMock()
    mock_trans_obj.abbreviation = "NIV"
    extra_result = MagicMock()
    extra_result.all.return_value = [(mock_verse_obj, mock_trans_obj)]

    mock_db.execute = AsyncMock(side_effect=[translations_result, extra_result])

    book_id = "book-123"
    ref_key = f"{book_id}:3:16"
    verse_id = str(uuid.uuid4())
    row_data = {
        "verse_id": verse_id,
        "book_id": book_id,
        "chapter": 3,
        "verse": 16,
        "text": "For God so loved the world",
        "translation_id": trans_id,
        "similarity": 0.9,
        "book_name": "John",
        "book_name_korean": "요한복음",
        "book_abbrev": "Jn",
        "testament": "NT",
        "genre": "gospel",
    }
    vector_results = [(ref_key, 0.9, row_data)]

    mock_cache = MagicMock()
    mock_cache.generate_cache_key.return_value = "key"
    mock_cache.get_cached_results.return_value = None

    original_val = search_module._has_embeddings
    try:
        search_module._has_embeddings = True

        with patch("search.get_cache", return_value=mock_cache):
            with patch("search.embed_query_async", return_value=np.array([0.1] * 1024)):
                with patch("search._vector_search", return_value=vector_results):
                    with patch("search._fulltext_search", return_value=[]):
                        with patch("search._fill_verse_gaps", return_value=[{
                            "reference": {"book": "John", "chapter": 3, "verse": 16},
                            "translations": {"NIV": "For God so loved..."},
                            "relevance_score": 0.9,
                            "verse_id": verse_id,
                        }]):
                            with patch("search.get_cross_references", new=AsyncMock(return_value=[])):
                                result = await search_verses(
                                    mock_db,
                                    "love",
                                    ["NIV"],
                                    max_results=10,
                                    use_cache=False,
                                    include_cross_refs=True,
                                )
    finally:
        search_module._has_embeddings = original_val

    assert "results" in result
    assert result["search_metadata"]["search_method"] in ("semantic", "semantic+rerank", "hybrid-rrf", "hybrid-rrf+rerank")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_verses_with_expanded_queries():
    """search_verses() handles expanded queries via asyncio.gather."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import search_verses
    import search as search_module
    import numpy as np
    import uuid

    mock_db = AsyncMock()

    trans_id = str(uuid.uuid4())
    mock_trans = MagicMock()
    mock_trans.id = trans_id
    mock_trans.abbreviation = "NIV"

    translations_result = MagicMock()
    translations_result.scalars.return_value.all.return_value = [mock_trans]
    extra_result = MagicMock()
    extra_result.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[translations_result, extra_result])

    mock_cache = MagicMock()
    mock_cache.generate_cache_key.return_value = "key"
    mock_cache.get_cached_results.return_value = None

    original_val = search_module._has_embeddings
    try:
        search_module._has_embeddings = True

        # embed_query_async returns embeddings for [main_query, expanded1, expanded2]
        embeddings = [np.array([0.1] * 1024), np.array([0.2] * 1024), np.array([0.3] * 1024)]

        with patch("search.get_cache", return_value=mock_cache):
            with patch("search.embed_query_async", side_effect=embeddings):
                with patch("search._vector_search", return_value=[]):
                    with patch("search._fulltext_search", return_value=[]):
                        result = await search_verses(
                            mock_db,
                            "love",
                            ["NIV"],
                            max_results=5,
                            use_cache=False,
                            expanded_queries=["agape love", "christian love"],
                        )
    finally:
        search_module._has_embeddings = original_val

    assert "results" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_search_verses_caches_results():
    """search_verses() calls cache.cache_results when use_cache=True."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from search import search_verses
    import search as search_module
    import numpy as np

    mock_db = AsyncMock()

    mock_trans = MagicMock()
    mock_trans.id = "trans-id"
    mock_trans.abbreviation = "NIV"
    translations_result = MagicMock()
    translations_result.scalars.return_value.all.return_value = [mock_trans]
    mock_db.execute = AsyncMock(return_value=translations_result)

    mock_cache = MagicMock()
    mock_cache.generate_cache_key.return_value = "key"
    mock_cache.get_cached_results.return_value = None

    original_val = search_module._has_embeddings
    try:
        search_module._has_embeddings = True

        with patch("search.get_cache", return_value=mock_cache):
            with patch("search.embed_query_async", return_value=np.array([0.1] * 1024)):
                with patch("search._vector_search", return_value=[]):
                    with patch("search._fulltext_search", return_value=[]):
                        await search_verses(mock_db, "faith", ["NIV"], use_cache=True)
    finally:
        search_module._has_embeddings = original_val

    mock_cache.cache_results.assert_called_once()


# --- _fill_verse_gaps edge cases ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_fill_verse_gaps_single_verse_per_chapter_group():
    """_fill_verse_gaps() skips chapter groups with only one verse (no gap possible)."""
    from unittest.mock import AsyncMock
    from search import _fill_verse_gaps

    mock_db = AsyncMock()

    # Two results in different chapters — no gap possible within same chapter
    results = [
        {
            "reference": {"book": "John", "chapter": 3, "verse": 16},
            "relevance_score": 0.9,
            "verse_id": "v1",
        },
        {
            "reference": {"book": "John", "chapter": 4, "verse": 18},
            "relevance_score": 0.8,
            "verse_id": "v2",
        },
    ]

    filled = await _fill_verse_gaps(mock_db, results, [], {})
    # No gaps found — result unchanged
    assert len(filled) == 2
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fill_verse_gaps_skips_already_present_verse():
    """_fill_verse_gaps() skips gap if that verse is already in result set."""
    from unittest.mock import AsyncMock
    from search import _fill_verse_gaps

    mock_db = AsyncMock()

    # Verse 2 is already in results, so the gap between 1 and 3 should be skipped
    results = [
        {"reference": {"book": "John", "chapter": 3, "verse": 1}, "relevance_score": 0.9, "verse_id": "v1"},
        {"reference": {"book": "John", "chapter": 3, "verse": 2}, "relevance_score": 0.85, "verse_id": "v2"},
        {"reference": {"book": "John", "chapter": 3, "verse": 3}, "relevance_score": 0.8, "verse_id": "v3"},
    ]

    filled = await _fill_verse_gaps(mock_db, results, [], {})
    # No new verses inserted — already complete sequence
    assert len(filled) == 3
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fill_verse_gaps_no_gap_rows_from_db():
    """_fill_verse_gaps() skips gap when DB returns no rows for the missing verse."""
    from unittest.mock import AsyncMock, MagicMock
    from search import _fill_verse_gaps

    mock_db = AsyncMock()
    empty_gap = MagicMock()
    empty_gap.all.return_value = []  # DB finds no rows for the gap verse
    mock_db.execute = AsyncMock(return_value=empty_gap)

    results = [
        {"reference": {"book": "John", "chapter": 3, "verse": 1}, "relevance_score": 0.9, "verse_id": "v1"},
        {"reference": {"book": "John", "chapter": 3, "verse": 3}, "relevance_score": 0.8, "verse_id": "v3"},
    ]

    filled = await _fill_verse_gaps(mock_db, results, [], {})
    # Gap detected but DB returned nothing — no insertion
    assert len(filled) == 2


# --- get_original_words sibling lookup ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_original_words_finds_words_via_sibling(test_db, sample_book, sample_translation):
    """get_original_words() finds original words via sibling verse lookup."""
    from tests.conftest import Verse, OriginalWord, Translation
    from search import get_original_words

    # Create a second translation
    trans2 = Translation(
        id=str(uuid.uuid4()),
        name="Second Translation",
        abbreviation="ST2",
        language_code="en",
        is_original_language=False,
    )
    test_db.add(trans2)
    await test_db.flush()

    # Two verses at same book/chapter/verse — different translations
    verse1 = Verse(
        id=str(uuid.uuid4()),
        translation_id=sample_translation.id,
        book_id=sample_book.id,
        chapter=1,
        verse=5,
        text="Verse in first translation",
    )
    verse2 = Verse(
        id=str(uuid.uuid4()),
        translation_id=trans2.id,
        book_id=sample_book.id,
        chapter=1,
        verse=5,
        text="Verse in second translation",
    )
    test_db.add(verse1)
    test_db.add(verse2)
    await test_db.flush()

    # Only verse2 has original words
    word = OriginalWord(
        id=str(uuid.uuid4()),
        verse_id=verse2.id,
        word="λόγος",
        language="greek",
        strongs_number="G3056",
        transliteration="logos",
        morphology="N-NSM",
        definition="word, reason",
        word_order=1,
    )
    test_db.add(word)
    await test_db.commit()

    # Query using verse1's ID — no direct words, should find via sibling (verse2)
    result = await get_original_words(test_db, uuid.UUID(verse1.id))

    assert result is not None
    assert result["language"] == "greek"
    assert len(result["words"]) == 1
    assert result["words"][0]["strongs"] == "G3056"
