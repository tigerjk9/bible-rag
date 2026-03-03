/**
 * Utility to parse biblical verse references from text and render them as clickable links.
 * Handles English (full names + abbreviations) and Korean book names.
 */

import React from 'react';
import Link from 'next/link';

// Maps lowercase book name variants → canonical English name used in verse URLs
const BOOK_NAME_MAP: Record<string, string> = {
  // Genesis
  'genesis': 'Genesis', 'gen': 'Genesis', '창세기': 'Genesis',
  // Exodus
  'exodus': 'Exodus', 'exod': 'Exodus', 'exo': 'Exodus', '출애굽기': 'Exodus',
  // Leviticus
  'leviticus': 'Leviticus', 'lev': 'Leviticus', '레위기': 'Leviticus',
  // Numbers
  'numbers': 'Numbers', 'num': 'Numbers', '민수기': 'Numbers',
  // Deuteronomy
  'deuteronomy': 'Deuteronomy', 'deut': 'Deuteronomy', 'deu': 'Deuteronomy', '신명기': 'Deuteronomy',
  // Joshua
  'joshua': 'Joshua', 'josh': 'Joshua', '여호수아': 'Joshua',
  // Judges
  'judges': 'Judges', 'judg': 'Judges', '사사기': 'Judges',
  // Ruth
  'ruth': 'Ruth', '룻기': 'Ruth',
  // 1 Samuel
  '1 samuel': '1 Samuel', '1sam': '1 Samuel', '1sa': '1 Samuel', '사무엘상': '1 Samuel',
  // 2 Samuel
  '2 samuel': '2 Samuel', '2sam': '2 Samuel', '2sa': '2 Samuel', '사무엘하': '2 Samuel',
  // 1 Kings
  '1 kings': '1 Kings', '1kgs': '1 Kings', '1ki': '1 Kings', '열왕기상': '1 Kings',
  // 2 Kings
  '2 kings': '2 Kings', '2kgs': '2 Kings', '2ki': '2 Kings', '열왕기하': '2 Kings',
  // 1 Chronicles
  '1 chronicles': '1 Chronicles', '1chr': '1 Chronicles', '1ch': '1 Chronicles', '역대상': '1 Chronicles',
  // 2 Chronicles
  '2 chronicles': '2 Chronicles', '2chr': '2 Chronicles', '2ch': '2 Chronicles', '역대하': '2 Chronicles',
  // Ezra
  'ezra': 'Ezra', '에스라': 'Ezra',
  // Nehemiah
  'nehemiah': 'Nehemiah', 'neh': 'Nehemiah', '느헤미야': 'Nehemiah',
  // Esther
  'esther': 'Esther', 'esth': 'Esther', '에스더': 'Esther',
  // Job
  'job': 'Job', '욥기': 'Job',
  // Psalms
  'psalms': 'Psalms', 'psalm': 'Psalms', 'ps': 'Psalms', '시편': 'Psalms',
  // Proverbs
  'proverbs': 'Proverbs', 'prov': 'Proverbs', 'pro': 'Proverbs', '잠언': 'Proverbs',
  // Ecclesiastes
  'ecclesiastes': 'Ecclesiastes', 'eccl': 'Ecclesiastes', 'ecc': 'Ecclesiastes', '전도서': 'Ecclesiastes',
  // Song of Solomon
  'song of solomon': 'Song of Solomon', 'song of songs': 'Song of Solomon',
  'sos': 'Song of Solomon', 'song': 'Song of Solomon', '아가': 'Song of Solomon',
  // Isaiah
  'isaiah': 'Isaiah', 'isa': 'Isaiah', '이사야': 'Isaiah',
  // Jeremiah
  'jeremiah': 'Jeremiah', 'jer': 'Jeremiah', '예레미야': 'Jeremiah',
  // Lamentations
  'lamentations': 'Lamentations', 'lam': 'Lamentations', '예레미야애가': 'Lamentations',
  // Ezekiel
  'ezekiel': 'Ezekiel', 'ezek': 'Ezekiel', 'eze': 'Ezekiel', '에스겔': 'Ezekiel',
  // Daniel
  'daniel': 'Daniel', 'dan': 'Daniel', '다니엘': 'Daniel',
  // Hosea
  'hosea': 'Hosea', 'hos': 'Hosea', '호세아': 'Hosea',
  // Joel
  'joel': 'Joel', '요엘': 'Joel',
  // Amos
  'amos': 'Amos', '아모스': 'Amos',
  // Obadiah
  'obadiah': 'Obadiah', 'obad': 'Obadiah', '오바댜': 'Obadiah',
  // Jonah
  'jonah': 'Jonah', 'jon': 'Jonah', '요나': 'Jonah',
  // Micah
  'micah': 'Micah', 'mic': 'Micah', '미가': 'Micah',
  // Nahum
  'nahum': 'Nahum', 'nah': 'Nahum', '나훔': 'Nahum',
  // Habakkuk
  'habakkuk': 'Habakkuk', 'hab': 'Habakkuk', '하박국': 'Habakkuk',
  // Zephaniah
  'zephaniah': 'Zephaniah', 'zeph': 'Zephaniah', '스바냐': 'Zephaniah',
  // Haggai
  'haggai': 'Haggai', 'hag': 'Haggai', '학개': 'Haggai',
  // Zechariah
  'zechariah': 'Zechariah', 'zech': 'Zechariah', '스가랴': 'Zechariah',
  // Malachi
  'malachi': 'Malachi', 'mal': 'Malachi', '말라기': 'Malachi',
  // Matthew
  'matthew': 'Matthew', 'matt': 'Matthew', 'mat': 'Matthew', '마태복음': 'Matthew',
  // Mark
  'mark': 'Mark', 'mrk': 'Mark', '마가복음': 'Mark',
  // Luke
  'luke': 'Luke', 'luk': 'Luke', '누가복음': 'Luke',
  // John
  'john': 'John', 'jn': 'John', '요한복음': 'John',
  // Acts
  'acts': 'Acts', '사도행전': 'Acts',
  // Romans
  'romans': 'Romans', 'rom': 'Romans', '로마서': 'Romans',
  // 1 Corinthians
  '1 corinthians': '1 Corinthians', '1cor': '1 Corinthians', '고린도전서': '1 Corinthians',
  // 2 Corinthians
  '2 corinthians': '2 Corinthians', '2cor': '2 Corinthians', '고린도후서': '2 Corinthians',
  // Galatians
  'galatians': 'Galatians', 'gal': 'Galatians', '갈라디아서': 'Galatians',
  // Ephesians
  'ephesians': 'Ephesians', 'eph': 'Ephesians', '에베소서': 'Ephesians',
  // Philippians
  'philippians': 'Philippians', 'phil': 'Philippians', '빌립보서': 'Philippians',
  // Colossians
  'colossians': 'Colossians', 'col': 'Colossians', '골로새서': 'Colossians',
  // 1 Thessalonians
  '1 thessalonians': '1 Thessalonians', '1thes': '1 Thessalonians', '1thess': '1 Thessalonians', '데살로니가전서': '1 Thessalonians',
  // 2 Thessalonians
  '2 thessalonians': '2 Thessalonians', '2thes': '2 Thessalonians', '2thess': '2 Thessalonians', '데살로니가후서': '2 Thessalonians',
  // 1 Timothy
  '1 timothy': '1 Timothy', '1tim': '1 Timothy', '디모데전서': '1 Timothy',
  // 2 Timothy
  '2 timothy': '2 Timothy', '2tim': '2 Timothy', '디모데후서': '2 Timothy',
  // Titus
  'titus': 'Titus', 'tit': 'Titus', '디도서': 'Titus',
  // Philemon
  'philemon': 'Philemon', 'phlm': 'Philemon', '빌레몬서': 'Philemon',
  // Hebrews
  'hebrews': 'Hebrews', 'heb': 'Hebrews', '히브리서': 'Hebrews',
  // James
  'james': 'James', 'jas': 'James', '야고보서': 'James',
  // 1 Peter
  '1 peter': '1 Peter', '1pet': '1 Peter', '베드로전서': '1 Peter',
  // 2 Peter
  '2 peter': '2 Peter', '2pet': '2 Peter', '베드로후서': '2 Peter',
  // 1 John
  '1 john': '1 John', '1jn': '1 John', '요한일서': '1 John',
  // 2 John
  '2 john': '2 John', '2jn': '2 John', '요한이서': '2 John',
  // 3 John
  '3 john': '3 John', '3jn': '3 John', '요한삼서': '3 John',
  // Jude
  'jude': 'Jude', '유다서': 'Jude',
  // Revelation
  'revelation': 'Revelation', 'rev': 'Revelation', '요한계시록': 'Revelation',
};

// Build regex alternation sorted by length (longest first) to prevent prefix issues
const _sortedVariants = Object.keys(BOOK_NAME_MAP).sort((a, b) => b.length - a.length);
const _escapedVariants = _sortedVariants.map((v) =>
  v.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
);
// Matches: <book name> <chapter>:<verse> with optional range (-\d+)
// Uses lookahead/lookbehind to avoid matching in mid-word for short abbreviations
const VERSE_REF_REGEX = new RegExp(
  `(?<![A-Za-z가-힣])(${_escapedVariants.join('|')})(?![A-Za-z가-힣])\\s+(\\d+):(\\d+)(?:-\\d+)?`,
  'gi'
);

interface ParsedSegment {
  type: 'text' | 'ref';
  content: string;
  book?: string;
  chapter?: number;
  verse?: number;
}

function parseSegments(text: string): ParsedSegment[] {
  const segments: ParsedSegment[] = [];
  let lastIndex = 0;
  const regex = new RegExp(VERSE_REF_REGEX.source, VERSE_REF_REGEX.flags);

  let match: RegExpExecArray | null;
  while ((match = regex.exec(text)) !== null) {
    // Text before this match
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }

    const bookVariant = match[1].toLowerCase();
    const canonicalBook = BOOK_NAME_MAP[bookVariant];
    if (canonicalBook) {
      segments.push({
        type: 'ref',
        content: match[0],
        book: canonicalBook,
        chapter: parseInt(match[2], 10),
        verse: parseInt(match[3], 10),
      });
    } else {
      // Unknown book variant — treat as plain text
      segments.push({ type: 'text', content: match[0] });
    }

    lastIndex = match.index + match[0].length;
  }

  // Remaining text after last match
  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) });
  }

  return segments;
}

/**
 * Parse AI-generated text and replace verse references with clickable links.
 * Only call this on completed text (not while streaming).
 */
export function parseVerseText(text: string): React.ReactNode {
  const segments = parseSegments(text);

  if (segments.every((s) => s.type === 'text')) {
    return text;
  }

  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === 'ref' && seg.book && seg.chapter && seg.verse) {
          const href = `/verse/${encodeURIComponent(seg.book)}/${seg.chapter}/${seg.verse}`;
          return (
            <Link
              key={i}
              href={href}
              className="verse-ref dark:text-accent-dark-reference dark:hover:border-accent-dark-reference"
            >
              {seg.content}
            </Link>
          );
        }
        return <React.Fragment key={i}>{seg.content}</React.Fragment>;
      })}
    </>
  );
}
