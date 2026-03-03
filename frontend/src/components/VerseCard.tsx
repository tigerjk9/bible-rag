'use client';

import { useState } from 'react';
import Link from 'next/link';
import { SearchResult } from '@/types';
import { getChapter } from '@/lib/api';

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

  const { reference, translations, relevance_score, cross_references } = result;

  const relevancePercent = Math.round(relevance_score * 100);
  const isKorean = (text: string) => /[\uac00-\ud7a3]/.test(text);
  const verseUrl = `/verse/${encodeURIComponent(reference.book)}/${reference.chapter}/${reference.verse}`;

  // Group cross-references by relationship type
  const groupedRefs = cross_references?.reduce<Record<string, typeof cross_references>>((acc, ref) => {
    const rel = ref.relationship || 'thematic';
    if (!acc[rel]) acc[rel] = [];
    acc[rel].push(ref);
    return acc;
  }, {});

  async function handleLoadContext() {
    // Toggle off if already loaded
    if (contextBefore !== null) {
      setShowContext(!showContext);
      return;
    }

    setLoadingContext(true);
    try {
      const translation = activeTranslation || defaultTranslation;
      const chapterData = await getChapter(
        reference.book,
        reference.chapter,
        translation ? [translation] : undefined,
      );

      const verses: { verse: number; translations: Record<string, string> }[] =
        chapterData?.verses ?? [];

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

      {/* Translation selector - underlined text tabs */}
      {Object.keys(translations).length > 1 && !showAllTranslations && (
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

      {/* Context: verses before */}
      {showContext && contextBefore && contextBefore.length > 0 && (
        <div className="mb-2 space-y-1 opacity-50">
          {contextBefore.map((cv) => (
            <p key={cv.verse} className={`${isKorean(cv.text) ? 'verse-text-korean korean-text' : 'verse-text'} text-sm dark:text-text-dark-secondary`}>
              <span className="font-ui text-xs text-text-tertiary dark:text-text-dark-tertiary mr-2 select-none">
                {cv.chapter}:{cv.verse}
              </span>
              {cv.text}
            </p>
          ))}
        </div>
      )}

      {/* Verse text - THE HERO */}
      {showAllTranslations ? (
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

      {/* Context: verses after */}
      {showContext && contextAfter && contextAfter.length > 0 && (
        <div className="mt-2 space-y-1 opacity-50">
          {contextAfter.map((cv) => (
            <p key={cv.verse} className={`${isKorean(cv.text) ? 'verse-text-korean korean-text' : 'verse-text'} text-sm dark:text-text-dark-secondary`}>
              <span className="font-ui text-xs text-text-tertiary dark:text-text-dark-tertiary mr-2 select-none">
                {cv.chapter}:{cv.verse}
              </span>
              {cv.text}
            </p>
          ))}
        </div>
      )}

      {/* Context toggle button + cross-refs row */}
      <div className="mt-space-md pt-space-md border-t border-border-light dark:border-border-dark-light flex flex-wrap items-center gap-x-4 gap-y-1">
        <button
          onClick={handleLoadContext}
          disabled={loadingContext}
          className="btn-text dark:text-text-dark-secondary dark:hover:text-text-dark-primary dark:border-text-dark-tertiary dark:hover:border-text-dark-primary text-xs"
        >
          {loadingContext
            ? 'Loading…'
            : showContext
            ? '▴ Hide context'
            : '± Context'}
        </button>

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
    </div>
  );
}
