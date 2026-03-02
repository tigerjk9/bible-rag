import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Thematic Search — Bible RAG',
  description: 'Explore biblical themes like love, faith, and forgiveness across Old and New Testaments in English and Korean.',
};

export default function ThemesLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
