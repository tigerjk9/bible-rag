'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { SearchResult, ChapterResponse } from '@/types';
import { getChapter } from '@/lib/api';
import ParallelView from '@/components/ParallelView';
import OriginalLanguage from '@/components/OriginalLanguage';
import ChapterView from '@/components/ChapterView';

interface VerseCardProps {
  result: SearchResult;
  showAllTranslations?: boolean;
  defaultTranslation?: string;
}

interface ContextVerse {
  verse: number;
  chapter: number;
  text: string;
}

// Relationship type display config
const REL_CONFIG: Record<string, { label: string; className: string }> = {
  quotation:  { label: 'Quotation',  className: 'text-accent-scripture dark:text-accent-dark-scripture' },
  parallel:   { label: 'Parallel',   className: 'text-emerald-600 dark:text-emerald-400' },
  allusion:   { label: 'Allusion',   className: 'text-amber-600 dark:text-amber-400' },
  thematic:   { label: 'Thematic',   className: 'text-purple-600 dark:text-purple-400' },
};

function confidenceLabel(confidence?: number): string | null {
  if (confidence === undefined || confidence === null || confidence >= 0.7) return null;
  return confidence >= 0.5 ? '· probable' : '· possible';
}

export default function VerseCard({ result, showAllTranslations = false, defaultTranslation }: VerseCardProps) {
  const initialTranslation =
    defaultTranslation && result.translations[defaultTranslation]
      ? defaultTranslation
      : Object.keys(result.translations)[0] || '';

  const [activeTranslation, setActiveTranslation] = useState<string>(initialTranslation);
  const [showCrossRefs, setShowCrossRefs] = useState(false);
  const [contextBefore, setContextBefore] = useState<ContextVerse[] | null>(null);
  const [contextAfter, setContextAfter] = useState<ContextVerse[] | null>(null);
  const [showContext, setShowContext] = useState(false);
  const [loadingContext, setLoadingContext] = useState(false);

  // New: verse study panel states
  const [showParallel, setShowParallel] = useState(false);
  const [showOriginalLang, setShowOriginalLang] = useState(false);
  const [showChapterModal, setShowChapterModal] = useState(false);
  const [chapterData, setChapterData] = useState<ChapterResponse | null>(null);
  const [loadingChapter, setLoadingChapter] = useState(false);

  const modalRef = useRef<HTMLDivElement>(null);

  const { reference, translations, relevance_score, cross_references, original } = result;

  const relevancePercent = Math.round(relevance_score * 100);
  const isKorean = (text: string) => /[\uac00-\ud7a3]/.test(text);
  const verseUrl = `/verse/${encodeURIComponent(reference.book)}/${reference.chapter}/${reference.verse}`;
  const translationCount = Object.keys(translations).length;

  // Group cross-references by relationship type
  const groupedRefs = cross_references?.reduce<Record<string, typeof cross_references>>((acc, ref) => {
    const rel = ref.relationship || 'thematic';
    if (!acc[rel]) acc[rel] = [];
    acc[rel].push(ref);
    return acc;
  }, {});

  // Convert translations Record to ParallelView format
  const parallelTranslations = Object.entries(translations).map(([abbreviation, text]) => ({
    abbreviation,
    text,
    language: isKorean(text) ? 'ko' : 'en',
  }));

  async function handleLoadContext() {
    if (contextBefore !== null) {
      setShowContext(!showContext);
      return;
    }

    setLoadingContext(true);
    try {
      const translation = activeTranslation || defaultTranslation;
      const chapterResult = await getChapter(
        reference.book,
        reference.chapter,
        translation ? [translation] : undefined,
      );

      const verses: { verse: number; translations: Record<string, string> }[] =
        chapterResult?.verses ?? [];

      const targetIdx = verses.findIndex((v) => v.verse === reference.verse);
      const translationKey = translation || Object.keys(verses[0]?.translations ?? {})[0] || '';

      const before: ContextVerse[] = [];
      const after: ContextVerse[] = [];

      for (let i = Math.max(0, targetIdx - 2); i < targetIdx; i++) {
        const v = verses[i];
        if (v) before.push({ verse: v.verse, chapter: reference.chapter, text: v.translations[translationKey] ?? '' });
      }
      for (let i = targetIdx + 1; i <= Math.min(verses.length - 1, targetIdx + 2); i++) {
        const v = verses[i];
        if (v) after.push({ verse: v.verse, chapter: reference.chapter, text: v.translations[translationKey] ?? '' });
      }

      setContextBefore(before);
      setContextAfter(after);
      setShowContext(true);
    } catch {
      // Silently fail — context is non-critical
    } finally {
      setLoadingContext(false);
    }
  }

  async function handleOpenChapter() {
    if (showChapterModal) {
      setShowChapterModal(false);
      return;
    }

    setShowChapterModal(true);

    if (!chapterData) {
      setLoadingChapter(true);
      try {
        const data = await getChapter(
          reference.book,
          reference.chapter,
          Object.keys(translations),
        );
        setChapterData(data);
      } catch {
        // Silently fail
      } finally {
        setLoadingChapter(false);
      }
    }
  }

  // Scroll to highlighted verse after chapter data loads and modal opens
  useEffect(() => {
    if (showChapterModal && chapterData && !loadingChapter) {
      const el = modalRef.current?.querySelector(`#verse-${reference.verse}`);
      if (el) {
        setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
      }
    }
  }, [showChapterModal, chapterData, loadingChapter, reference.verse]);

  // Close modal on Escape key
  useEffect(() => {
    if (!showChapterModal) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowChapterModal(false);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [showChapterModal]);

  return (
    <div className="verse-card">
      {/* Reference as large typographic element */}
      <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between mb-space-sm gap-2">
        <div className="flex items-baseline gap-2">
          <Link href={verseUrl} className="group flex items-baseline gap-2">
            <span className="font-ui text-xs sm:text-sm uppercase tracking-wide text-accent-scripture dark:text-accent-dark-scripture hover:text-text-primary dark:hover:text-text-dark-primary transition-colors">
              {reference.book}
            </span>
            <span className="font-serif text-2xl sm:text-3xl md:text-4xl font-light text-accent-scripture dark:text-accent-dark-scripture group-hover:text-text-primary dark:group-hover:text-text-dark-primary transition-colors">
              {reference.chapter}:{reference.verse}
            </span>
          </Link>
        </div>

        {/* Testament and relevance */}
        <div className="flex sm:flex-col items-center sm:items-end gap-2 sm:gap-1">
          <span className="font-ui text-xs uppercase tracking-wide text-text-tertiary dark:text-text-dark-tertiary">
            {reference.testament === 'OT' ? 'OT' : 'NT'}
          </span>
          <span className="font-ui text-xs text-text-secondary dark:text-text-dark-secondary">
            <span className="hidden sm:inline">Relevance: </span><span className="font-medium">{relevancePercent}%</span>
          </span>
        </div>
      </div>

      {/* Korean reference */}
      {reference.book_korean && (
        <Link href={verseUrl}>
          <p className="font-korean text-sm text-text-secondary dark:text-text-dark-secondary mb-space-md hover:text-text-primary dark:hover:text-text-dark-primary transition-colors">
            {reference.book_korean} {reference.chapter}:{reference.verse}
          </p>
        </Link>
      )}

      {/* Translation selector — hidden when Compare mode is active */}
      {!showParallel && Object.keys(translations).length > 1 && !showAllTranslations && (
        <div className="flex gap-4 mb-space-sm border-b border-border-light dark:border-border-dark-light pb-2">
          {Object.keys(translations).map((trans) => (
            <button
              key={trans}
              onClick={() => setActiveTranslation(trans)}
              className={`translation-tab dark:text-text-dark-tertiary dark:hover:text-text-dark-primary dark:border-transparent ${
                activeTranslation === trans ? 'translation-tab-active dark:text-text-dark-primary dark:border-text-dark-primary' : ''
              }`}
            >
              {trans}
            </button>
          ))}
        </div>
      )}

      {/* Verse text — ParallelView when Compare active, else single/all */}
      {showParallel ? (
        <div className="mb-space-sm">
          <ParallelView
            reference={{
              book: reference.book,
              book_korean: reference.book_korean,
              chapter: reference.chapter,
              verse: reference.verse,
            }}
            translations={parallelTranslations}
            layout="vertical"
          />
        </div>
      ) : showAllTranslations ? (
        <div className="space-y-space-md">
          {Object.entries(translations).map(([trans, text]) => (
            <div key={trans} className="border-l-4 border-border-light dark:border-border-dark-light pl-space-md">
              <span className="font-ui text-xs uppercase tracking-wide text-text-tertiary dark:text-text-dark-tertiary block mb-2">
                {trans}
              </span>
              <p className={`${isKorean(text) ? 'verse-text-korean korean-text dark:text-text-dark-primary' : 'verse-text dark:text-text-dark-primary'}`}>
                {text}
              </p>
            </div>
          ))}
        </div>
      ) : showContext && (contextBefore?.length || contextAfter?.length) ? (
        <div className="space-y-1 mb-space-sm">
          {(contextBefore ?? []).map((cv) => (
            <p key={cv.verse} className={`${isKorean(cv.text) ? 'verse-text-korean korean-text' : 'verse-text'} text-sm dark:text-text-dark-secondary`}>
              <span className="font-ui text-xs text-text-tertiary dark:text-text-dark-tertiary mr-2 select-none">
                {cv.chapter}:{cv.verse}
              </span>
              {cv.text}
            </p>
          ))}
          <p className={`${
              isKorean(translations[activeTranslation] || '')
                ? 'verse-text-korean korean-text dark:text-text-dark-primary'
                : 'verse-text dark:text-text-dark-primary'
            }`}
          >
            <span className="font-ui text-xs text-text-tertiary dark:text-text-dark-tertiary mr-2 select-none">
              {reference.chapter}:{reference.verse}
            </span>
            {translations[activeTranslation]}
          </p>
          {(contextAfter ?? []).map((cv) => (
            <p key={cv.verse} className={`${isKorean(cv.text) ? 'verse-text-korean korean-text' : 'verse-text'} text-sm dark:text-text-dark-secondary`}>
              <span className="font-ui text-xs text-text-tertiary dark:text-text-dark-tertiary mr-2 select-none">
                {cv.chapter}:{cv.verse}
              </span>
              {cv.text}
            </p>
          ))}
        </div>
      ) : (
        <p className={`${
            isKorean(translations[activeTranslation] || '')
              ? 'verse-text-korean korean-text dark:text-text-dark-primary'
              : 'verse-text dark:text-text-dark-primary'
          } mb-space-sm`}
        >
          {translations[activeTranslation]}
        </p>
      )}

      {/* Inline Original Language (word-level Strong's interlinear) */}
      {showOriginalLang && original && (
        <div className="mt-space-sm pt-space-sm border-t border-border-light dark:border-border-dark-light">
          <OriginalLanguage
            language={original.language as 'greek' | 'hebrew' | 'aramaic'}
            text={original.words?.map(w => w.word).join(' ') || ''}
            transliteration={original.words?.map(w => w.transliteration).filter(Boolean).join(' ')}
            words={original.words}
            strongs={original.words?.map(w => w.strongs).filter(Boolean) as string[]}
            showInterlinear={true}
          />
        </div>
      )}

      {/* Action bar */}
      <div className="mt-space-md pt-space-md border-t border-border-light dark:border-border-dark-light flex flex-wrap items-center gap-x-4 gap-y-1">
        <button
          onClick={handleLoadContext}
          disabled={loadingContext}
          className="btn-text dark:text-text-dark-secondary dark:hover:text-text-dark-primary dark:border-text-dark-tertiary dark:hover:border-text-dark-primary text-xs"
        >
          {loadingContext ? 'Loading…' : showContext ? '▴ Hide context' : '± Context'}
        </button>

        {translationCount > 1 && (
          <button
            onClick={() => setShowParallel(!showParallel)}
            className={`btn-text text-xs ${
              showParallel
                ? 'text-accent-scripture dark:text-accent-dark-scripture border-accent-scripture dark:border-accent-dark-scripture'
                : 'dark:text-text-dark-secondary dark:hover:text-text-dark-primary dark:border-text-dark-tertiary dark:hover:border-text-dark-primary'
            }`}
          >
            ⧉ Compare
          </button>
        )}

        <button
          onClick={handleOpenChapter}
          className={`btn-text text-xs ${
            showChapterModal
              ? 'text-accent-scripture dark:text-accent-dark-scripture border-accent-scripture dark:border-accent-dark-scripture'
              : 'dark:text-text-dark-secondary dark:hover:text-text-dark-primary dark:border-text-dark-tertiary dark:hover:border-text-dark-primary'
          }`}
        >
          ≡ Chapter
        </button>

        {original && original.words && original.words.length > 0 && (
          <button
            onClick={() => setShowOriginalLang(!showOriginalLang)}
            className={`btn-text text-xs ${
              showOriginalLang
                ? 'text-accent-scripture dark:text-accent-dark-scripture border-accent-scripture dark:border-accent-dark-scripture'
                : 'dark:text-text-dark-secondary dark:hover:text-text-dark-primary dark:border-text-dark-tertiary dark:hover:border-text-dark-primary'
            }`}
          >
            ΑΩ {original.language === 'hebrew' ? 'Hebrew' : 'Greek'}
          </button>
        )}

        {cross_references && cross_references.length > 0 && (
          <button
            onClick={() => setShowCrossRefs(!showCrossRefs)}
            className="btn-text dark:text-text-dark-secondary dark:hover:text-text-dark-primary dark:border-text-dark-tertiary dark:hover:border-text-dark-primary text-xs"
          >
            {showCrossRefs ? '▾' : '▸'} See also ({cross_references.length})
          </button>
        )}
      </div>

      {/* Cross-references: grouped by relationship type with confidence labels */}
      {showCrossRefs && groupedRefs && (
        <div className="mt-2 space-y-2">
          {Object.entries(groupedRefs).map(([rel, refs]) => {
            const config = REL_CONFIG[rel] ?? { label: rel, className: 'text-text-tertiary dark:text-text-dark-tertiary' };
            return (
              <div key={rel}>
                <span className={`font-ui text-[10px] uppercase tracking-wide ${config.className} mr-2`}>
                  {config.label}
                </span>
                <span className="inline-flex flex-wrap gap-x-3 gap-y-1">
                  {refs.map((ref) => {
                    const crossRefUrl = `/verse/${encodeURIComponent(ref.book)}/${ref.chapter}/${ref.verse}`;
                    const confLabel = confidenceLabel(ref.confidence);
                    return (
                      <span key={`${ref.book}-${ref.chapter}-${ref.verse}`} className="inline-flex items-baseline gap-1">
                        <Link
                          href={crossRefUrl}
                          className="verse-ref dark:text-accent-dark-reference dark:hover:border-accent-dark-reference"
                        >
                          {ref.book} {ref.chapter}:{ref.verse}
                        </Link>
                        {confLabel && (
                          <span className="font-ui text-[10px] text-text-tertiary dark:text-text-dark-tertiary">
                            {confLabel}
                          </span>
                        )}
                      </span>
                    );
                  })}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Chapter Reader Modal */}
      {showChapterModal && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
          aria-modal="true"
          role="dialog"
          aria-label={`${reference.book} chapter ${reference.chapter}`}
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowChapterModal(false)}
          />

          {/* Modal panel */}
          <div
            ref={modalRef}
            className="relative z-10 w-full sm:max-w-2xl lg:max-w-3xl max-h-[85vh] sm:max-h-[80vh] overflow-y-auto bg-surface dark:bg-surface-dark border border-border-light dark:border-border-dark-light shadow-2xl"
          >
            {/* Sticky header */}
            <div className="sticky top-0 z-10 flex items-center justify-between px-space-md py-space-sm bg-surface dark:bg-surface-dark border-b border-border-light dark:border-border-dark-light">
              <span className="font-ui text-sm uppercase tracking-wide text-text-primary dark:text-text-dark-primary">
                {reference.book} {reference.chapter}
                {reference.book_korean && (
                  <span className="font-korean ml-2 text-text-secondary dark:text-text-dark-secondary">
                    {reference.book_korean} {reference.chapter}장
                  </span>
                )}
              </span>
              <button
                onClick={() => setShowChapterModal(false)}
                className="font-ui text-xs uppercase tracking-wide text-text-secondary dark:text-text-dark-secondary hover:text-text-primary dark:hover:text-text-dark-primary transition-colors px-2 py-1"
                aria-label="Close chapter view"
              >
                ✕ Close
              </button>
            </div>

            {/* Content */}
            <div className="p-space-md">
              {loadingChapter ? (
                <div className="flex flex-col items-center py-space-lg gap-3">
                  <div className="spinner" />
                  <p className="font-ui text-sm text-text-secondary dark:text-text-dark-secondary">
                    Loading chapter…
                  </p>
                </div>
              ) : chapterData ? (
                <ChapterView
                  reference={{
                    book: chapterData.reference.book,
                    book_korean: chapterData.reference.book_korean,
                    chapter: chapterData.reference.chapter,
                    testament: chapterData.reference.testament,
                  }}
                  verses={chapterData.verses}
                  selectedTranslation={activeTranslation}
                  showOriginal={false}
                  highlightVerse={reference.verse}
                />
              ) : (
                <p className="font-ui text-sm text-text-tertiary dark:text-text-dark-tertiary text-center py-space-lg">
                  Could not load chapter.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
