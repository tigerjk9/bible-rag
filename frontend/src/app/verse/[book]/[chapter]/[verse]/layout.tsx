import type { Metadata } from 'next';

interface Params {
  book: string;
  chapter: string;
  verse: string;
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { book, chapter, verse } = await params;
  const bookName = decodeURIComponent(book);
  const reference = `${bookName} ${chapter}:${verse}`;

  return {
    title: `${reference} — Bible RAG`,
    description: `Read ${reference} in multiple English and Korean Bible translations with original language analysis and cross-references.`,
  };
}

export default function VerseLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
