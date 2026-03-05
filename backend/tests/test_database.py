"""Tests for database models and session management."""

import uuid
import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


# --- ORM Model Instantiation ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_translation_model_roundtrip(test_db):
    """Translation model can be created and queried."""
    from tests.conftest import Translation

    t = Translation(
        id=str(uuid.uuid4()),
        name="New International Version",
        abbreviation="NIV",
        language_code="en",
        is_original_language=False,
    )
    test_db.add(t)
    await test_db.commit()

    result = (await test_db.execute(select(Translation).where(Translation.abbreviation == "NIV"))).scalar_one()
    assert result.name == "New International Version"
    assert result.language_code == "en"
    assert result.is_original_language is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_book_model_roundtrip(test_db):
    """Book model can be created and queried."""
    from tests.conftest import Book

    b = Book(
        id=str(uuid.uuid4()),
        name="Romans",
        abbreviation="Rom",
        testament="NT",
        genre="epistle",
        book_number=45,
        total_chapters=16,
    )
    test_db.add(b)
    await test_db.commit()

    result = (await test_db.execute(select(Book).where(Book.abbreviation == "Rom"))).scalar_one()
    assert result.name == "Romans"
    assert result.testament == "NT"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_verse_model_roundtrip(test_db, sample_translation, sample_book):
    """Verse model can be created and queried."""
    from tests.conftest import Verse

    v = Verse(
        id=str(uuid.uuid4()),
        translation_id=sample_translation.id,
        book_id=sample_book.id,
        chapter=3,
        verse=16,
        text="For God so loved the world...",
    )
    test_db.add(v)
    await test_db.commit()

    result = (await test_db.execute(
        select(Verse).where(Verse.chapter == 3, Verse.verse == 16)
    )).scalar_one()
    assert result.text == "For God so loved the world..."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_verse_requires_valid_translation_id(test_db, sample_book):
    """Verse with invalid translation_id violates FK constraint."""
    from tests.conftest import Verse

    v = Verse(
        id=str(uuid.uuid4()),
        translation_id=str(uuid.uuid4()),  # nonexistent
        book_id=sample_book.id,
        chapter=1,
        verse=1,
        text="Test",
    )
    test_db.add(v)
    with pytest.raises(Exception):  # FK or integrity error
        await test_db.commit()
    await test_db.rollback()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_verse_requires_valid_book_id(test_db, sample_translation):
    """Verse with invalid book_id violates FK constraint."""
    from tests.conftest import Verse

    v = Verse(
        id=str(uuid.uuid4()),
        translation_id=sample_translation.id,
        book_id=str(uuid.uuid4()),  # nonexistent
        chapter=1,
        verse=1,
        text="Test",
    )
    test_db.add(v)
    with pytest.raises(Exception):
        await test_db.commit()
    await test_db.rollback()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cross_reference_roundtrip(test_db, sample_verse, sample_translation, sample_nt_book):
    """CrossReference model can be created and queried."""
    from tests.conftest import Verse, CrossReference

    related = Verse(
        id=str(uuid.uuid4()),
        translation_id=sample_translation.id,
        book_id=sample_nt_book.id,
        chapter=1,
        verse=1,
        text="Related verse",
    )
    test_db.add(related)
    await test_db.flush()

    cr = CrossReference(
        id=str(uuid.uuid4()),
        verse_id=sample_verse.id,
        related_verse_id=related.id,
        relationship_type="parallel",
        confidence=0.9,
    )
    test_db.add(cr)
    await test_db.commit()

    result = (await test_db.execute(
        select(CrossReference).where(CrossReference.verse_id == sample_verse.id)
    )).scalar_one()
    assert result.relationship_type == "parallel"
    assert result.confidence == 0.9


@pytest.mark.asyncio
@pytest.mark.unit
async def test_original_word_roundtrip(test_db, sample_verse):
    """OriginalWord model can be created and queried."""
    from tests.conftest import OriginalWord

    w = OriginalWord(
        id=str(uuid.uuid4()),
        verse_id=sample_verse.id,
        word="ἀγάπη",
        language="greek",
        strongs_number="G26",
        transliteration="agape",
        definition="love",
        word_order=1,
    )
    test_db.add(w)
    await test_db.commit()

    result = (await test_db.execute(
        select(OriginalWord).where(OriginalWord.strongs_number == "G26")
    )).scalar_one()
    assert result.word == "ἀγάπη"
    assert result.transliteration == "agape"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_translation_abbreviation_unique(test_db):
    """Translation abbreviation must be unique."""
    from tests.conftest import Translation

    t1 = Translation(
        id=str(uuid.uuid4()),
        name="English Standard Version",
        abbreviation="ESV",
        language_code="en",
    )
    t2 = Translation(
        id=str(uuid.uuid4()),
        name="Another ESV",
        abbreviation="ESV",  # duplicate
        language_code="en",
    )
    test_db.add(t1)
    await test_db.commit()
    test_db.add(t2)
    with pytest.raises(Exception):
        await test_db.commit()
    await test_db.rollback()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_embedding_roundtrip(test_db, sample_verse):
    """Embedding model can be created and queried."""
    from tests.conftest import Embedding

    emb = Embedding(
        id=str(uuid.uuid4()),
        verse_id=sample_verse.id,
        vector="[0.1, 0.2, 0.3]",
        model_version="test-model",
    )
    test_db.add(emb)
    await test_db.commit()

    result = (await test_db.execute(
        select(Embedding).where(Embedding.verse_id == sample_verse.id)
    )).scalar_one()
    assert result.model_version == "test-model"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_db_yields_session(test_db):
    """get_db dependency yields an AsyncSession."""
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(test_db, AsyncSession)
