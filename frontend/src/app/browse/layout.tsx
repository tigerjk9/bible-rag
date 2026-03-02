import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Browse Bible — Bible RAG',
  description: 'Read and explore the Bible chapter by chapter in English and Korean translations with original language analysis.',
};

export default function BrowseLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
