"""Verses API router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import StrongsSearchResponse, StrongsVerse, VerseDetailResponse, VerseReference
from search import get_verse_by_reference, get_chapter_by_reference

router = APIRouter(prefix="/api", tags=["verses"])


@router.get("/verse/{book}/{chapter}/{verse}", response_model=VerseDetailResponse)
async def get_verse(
    book: str,
    chapter: int,
    verse: int,
    translations: Optional[str] = Query(
        None,
        description="Comma-separated translation abbreviations",
    ),
    include_original: bool = Query(
        False,
        description="Include original language data",
    ),
    include_cross_refs: bool = Query(
        True,
        description="Include cross-references",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific verse by reference.

    Retrieve a verse in multiple translations with optional original
    language data and cross-references.

    Args:
        book: Book name or abbreviation (e.g., 'John', '요한복음', 'John')
        chapter: Chapter number
        verse: Verse number
        translations: Comma-separated translation abbreviations
        include_original: Include Greek/Hebrew data
        include_cross_refs: Include cross-references

    Returns:
        Verse data with translations and optional enrichments
    """
    # Parse translations
    translation_list = None
    if translations:
        translation_list = [t.strip() for t in translations.split(",")]

    result = await get_verse_by_reference(
        db=db,
        book=book,
        chapter=chapter,
        verse=verse,
        translations=translation_list,
        include_original=include_original,
        include_cross_refs=include_cross_refs,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "VERSE_NOT_FOUND",
                "message": "Verse not found",
                "details": {
                    "book": book,
                    "chapter": chapter,
                    "verse": verse,
                },
            },
        )

    return VerseDetailResponse(**result)


@router.get("/chapter/{book}/{chapter}")
async def get_chapter(
    book: str,
    chapter: int,
    translations: Optional[str] = Query(
        None,
        description="Comma-separated translation abbreviations",
    ),
    include_original: bool = Query(
        False,
        description="Include original language data",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get an entire chapter with all verses.

    Retrieve a complete chapter in multiple translations with optional
    original language data.

    Args:
        book: Book name or abbreviation (e.g., 'John', '요한복음')
        chapter: Chapter number
        translations: Comma-separated translation abbreviations
        include_original: Include Greek/Hebrew data

    Returns:
        Chapter data with all verses
    """
    # Parse translations
    translation_list = None
    if translations:
        translation_list = [t.strip() for t in translations.split(",")]

    result = await get_chapter_by_reference(
        db=db,
        book=book,
        chapter=chapter,
        translations=translation_list,
        include_original=include_original,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CHAPTER_NOT_FOUND",
                "message": "Chapter not found",
                "details": {
                    "book": book,
                    "chapter": chapter,
                },
            },
        )

    return result


@router.get("/strongs/{strongs_number}", response_model=StrongsSearchResponse)
async def get_strongs_verses(
    strongs_number: str,
    translations: Optional[str] = Query(
        None,
        description="Comma-separated translation abbreviations (e.g. 'NIV,KRV'). Defaults to all non-original translations.",
    ),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of verses to return"),
    db: AsyncSession = Depends(get_db),
):
    """Look up all Bible verses that contain a specific Strong's concordance number.

    Returns the word definition, language, and a list of matching verses.

    Args:
        strongs_number: Strong's number, e.g. 'G25' (Greek) or 'H157' (Hebrew)
        translations: Comma-separated translation abbreviations
        limit: Maximum number of verses to return (1-50)
    """
    translation_list = [t.strip() for t in translations.split(",")] if translations else None

    # Normalise strongs_number (uppercase prefix, e.g. g25 → G25)
    strongs_upper = strongs_number.upper()

    # 1. Fetch word metadata (definition, language, transliteration) from any matching row
    meta_sql = text("""
        SELECT language, definition, transliteration
        FROM original_words
        WHERE UPPER(strongs_number) = :sn
        ORDER BY definition NULLS LAST
        LIMIT 1
    """)
    meta_result = await db.execute(meta_sql, {"sn": strongs_upper})
    meta_row = meta_result.fetchone()

    if meta_row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "STRONGS_NOT_FOUND",
                "message": f"No verses found for Strong's number {strongs_number}",
            },
        )

    language = meta_row.language
    definition = meta_row.definition
    transliteration = meta_row.transliteration

    # 2. Count total distinct verses that contain this Strong's number
    count_sql = text("""
        SELECT COUNT(DISTINCT ow.verse_id) AS total
        FROM original_words ow
        WHERE UPPER(ow.strongs_number) = :sn
    """)
    count_result = await db.execute(count_sql, {"sn": strongs_upper})
    total_count = count_result.scalar() or 0

    # 3. Fetch verses with translations
    if translation_list:
        verses_sql = text("""
            SELECT DISTINCT ON (b.book_number, v.chapter, v.verse, t.abbreviation)
                b.name        AS book,
                b.name_korean AS book_korean,
                b.testament,
                b.genre,
                v.chapter,
                v.verse,
                t.abbreviation AS translation,
                v.text
            FROM original_words ow
            JOIN verses v        ON v.id = ow.verse_id
            JOIN books b         ON b.id = v.book_id
            JOIN translations t  ON t.id = v.translation_id
            WHERE UPPER(ow.strongs_number) = :sn
              AND t.abbreviation = ANY(:translations)
              AND t.is_original_language = FALSE
            ORDER BY b.book_number, v.chapter, v.verse, t.abbreviation
            LIMIT :limit
        """)
        rows = (await db.execute(verses_sql, {
            "sn": strongs_upper,
            "translations": translation_list,
            "limit": limit,
        })).fetchall()
    else:
        verses_sql = text("""
            SELECT DISTINCT ON (b.book_number, v.chapter, v.verse, t.abbreviation)
                b.name        AS book,
                b.name_korean AS book_korean,
                b.testament,
                b.genre,
                v.chapter,
                v.verse,
                t.abbreviation AS translation,
                v.text
            FROM original_words ow
            JOIN verses v        ON v.id = ow.verse_id
            JOIN books b         ON b.id = v.book_id
            JOIN translations t  ON t.id = v.translation_id
            WHERE UPPER(ow.strongs_number) = :sn
              AND t.is_original_language = FALSE
            ORDER BY b.book_number, v.chapter, v.verse, t.abbreviation
            LIMIT :limit
        """)
        rows = (await db.execute(verses_sql, {"sn": strongs_upper, "limit": limit})).fetchall()

    # 4. Group translations per verse reference
    verse_map: dict[tuple, StrongsVerse] = {}
    for row in rows:
        key = (row.book, row.chapter, row.verse)
        if key not in verse_map:
            verse_map[key] = StrongsVerse(
                reference=VerseReference(
                    book=row.book,
                    book_korean=row.book_korean,
                    chapter=row.chapter,
                    verse=row.verse,
                    testament=row.testament,
                    genre=row.genre,
                ),
                translations={},
            )
        verse_map[key].translations[row.translation] = row.text

    return StrongsSearchResponse(
        strongs_number=strongs_upper,
        language=language,
        definition=definition,
        transliteration=transliteration,
        total_count=total_count,
        verses=list(verse_map.values()),
    )
