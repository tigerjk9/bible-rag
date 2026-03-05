"""Tests for cross-reference parsing and management."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


def _make_mgr():
    """Create a CrossReferenceManager without calling __init__."""
    from cross_references import CrossReferenceManager
    mgr = CrossReferenceManager.__new__(CrossReferenceManager)
    mgr.db = MagicMock()
    mgr._should_close_db = False
    return mgr


# --- parse_verse_reference ---

@pytest.mark.unit
def test_parse_verse_reference_dot_format():
    """parse_verse_reference() handles 'Gen.1.1' format."""
    mgr = _make_mgr()
    result = mgr.parse_verse_reference("Gen.1.1")
    assert result == ("Gen", 1, 1)


@pytest.mark.unit
def test_parse_verse_reference_dot_format_nt():
    """parse_verse_reference() handles 'Matt.5.3' format."""
    mgr = _make_mgr()
    result = mgr.parse_verse_reference("Matt.5.3")
    assert result == ("Matt", 5, 3)


@pytest.mark.unit
def test_parse_verse_reference_colon_format():
    """parse_verse_reference() handles 'Genesis 1:1' format."""
    mgr = _make_mgr()
    result = mgr.parse_verse_reference("Genesis 1:1")
    assert result == ("Genesis", 1, 1)


@pytest.mark.unit
def test_parse_verse_reference_colon_format_multiword():
    """parse_verse_reference() handles 'Song of Songs 3:4' format."""
    mgr = _make_mgr()
    result = mgr.parse_verse_reference("Song of Songs 3:4")
    assert result == ("Song of Songs", 3, 4)


@pytest.mark.unit
def test_parse_verse_reference_invalid_returns_none():
    """parse_verse_reference() returns None for invalid input."""
    mgr = _make_mgr()
    result = mgr.parse_verse_reference("not a verse ref")
    assert result is None


@pytest.mark.unit
def test_parse_verse_reference_empty_string():
    """parse_verse_reference() returns None for empty string."""
    mgr = _make_mgr()
    result = mgr.parse_verse_reference("")
    assert result is None


@pytest.mark.unit
def test_parse_verse_reference_non_numeric_chapter():
    """parse_verse_reference() returns None when chapter is not numeric."""
    mgr = _make_mgr()
    result = mgr.parse_verse_reference("Gen.a.1")
    assert result is None


# --- find_verse_by_reference ---

@pytest.mark.unit
def test_find_verse_by_reference_book_not_found():
    """find_verse_by_reference() returns None when book is not found."""
    mgr = _make_mgr()
    mgr.db.execute.return_value.scalar_one_or_none.return_value = None

    result = mgr.find_verse_by_reference("NonexistentBook", 1, 1)
    assert result is None


@pytest.mark.unit
def test_find_verse_by_reference_translation_not_found():
    """find_verse_by_reference() returns None when translation is not found."""
    mock_book = MagicMock()
    mgr = _make_mgr()
    # First call (book query) returns a book, second (translation) returns None
    mgr.db.execute.return_value.scalar_one_or_none.side_effect = [mock_book, None]

    result = mgr.find_verse_by_reference("Genesis", 1, 1, translation_abbrev="MISSING")
    assert result is None


@pytest.mark.unit
def test_find_verse_by_reference_success():
    """find_verse_by_reference() returns Verse when found."""
    mock_book = MagicMock()
    mock_translation = MagicMock()
    mock_verse = MagicMock()
    mgr = _make_mgr()
    mgr.db.execute.return_value.scalar_one_or_none.side_effect = [
        mock_book, mock_translation, mock_verse
    ]

    result = mgr.find_verse_by_reference("Genesis", 1, 1)
    assert result is mock_verse


# --- fetch_openbible_data ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_fetch_openbible_data_returns_list():
    """fetch_openbible_data() returns combined list from all files."""
    sample_response = {"cross_references": [{"from": "Gen.1.1", "to": "John.1.1"}]}

    mock_response = MagicMock()
    mock_response.json.return_value = sample_response
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mgr = _make_mgr()

    with patch("cross_references.httpx.AsyncClient", return_value=mock_client):
        result = await mgr.fetch_openbible_data()

    # 7 files, each with 1 entry
    assert len(result) == 7
    assert result[0]["from"] == "Gen.1.1"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fetch_openbible_data_http_error_raises():
    """fetch_openbible_data() raises on HTTP error."""
    import httpx

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock()
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mgr = _make_mgr()

    with patch("cross_references.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await mgr.fetch_openbible_data()


# --- relationship type mapping ---

@pytest.mark.unit
def test_relationship_types_mapping():
    """CrossReferenceManager has expected relationship type keys."""
    mgr = _make_mgr()
    assert "quotation" in mgr.RELATIONSHIP_TYPES
    assert "allusion" in mgr.RELATIONSHIP_TYPES
    assert "parallel" in mgr.RELATIONSHIP_TYPES
    assert "theme" in mgr.RELATIONSHIP_TYPES


# --- create_cross_reference ---

@pytest.mark.unit
def test_create_cross_reference_creates_new():
    """create_cross_reference() creates a new CrossReference and adds it to db."""
    mgr = _make_mgr()

    # No existing cross-reference
    mgr.db.query.return_value.filter.return_value.first.return_value = None

    from_verse = MagicMock()
    from_verse.id = "verse-1"
    to_verse = MagicMock()
    to_verse.id = "verse-2"

    result = mgr.create_cross_reference(from_verse, to_verse, "parallel", confidence=0.9)

    assert result is not None
    mgr.db.add.assert_called_once()
    assert result.relationship_type == "parallel"
    assert result.confidence == 0.9


@pytest.mark.unit
def test_create_cross_reference_returns_none_if_exists():
    """create_cross_reference() returns None when duplicate exists."""
    mgr = _make_mgr()

    existing = MagicMock()
    mgr.db.query.return_value.filter.return_value.first.return_value = existing

    from_verse = MagicMock()
    to_verse = MagicMock()

    result = mgr.create_cross_reference(from_verse, to_verse, "quotation")
    assert result is None
    mgr.db.add.assert_not_called()


# --- generate_semantic_cross_references ---

@pytest.mark.unit
def test_generate_semantic_cross_references_returns_empty():
    """generate_semantic_cross_references() returns [] (not yet implemented)."""
    from uuid import uuid4
    mgr = _make_mgr()

    result = mgr.generate_semantic_cross_references(uuid4())
    assert result == []


# --- get_cross_references ---

@pytest.mark.unit
def test_get_cross_references_empty():
    """get_cross_references() returns empty list when no refs exist."""
    from uuid import uuid4
    mgr = _make_mgr()

    mgr.db.query.return_value.filter.return_value.all.return_value = []

    result = mgr.get_cross_references(uuid4())
    assert result == []


@pytest.mark.unit
def test_get_cross_references_with_results():
    """get_cross_references() maps CrossReference objects to dicts."""
    from uuid import uuid4
    mgr = _make_mgr()

    # Mock a cross reference with a related verse
    mock_related = MagicMock()
    mock_related.id = str(uuid4())
    mock_related.book.name = "John"
    mock_related.book.name_korean = "요한복음"
    mock_related.chapter = 3
    mock_related.verse = 16
    mock_related.text = "For God so loved..."

    mock_ref = MagicMock()
    mock_ref.related_verse = mock_related
    mock_ref.relationship_type = "quotation"
    mock_ref.confidence = 0.95

    mgr.db.query.return_value.filter.return_value.all.return_value = [mock_ref]

    result = mgr.get_cross_references(uuid4())
    assert len(result) == 1
    assert result[0]["book"] == "John"
    assert result[0]["relationship_type"] == "quotation"
    assert result[0]["confidence"] == 0.95


# --- populate_from_openbible ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_populate_from_openbible_empty_data_returns_zero():
    """populate_from_openbible() returns 0 when no data fetched."""
    from unittest.mock import AsyncMock, patch

    mgr = _make_mgr()

    with patch.object(mgr, "fetch_openbible_data", new=AsyncMock(return_value=[])):
        result = await mgr.populate_from_openbible()

    assert result == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_populate_from_openbible_skips_entries_without_verse_data():
    """populate_from_openbible() skips entries missing from_verse or to_verse."""
    from unittest.mock import AsyncMock, patch

    mgr = _make_mgr()

    bad_entries = [
        {"votes": 10},  # no from_verse or to_verse
        {"from_verse": None, "to_verse": [], "votes": 5},  # None from_verse
    ]

    with patch.object(mgr, "fetch_openbible_data", new=AsyncMock(return_value=bad_entries)):
        result = await mgr.populate_from_openbible()

    assert result == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_populate_from_openbible_skips_when_from_verse_not_found():
    """populate_from_openbible() skips entries when from_verse not found in DB."""
    from unittest.mock import AsyncMock, patch, MagicMock

    mgr = _make_mgr()

    entries = [
        {
            "from_verse": {"book": "Nonexistent", "chapter": 1, "verse": 1},
            "to_verse": [{"book": "John", "chapter": 3, "verse_start": 16}],
            "votes": 10,
        }
    ]

    with patch.object(mgr, "fetch_openbible_data", new=AsyncMock(return_value=entries)):
        with patch.object(mgr, "find_verse_by_reference", return_value=None):
            result = await mgr.populate_from_openbible()

    assert result == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_populate_from_openbible_creates_bidirectional_refs():
    """populate_from_openbible() creates cross-references for valid entries."""
    from unittest.mock import AsyncMock, patch, MagicMock

    mgr = _make_mgr()
    mgr.db.commit = MagicMock()

    mock_from_verse = MagicMock()
    mock_from_verse.id = "verse-a"
    mock_to_verse = MagicMock()
    mock_to_verse.id = "verse-b"
    mock_cross_ref = MagicMock()

    entries = [
        {
            "from_verse": {"book": "Genesis", "chapter": 1, "verse": 1},
            "to_verse": [{"book": "John", "chapter": 1, "verse_start": 1, "verse_end": 1}],
            "votes": 50,
        }
    ]

    find_verse_results = [mock_from_verse, mock_to_verse]

    with patch.object(mgr, "fetch_openbible_data", new=AsyncMock(return_value=entries)):
        with patch.object(mgr, "find_verse_by_reference", side_effect=find_verse_results):
            with patch.object(mgr, "create_cross_reference", return_value=mock_cross_ref):
                result = await mgr.populate_from_openbible()

    assert result == 2  # forward + reverse refs
