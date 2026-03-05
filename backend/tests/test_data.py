"""Tests to ensure data modules are importable and well-formed."""

import pytest


@pytest.mark.unit
def test_books_metadata_importable():
    """data.books_metadata module can be imported."""
    from data import books_metadata
    assert books_metadata is not None


@pytest.mark.unit
def test_books_metadata_has_books():
    """books_metadata module contains book data."""
    from data.books_metadata import BOOKS_METADATA
    assert isinstance(BOOKS_METADATA, list)
    assert len(BOOKS_METADATA) > 0


@pytest.mark.unit
def test_books_metadata_first_entry_structure():
    """First BOOKS_METADATA entry has required fields."""
    from data.books_metadata import BOOKS_METADATA
    first = BOOKS_METADATA[0]
    assert hasattr(first, "name")
    assert hasattr(first, "testament")


@pytest.mark.unit
def test_get_book_by_number_found():
    """get_book_by_number() returns correct book for valid number."""
    from data.books_metadata import get_book_by_number
    book = get_book_by_number(1)
    assert book is not None
    assert book.name == "Genesis"


@pytest.mark.unit
def test_get_book_by_number_not_found():
    """get_book_by_number() returns None for invalid number."""
    from data.books_metadata import get_book_by_number
    assert get_book_by_number(999) is None


@pytest.mark.unit
def test_get_book_by_name_english():
    """get_book_by_name() finds book by English name."""
    from data.books_metadata import get_book_by_name
    book = get_book_by_name("Genesis")
    assert book is not None
    assert book.book_number == 1


@pytest.mark.unit
def test_get_book_by_name_abbreviation():
    """get_book_by_name() finds book by abbreviation (case-insensitive)."""
    from data.books_metadata import get_book_by_name
    book = get_book_by_name("gen")
    assert book is not None
    assert book.name == "Genesis"


@pytest.mark.unit
def test_get_book_by_name_not_found():
    """get_book_by_name() returns None for unknown name."""
    from data.books_metadata import get_book_by_name
    assert get_book_by_name("Fakebook") is None


@pytest.mark.unit
def test_get_books_by_testament():
    """get_books_by_testament() returns only OT or NT books."""
    from data.books_metadata import get_books_by_testament
    ot_books = get_books_by_testament("OT")
    nt_books = get_books_by_testament("NT")
    assert len(ot_books) == 39
    assert len(nt_books) == 27
    assert all(b.testament == "OT" for b in ot_books)


@pytest.mark.unit
def test_get_books_by_genre():
    """get_books_by_genre() returns only books of matching genre."""
    from data.books_metadata import get_books_by_genre
    law_books = get_books_by_genre("law")
    assert len(law_books) > 0
    assert all(b.genre == "law" for b in law_books)
