"""Tests for original language (Strong's) parsing and management."""

import pytest
from unittest.mock import MagicMock, patch


def _make_mgr():
    """Create an OriginalLanguageManager without calling __init__."""
    from original_language import OriginalLanguageManager
    mgr = OriginalLanguageManager.__new__(OriginalLanguageManager)
    mgr.db = MagicMock()
    mgr._should_close_db = False
    mgr.strongs_hebrew_data = None
    mgr.strongs_greek_data = None
    return mgr


# --- _parse_js_dictionary ---

@pytest.mark.unit
def test_parse_js_dictionary_valid_input():
    """_parse_js_dictionary() parses valid JS dictionary format."""
    mgr = _make_mgr()
    js_text = 'var dict = {"G1": {"word": "alpha"}, "G2": {"word": "beta"}}; module.exports = dict;'
    result = mgr._parse_js_dictionary(js_text)

    assert isinstance(result, dict)
    assert "G1" in result
    assert result["G1"]["word"] == "alpha"
    assert "G2" in result


@pytest.mark.unit
def test_parse_js_dictionary_no_dict_start():
    """_parse_js_dictionary() returns {} when no '= {' found."""
    mgr = _make_mgr()
    result = mgr._parse_js_dictionary("no dictionary here")
    assert result == {}


@pytest.mark.unit
def test_parse_js_dictionary_no_dict_end():
    """_parse_js_dictionary() returns {} when no '};' found."""
    mgr = _make_mgr()
    result = mgr._parse_js_dictionary('var x = {"key": "value"')  # missing };
    assert result == {}


@pytest.mark.unit
def test_parse_js_dictionary_invalid_json():
    """_parse_js_dictionary() returns {} on JSON parse error."""
    mgr = _make_mgr()
    # Valid start/end markers but invalid JSON content
    result = mgr._parse_js_dictionary('var x = {invalid json here};')
    assert result == {}


@pytest.mark.unit
def test_parse_js_dictionary_empty_dict():
    """_parse_js_dictionary() handles empty dictionary."""
    mgr = _make_mgr()
    result = mgr._parse_js_dictionary('var x = {}; module.exports = x;')
    assert result == {}


# --- _parse_dat_format ---

@pytest.mark.unit
def test_parse_dat_format_greek_entry():
    """_parse_dat_format() parses a Greek Strong's .dat entry."""
    mgr = _make_mgr()
    dat_text = "$$T0000025\n\\025\\\n 25  agapao  ag-ap-ah'-o\n\n To love:--love.\n"
    result = mgr._parse_dat_format(dat_text, "greek")

    assert isinstance(result, dict)
    assert "G25" in result


@pytest.mark.unit
def test_parse_dat_format_hebrew_entry():
    """_parse_dat_format() uses 'H' prefix for hebrew."""
    mgr = _make_mgr()
    dat_text = "$$T0000001\n\\01\\\n 1  ab  awb\n\n Father:--father.\n"
    result = mgr._parse_dat_format(dat_text, "hebrew")
    assert "H1" in result


@pytest.mark.unit
def test_parse_dat_format_empty_input():
    """_parse_dat_format() returns {} for empty input."""
    mgr = _make_mgr()
    result = mgr._parse_dat_format("", "greek")
    assert result == {}


@pytest.mark.unit
def test_parse_dat_format_malformed_lines_skipped():
    """_parse_dat_format() skips entries without a valid number."""
    mgr = _make_mgr()
    dat_text = (
        "$$T\nno number here\njust text\n\n"
        "$$T0000005\n\\05\\\n 5  word  pronunciation\n\n Definition.\n"
    )
    result = mgr._parse_dat_format(dat_text, "greek")
    # Only the entry with a valid number parses correctly
    assert "G5" in result


# --- OriginalLanguageManager initialization ---

@pytest.mark.unit
def test_manager_initializes_with_none_data():
    """OriginalLanguageManager starts with None for strongs data."""
    mgr = _make_mgr()
    assert mgr.strongs_hebrew_data is None
    assert mgr.strongs_greek_data is None


@pytest.mark.unit
def test_language_prefix_assignment():
    """_parse_dat_format() correctly assigns G vs H prefix by language."""
    mgr = _make_mgr()
    dat_text = "$$T0000010\n\\010\\\n 10 word pron\n\n definition.\n"

    greek_result = mgr._parse_dat_format(dat_text, "greek")
    hebrew_result = mgr._parse_dat_format(dat_text, "hebrew")

    assert "G10" in greek_result
    assert "H10" in hebrew_result
    assert "H10" not in greek_result
    assert "G10" not in hebrew_result


# --- STRONGS URL constants ---

@pytest.mark.unit
def test_strongs_urls_defined():
    """OriginalLanguageManager defines expected URL constants."""
    from original_language import OriginalLanguageManager

    assert "strongs" in OriginalLanguageManager.STRONGS_GREEK_URL.lower()
    assert "strongs" in OriginalLanguageManager.STRONGS_HEBREW_URL.lower()
    assert "greek" in OriginalLanguageManager.STRONGS_GREEK_URL.lower()
    assert "hebrew" in OriginalLanguageManager.STRONGS_HEBREW_URL.lower()


# --- fetch_strongs_data (async) ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_fetch_strongs_data_js_format_success():
    """fetch_strongs_data() stores parsed JS data on success."""
    from unittest.mock import AsyncMock, patch, MagicMock

    mgr = _make_mgr()

    js_content = 'var dict = {"G1": {"word": "alpha"}}; module.exports = dict;'
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = js_content

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("original_language.httpx.AsyncClient", return_value=mock_client):
        hebrew_data, greek_data = await mgr.fetch_strongs_data()

    # Greek data parsed from JS dict (both calls return same mock)
    assert isinstance(greek_data, dict)
    assert mgr.strongs_greek_data is greek_data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fetch_strongs_data_falls_back_to_dat():
    """fetch_strongs_data() falls back to .dat format when JS fails."""
    import httpx
    from unittest.mock import AsyncMock, patch, MagicMock

    mgr = _make_mgr()

    dat_content = "$$T0000001\n\\01\\\n 1  word  pron\n\n Definition.\\n"

    def make_response(content=None, raise_error=False):
        r = MagicMock()
        if raise_error:
            r.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=MagicMock()
            )
        else:
            r.raise_for_status = MagicMock()
            r.text = content
        return r

    # First call (JS) raises, second call (.dat) succeeds
    side_effects = [
        make_response(raise_error=True),   # hebrew JS fails
        make_response(dat_content),        # hebrew dat succeeds
        make_response(raise_error=True),   # greek JS fails
        make_response(dat_content),        # greek dat succeeds
    ]

    mock_client = AsyncMock()
    mock_client.get.side_effect = side_effects
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("original_language.httpx.AsyncClient", return_value=mock_client):
        hebrew_data, greek_data = await mgr.fetch_strongs_data()

    assert isinstance(hebrew_data, dict)
    assert isinstance(greek_data, dict)


# --- fetch_strongs_data_sync ---

@pytest.mark.unit
def test_fetch_strongs_data_sync_success():
    """fetch_strongs_data_sync() loads .dat format via requests."""
    from unittest.mock import patch, MagicMock

    mgr = _make_mgr()
    dat_content = "$$T0000025\n\\025\\\n 25  agapao  ag-ap-ah'-o\n\n To love.\\n"

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = dat_content

    with patch("original_language.requests.get", return_value=mock_response):
        hebrew_data, greek_data = mgr.fetch_strongs_data_sync()

    assert isinstance(hebrew_data, dict)
    assert isinstance(greek_data, dict)
    assert mgr.strongs_hebrew_data is hebrew_data
    assert mgr.strongs_greek_data is greek_data


# --- get_strongs_definition ---

@pytest.mark.unit
def test_get_strongs_definition_greek_not_loaded_returns_none():
    """get_strongs_definition() returns None when Greek data not loaded."""
    mgr = _make_mgr()
    mgr.strongs_greek_data = None

    result = mgr.get_strongs_definition("G25", "greek")
    assert result is None


@pytest.mark.unit
def test_get_strongs_definition_hebrew_not_loaded_returns_none():
    """get_strongs_definition() returns None when Hebrew data not loaded."""
    mgr = _make_mgr()
    mgr.strongs_hebrew_data = None

    result = mgr.get_strongs_definition("H157", "hebrew")
    assert result is None


@pytest.mark.unit
def test_get_strongs_definition_found():
    """get_strongs_definition() returns entry from loaded data."""
    mgr = _make_mgr()
    mgr.strongs_greek_data = {
        "G25": {"strongs_def": "to love", "lemma": "ἀγαπάω", "translit": "agapao"}
    }

    result = mgr.get_strongs_definition("G25", "greek")
    assert result is not None
    assert result["strongs_def"] == "to love"


@pytest.mark.unit
def test_get_strongs_definition_not_found_returns_none():
    """get_strongs_definition() returns None when number not in data."""
    mgr = _make_mgr()
    mgr.strongs_greek_data = {}

    result = mgr.get_strongs_definition("G9999", "greek")
    assert result is None


# --- parse_strongs_from_text ---

@pytest.mark.unit
def test_parse_strongs_from_text_finds_greek():
    """parse_strongs_from_text() finds G-prefixed Strong's numbers."""
    mgr = _make_mgr()
    result = mgr.parse_strongs_from_text("See G25 and G1234 for love terms.")
    assert "G25" in result
    assert "G1234" in result


@pytest.mark.unit
def test_parse_strongs_from_text_finds_hebrew():
    """parse_strongs_from_text() finds H-prefixed Strong's numbers."""
    mgr = _make_mgr()
    result = mgr.parse_strongs_from_text("Hebrew root H157 (love) and H430 (God).")
    assert "H157" in result
    assert "H430" in result


@pytest.mark.unit
def test_parse_strongs_from_text_empty_returns_empty():
    """parse_strongs_from_text() returns empty list for no matches."""
    mgr = _make_mgr()
    result = mgr.parse_strongs_from_text("No strongs numbers here.")
    assert result == []


# --- populate_from_original_text ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_populate_from_original_text_returns_zero():
    """populate_from_original_text() returns 0 (not yet implemented)."""
    mgr = _make_mgr()
    result = await mgr.populate_from_original_text("SBLGNT")
    assert result == 0


# --- create_original_word ---

@pytest.mark.unit
def test_create_original_word_no_strongs():
    """create_original_word() creates OriginalWord without Strong's enrichment."""
    from unittest.mock import MagicMock

    mgr = _make_mgr()
    mgr.db.add = MagicMock()

    mock_verse = MagicMock()
    mock_verse.id = "verse-uuid"

    word = mgr.create_original_word(
        verse=mock_verse,
        word="ἀγάπη",
        language="greek",
        word_order=1,
    )

    assert word is not None
    assert word.word == "ἀγάπη"
    assert word.language == "greek"
    mgr.db.add.assert_called_once_with(word)


@pytest.mark.unit
def test_create_original_word_with_strongs_enriches_definition():
    """create_original_word() enriches definition from loaded Strong's data."""
    from unittest.mock import MagicMock

    mgr = _make_mgr()
    mgr.db.add = MagicMock()
    mgr.strongs_greek_data = {
        "G26": {"strongs_def": "love", "translit": "agape", "lemma": "ἀγάπη"}
    }

    mock_verse = MagicMock()
    mock_verse.id = "verse-uuid"

    word = mgr.create_original_word(
        verse=mock_verse,
        word="",
        language="greek",
        strongs_number="G26",
        word_order=1,
    )

    # Definition and transliteration should be filled from Strong's data
    assert word.definition == "love"
    assert word.transliteration == "agape"


# --- get_original_words ---

@pytest.mark.unit
def test_get_original_words_returns_list():
    """get_original_words() returns formatted list from DB query."""
    from unittest.mock import MagicMock
    from uuid import uuid4

    mgr = _make_mgr()

    mock_word = MagicMock()
    mock_word.word = "ἀγάπη"
    mock_word.language = "greek"
    mock_word.strongs_number = "G26"
    mock_word.transliteration = "agape"
    mock_word.morphology = "N-NSF"
    mock_word.definition = "love"
    mock_word.word_order = 1

    # get_original_words uses self.db.query(OriginalWord).filter(...).order_by(...).all()
    mgr.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_word]

    result = mgr.get_original_words(uuid4())

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["word"] == "ἀγάπη"
    assert result[0]["language"] == "greek"


@pytest.mark.unit
def test_get_original_words_empty_returns_empty():
    """get_original_words() returns empty list when no words found."""
    from uuid import uuid4

    mgr = _make_mgr()
    mgr.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    result = mgr.get_original_words(uuid4())
    assert result == []


# --- get_verses_with_strongs ---

@pytest.mark.unit
def test_get_verses_with_strongs_returns_list():
    """get_verses_with_strongs() returns formatted verse list."""
    from unittest.mock import MagicMock
    from uuid import uuid4

    mgr = _make_mgr()

    verse_id = uuid4()
    mock_word = MagicMock()
    mock_word.verse_id = verse_id
    mock_word.word = "ἀγαπάω"
    mock_word.transliteration = "agapao"

    mock_verse = MagicMock()
    mock_verse.id = verse_id
    mock_verse.chapter = 3
    mock_verse.verse = 16
    mock_verse.text = "For God so loved..."
    mock_verse.book.name = "John"
    mock_verse.book.name_korean = "요한복음"
    mock_word.verse = mock_verse

    mgr.db.query.return_value.filter.return_value.all.return_value = [mock_word]

    result = mgr.get_verses_with_strongs("G26")

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["book"] == "John"
    assert result[0]["word"] == "ἀγαπάω"


@pytest.mark.unit
def test_get_verses_with_strongs_empty_returns_empty():
    """get_verses_with_strongs() returns empty list when no matches."""
    mgr = _make_mgr()
    mgr.db.query.return_value.filter.return_value.all.return_value = []

    result = mgr.get_verses_with_strongs("G9999")
    assert result == []


# --- __init__ and __del__ ---

@pytest.mark.unit
def test_manager_init_with_provided_db():
    """OriginalLanguageManager.__init__ stores provided db without closing it."""
    from original_language import OriginalLanguageManager

    mock_db = MagicMock()
    with patch("original_language.SessionLocal", return_value=MagicMock()):
        mgr = OriginalLanguageManager(db=mock_db)

    assert mgr.db is mock_db
    assert mgr._should_close_db is False
    assert mgr.strongs_hebrew_data is None
    assert mgr.strongs_greek_data is None


@pytest.mark.unit
def test_manager_init_creates_session_when_no_db():
    """OriginalLanguageManager.__init__ creates its own session when db=None."""
    from original_language import OriginalLanguageManager

    mock_session = MagicMock()
    with patch("original_language.SessionLocal", return_value=mock_session):
        mgr = OriginalLanguageManager(db=None)

    assert mgr.db is mock_session
    assert mgr._should_close_db is True


@pytest.mark.unit
def test_manager_del_closes_db_when_owned():
    """OriginalLanguageManager.__del__ closes db when _should_close_db=True."""
    mgr = _make_mgr()
    mgr._should_close_db = True
    mock_db = MagicMock()
    mgr.db = mock_db

    mgr.__del__()

    mock_db.close.assert_called_once()


# --- httpx not available ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_fetch_strongs_data_raises_without_httpx():
    """fetch_strongs_data() raises ImportError when httpx is not available."""
    import original_language as ol_module
    original_available = ol_module.HTTPX_AVAILABLE
    try:
        ol_module.HTTPX_AVAILABLE = False
        mgr = _make_mgr()
        with pytest.raises(ImportError, match="httpx"):
            await mgr.fetch_strongs_data()
    finally:
        ol_module.HTTPX_AVAILABLE = original_available


# --- fetch_strongs_data dat fallback errors ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_fetch_strongs_data_all_fallbacks_fail():
    """fetch_strongs_data() returns empty dicts when all fetches fail."""
    import httpx

    mgr = _make_mgr()

    def make_error_response():
        r = MagicMock()
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock()
        )
        return r

    mock_client = MagicMock()
    mock_client.get = MagicMock(return_value=make_error_response())
    mock_client.__aenter__ = MagicMock(return_value=mock_client)
    mock_client.__aexit__ = MagicMock(return_value=None)

    from unittest.mock import AsyncMock
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(side_effect=Exception("network error"))

    with patch("original_language.httpx.AsyncClient", return_value=mock_client):
        hebrew_data, greek_data = await mgr.fetch_strongs_data()

    assert hebrew_data == {}
    assert greek_data == {}


# --- fetch_strongs_data_sync error paths ---

@pytest.mark.unit
def test_fetch_strongs_data_sync_both_fail():
    """fetch_strongs_data_sync() returns empty dicts when both requests fail."""
    import requests as req_module

    mgr = _make_mgr()

    with patch("original_language.requests.get", side_effect=req_module.RequestException("timeout")):
        hebrew_data, greek_data = mgr.fetch_strongs_data_sync()

    assert hebrew_data == {}
    assert greek_data == {}
    assert mgr.strongs_hebrew_data == {}
    assert mgr.strongs_greek_data == {}


# --- _parse_dat_format: see GREEK/HEBREW skip ---

@pytest.mark.unit
def test_parse_dat_format_skips_see_greek_lines():
    """_parse_dat_format() skips 'see GREEK' / 'see HEBREW' reference lines."""
    mgr = _make_mgr()
    # Entry has a "see GREEK" cross-reference line that should be skipped
    dat_text = (
        "$$T0000430\n"
        "\\0430\\\n"
        " 430  elohim  el-o-heem'\n"
        "see GREEK 2316\n"
        " plural of 433; gods:--God.\n"
    )
    result = mgr._parse_dat_format(dat_text, "hebrew")
    assert "H430" in result
    # Definition should not include the "see GREEK" line
    assert "see GREEK" not in result["H430"]["strongs_def"]


# --- populate_greek_nt ---

@pytest.mark.unit
def test_populate_greek_nt_success():
    """populate_greek_nt() creates OriginalWord entries for each word."""
    mgr = _make_mgr()
    mgr.strongs_greek_data = {
        "G3779": {"strongs_def": "so, thus", "translit": "houtōs"}
    }

    mock_book = MagicMock()
    mock_book.id = "book-uuid"
    mock_verse = MagicMock()
    mock_verse.id = "verse-uuid"

    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = mock_book
    verse_result = MagicMock()
    verse_result.scalars.return_value.first.return_value = mock_verse

    mgr.db.execute.side_effect = [book_result, verse_result]
    mgr.db.add_all = MagicMock()
    mgr.db.commit = MagicMock()

    verses_data = [
        {
            "book_number": 43,
            "chapter": 3,
            "verse": 16,
            "words": [
                {"text": "οὕτως", "strongs": "G3779", "transliteration": "houtōs", "morphology": "ADV", "word_order": 1}
            ],
        }
    ]

    count = mgr.populate_greek_nt(verses_data, batch_size=100)
    assert count == 1
    mgr.db.commit.assert_called()


@pytest.mark.unit
def test_populate_greek_nt_book_not_found():
    """populate_greek_nt() skips verse when book is not in database."""
    mgr = _make_mgr()
    mgr.strongs_greek_data = {}

    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = None  # book not found
    mgr.db.execute.return_value = book_result

    verses_data = [{"book_number": 99, "chapter": 1, "verse": 1, "words": []}]
    count = mgr.populate_greek_nt(verses_data)
    assert count == 0


@pytest.mark.unit
def test_populate_greek_nt_verse_not_found():
    """populate_greek_nt() skips when verse is not in database."""
    mgr = _make_mgr()
    mgr.strongs_greek_data = {}

    mock_book = MagicMock()
    mock_book.id = "book-uuid"

    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = mock_book

    verse_result = MagicMock()
    verse_result.scalars.return_value.first.return_value = None  # verse not found

    mgr.db.execute.side_effect = [book_result, verse_result]

    verses_data = [{"book_number": 43, "chapter": 999, "verse": 1, "words": [{"text": "word", "word_order": 1}]}]
    count = mgr.populate_greek_nt(verses_data)
    assert count == 0


@pytest.mark.unit
def test_populate_greek_nt_loads_strongs_if_not_loaded():
    """populate_greek_nt() calls fetch_strongs_data_sync when data not loaded."""
    mgr = _make_mgr()
    mgr.strongs_greek_data = None  # not loaded

    # fetch_strongs_data_sync should be called
    with patch.object(mgr, "fetch_strongs_data_sync") as mock_fetch:
        mock_fetch.side_effect = lambda: setattr(mgr, "strongs_greek_data", {}) or setattr(mgr, "strongs_hebrew_data", {})
        mgr.db.execute.return_value.scalar_one_or_none.return_value = None

        count = mgr.populate_greek_nt([])

    mock_fetch.assert_called_once()
    assert count == 0


@pytest.mark.unit
def test_populate_greek_nt_batch_commit():
    """populate_greek_nt() commits intermediate batches when batch_size is reached."""
    mgr = _make_mgr()
    mgr.strongs_greek_data = {}

    mock_book = MagicMock()
    mock_book.id = "book-uuid"
    mock_verse = MagicMock()
    mock_verse.id = "verse-uuid"

    def make_db_side_effect(n_words):
        results = []
        for _ in range(n_words):
            book_r = MagicMock()
            book_r.scalar_one_or_none.return_value = mock_book
            verse_r = MagicMock()
            verse_r.scalars.return_value.first.return_value = mock_verse
            results.extend([book_r, verse_r])
        return results

    # 3 verses each with 1 word, batch_size=2 → should commit mid-loop
    verses_data = [
        {"book_number": 43, "chapter": 3, "verse": i, "words": [{"text": "word", "word_order": 1}]}
        for i in range(1, 4)
    ]
    mgr.db.execute.side_effect = make_db_side_effect(3)
    mgr.db.add_all = MagicMock()
    mgr.db.commit = MagicMock()

    count = mgr.populate_greek_nt(verses_data, batch_size=2)
    assert count == 3
    # Should have committed at least twice (mid-batch + final)
    assert mgr.db.commit.call_count >= 2


# --- populate_hebrew_ot ---

@pytest.mark.unit
def test_populate_hebrew_ot_success():
    """populate_hebrew_ot() creates OriginalWord entries for Hebrew words."""
    mgr = _make_mgr()
    mgr.strongs_hebrew_data = {
        "H7225": {"strongs_def": "beginning", "translit": "reshit"}
    }

    mock_book = MagicMock()
    mock_book.id = "book-uuid"
    mock_verse = MagicMock()
    mock_verse.id = "verse-uuid"

    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = mock_book
    verse_result = MagicMock()
    verse_result.scalars.return_value.first.return_value = mock_verse

    mgr.db.execute.side_effect = [book_result, verse_result]
    mgr.db.add_all = MagicMock()
    mgr.db.commit = MagicMock()

    verses_data = [
        {
            "book": "Genesis",
            "chapter": 1,
            "verse": 1,
            "language": "hebrew",
            "words": [
                {"word": "בְּרֵאשִׁית", "strongs": "H7225", "transliteration": "bereshit", "morphology": "N-FS", "word_order": 1}
            ],
        }
    ]

    count = mgr.populate_hebrew_ot(verses_data, batch_size=100)
    assert count == 1
    mgr.db.commit.assert_called()


@pytest.mark.unit
def test_populate_hebrew_ot_missing_book_name():
    """populate_hebrew_ot() skips entries with no book name."""
    mgr = _make_mgr()
    mgr.strongs_hebrew_data = {}

    verses_data = [{"chapter": 1, "verse": 1, "words": []}]  # no "book" key
    count = mgr.populate_hebrew_ot(verses_data)
    assert count == 0
    mgr.db.execute.assert_not_called()


@pytest.mark.unit
def test_populate_hebrew_ot_book_not_found():
    """populate_hebrew_ot() skips when book not found in database."""
    mgr = _make_mgr()
    mgr.strongs_hebrew_data = {}

    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = None
    mgr.db.execute.return_value = book_result

    verses_data = [{"book": "UnknownBook", "chapter": 1, "verse": 1, "words": []}]
    count = mgr.populate_hebrew_ot(verses_data)
    assert count == 0


@pytest.mark.unit
def test_populate_hebrew_ot_verse_not_found():
    """populate_hebrew_ot() skips when verse not found in database."""
    mgr = _make_mgr()
    mgr.strongs_hebrew_data = {}

    mock_book = MagicMock()
    mock_book.id = "book-uuid"

    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = mock_book

    verse_result = MagicMock()
    verse_result.scalars.return_value.first.return_value = None

    mgr.db.execute.side_effect = [book_result, verse_result]

    verses_data = [{"book": "Genesis", "chapter": 999, "verse": 1, "words": [{"word": "word", "word_order": 1}]}]
    count = mgr.populate_hebrew_ot(verses_data)
    assert count == 0


@pytest.mark.unit
def test_populate_hebrew_ot_loads_strongs_if_not_loaded():
    """populate_hebrew_ot() calls fetch_strongs_data_sync when data not loaded."""
    mgr = _make_mgr()
    mgr.strongs_hebrew_data = None

    with patch.object(mgr, "fetch_strongs_data_sync") as mock_fetch:
        mock_fetch.side_effect = lambda: setattr(mgr, "strongs_hebrew_data", {}) or setattr(mgr, "strongs_greek_data", {})
        count = mgr.populate_hebrew_ot([])

    mock_fetch.assert_called_once()
    assert count == 0


@pytest.mark.unit
def test_populate_hebrew_ot_aramaic_language():
    """populate_hebrew_ot() uses language field from verse data (e.g. aramaic)."""
    mgr = _make_mgr()
    mgr.strongs_hebrew_data = {}

    mock_book = MagicMock()
    mock_book.id = "book-uuid"
    mock_verse = MagicMock()
    mock_verse.id = "verse-uuid"

    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = mock_book
    verse_result = MagicMock()
    verse_result.scalars.return_value.first.return_value = mock_verse

    mgr.db.execute.side_effect = [book_result, verse_result]
    mgr.db.add_all = MagicMock()
    mgr.db.commit = MagicMock()

    # Daniel 2:4 - starts in Aramaic
    verses_data = [
        {
            "book": "Daniel",
            "chapter": 2,
            "verse": 4,
            "language": "aramaic",
            "words": [{"word": "מַלְכָּא", "word_order": 1}],
        }
    ]

    count = mgr.populate_hebrew_ot(verses_data)
    assert count == 1


# --- add_sample_original_words ---

@pytest.mark.unit
def test_add_sample_original_words_book_not_found():
    """add_sample_original_words() skips entries when book not in database."""
    mgr = _make_mgr()

    # All book lookups return None
    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = None
    mgr.db.execute.return_value = book_result
    mgr.db.commit = MagicMock()

    count = mgr.add_sample_original_words()
    assert count == 0


@pytest.mark.unit
def test_add_sample_original_words_verse_not_found():
    """add_sample_original_words() skips entries when verse not found."""
    mgr = _make_mgr()

    mock_book = MagicMock()
    mock_book.id = "book-uuid"

    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = mock_book

    verse_result = MagicMock()
    verse_result.scalar_one_or_none.return_value = None  # verse not found

    # Both entries (John and Genesis) will fail at verse lookup
    mgr.db.execute.side_effect = [
        book_result, verse_result,  # John entry
        book_result, verse_result,  # Genesis entry
    ]
    mgr.db.commit = MagicMock()

    count = mgr.add_sample_original_words()
    assert count == 0


@pytest.mark.unit
def test_add_sample_original_words_success():
    """add_sample_original_words() creates words when book and verse found."""
    mgr = _make_mgr()
    mgr.strongs_greek_data = {
        "G3779": {"strongs_def": "so", "translit": "houtōs"},
        "G1063": {"strongs_def": "for", "translit": "gar"},
        "G25": {"strongs_def": "to love", "translit": "agapao"},
        "G3588": {"strongs_def": "the", "translit": "ho"},
        "G2316": {"strongs_def": "God", "translit": "theos"},
        "G2889": {"strongs_def": "world", "translit": "kosmos"},
    }
    mgr.strongs_hebrew_data = {
        "H7225": {"strongs_def": "beginning", "translit": "reshit"},
        "H1254": {"strongs_def": "create", "translit": "bara"},
        "H430": {"strongs_def": "God", "translit": "elohim"},
        "H853": {"strongs_def": "direct object marker", "translit": "et"},
        "H8064": {"strongs_def": "heavens", "translit": "shamayim"},
        "H776": {"strongs_def": "earth", "translit": "erets"},
    }

    mock_book = MagicMock()
    mock_book.id = "book-uuid"
    mock_verse = MagicMock()
    mock_verse.id = "verse-uuid"

    book_result = MagicMock()
    book_result.scalar_one_or_none.return_value = mock_book
    verse_result = MagicMock()
    verse_result.scalar_one_or_none.return_value = mock_verse

    # 2 entries: John and Genesis, each needs a book+verse lookup
    mgr.db.execute.side_effect = [
        book_result, verse_result,  # John 3:16
        book_result, verse_result,  # Genesis 1:1
    ]
    mgr.db.add = MagicMock()
    mgr.db.commit = MagicMock()

    count = mgr.add_sample_original_words()
    # John 3:16 has 7 words, Genesis 1:1 has 7 words
    assert count == 14
    mgr.db.commit.assert_called_once()
