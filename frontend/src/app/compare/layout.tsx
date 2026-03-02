import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Compare Translations — Bible RAG',
  description: 'Compare Bible translations side-by-side with original Greek and Hebrew text, Strong\'s numbers, and Korean translations.',
};

export default function CompareLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
