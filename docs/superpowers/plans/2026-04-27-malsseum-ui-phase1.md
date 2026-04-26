# 말씀의 길 (VERBUM) — Phase 1 구현 플랜

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gemini API 기반 한지 미감 성경 대화 웹앱 MVP — 채팅, 구절 카드, 제안 칩이 동작하는 상태로 Vercel 배포

**Architecture:** Next.js 15 App Router + Next.js API Routes(서버사이드 Gemini 호출) + Bolls.life Bible API. 별도 DB/임베딩 모델 없음. [[VERSE:...]] 태그를 파싱해 인라인 구절 카드로 변환.

**Tech Stack:** Next.js 15, TypeScript, Tailwind CSS 3, `@google/generative-ai`, Vitest, React Testing Library

**⚠️ 새 레포:** 이 앱은 `bible-rag`와 **별개 디렉토리**에 생성합니다.
- 생성 위치: `I:\내 드라이브\Github Desktop\malsseum-ui\`
- 이 플랜 파일은 bible-rag 레포의 기획 산출물로 저장됨

---

## 파일 구조 (Phase 1 완료 시)

```
malsseum-ui/
├── src/
│   ├── app/
│   │   ├── layout.tsx          ← 폰트 로드, HTML 기반
│   │   ├── page.tsx            ← ChatInterface 마운트
│   │   ├── globals.css         ← 한지 디자인 토큰 + 괘선
│   │   └── api/
│   │       ├── chat/route.ts   ← POST: Gemini SSE 스트리밍
│   │       └── verse/route.ts  ← GET: Bolls.life 프록시
│   ├── components/
│   │   ├── ChatInterface.tsx   ← 상태, 스크롤, 패널 조율
│   │   ├── MessageBubble.tsx   ← user / assistant 버블
│   │   ├── VerseCard.tsx       ← 구절 텍스트 + 액션 버튼
│   │   ├── SuggestionChips.tsx ← 다음 단계 칩
│   │   ├── ChatInput.tsx       ← textarea + 전송
│   │   ├── IconSidebar.tsx     ← 데스크탑 좌측 아이콘
│   │   └── TopBar.tsx          ← 앱 이름 + 번역본 선택
│   └── lib/
│       ├── types.ts            ← 공유 타입 정의
│       ├── constants.ts        ← 책 ID 맵, 번역본 코드
│       ├── verse-parser.ts     ← [[VERSE:...]] 추출
│       ├── bible-api.ts        ← Bolls.life fetch 래퍼
│       └── gemini.ts           ← 시스템 프롬프트 + 메시지 변환
├── vitest.config.ts
├── vitest.setup.ts
├── tailwind.config.js
├── next.config.js
├── .env.example
└── .env.local               ← gitignore됨, GEMINI_API_KEY 설정
```

---

## Task 1: 프로젝트 부트스트랩

**Files:**
- Create: `malsseum-ui/` (전체 디렉토리)
- Create: `malsseum-ui/vitest.config.ts`
- Create: `malsseum-ui/vitest.setup.ts`

- [ ] **Step 1: Next.js 앱 생성**

```bash
cd "I:\내 드라이브\Github Desktop"
npx create-next-app@latest malsseum-ui \
  --typescript --tailwind --eslint --app --src-dir \
  --import-alias "@/*" --no-git
cd malsseum-ui
```

프롬프트가 나오면: App Router → Yes, Turbopack → No (Vitest 호환성)

- [ ] **Step 2: 의존성 설치**

```bash
npm install @google/generative-ai
npm install -D vitest @vitejs/plugin-react @testing-library/react \
  @testing-library/jest-dom @testing-library/user-event jsdom
```

- [ ] **Step 3: Vitest 설정**

`vitest.config.ts` 생성:

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
})
```

`vitest.setup.ts` 생성:

```typescript
import '@testing-library/jest-dom'
```

`package.json`의 `scripts`에 추가:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 4: 동작 확인**

```bash
npm run dev
```

`http://localhost:3000` — Next.js 기본 페이지 확인 후 Ctrl+C

- [ ] **Step 5: git 초기화 + 첫 커밋**

```bash
git init
echo "node_modules\n.next\n.env.local" >> .gitignore
git add -A
git commit -m "chore: bootstrap Next.js 15 + vitest"
```

---

## Task 2: 한지 디자인 시스템

**Files:**
- Modify: `src/app/globals.css`
- Modify: `tailwind.config.js`
- Modify: `src/app/layout.tsx`

- [ ] **Step 1: `globals.css` — 한지 디자인 토큰**

`src/app/globals.css`를 아래로 완전 교체:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ── 한지 디자인 토큰 ── */
:root {
  --hanji-cream: #f5ede0;
  --hanji-warm: #ede8e0;
  --ink-dark: #3d2b1f;
  --ink-medium: #7a5c3a;
  --clay: #8b6343;
  --clay-light: rgba(139, 99, 67, 0.12);
  --clay-border: rgba(139, 99, 67, 0.25);
  --paper-white: #ffffff;
  --suggestion-bg: rgba(245, 237, 224, 0.8);

  /* 폰트 */
  --font-serif: 'Noto Serif KR', 'Georgia', serif;
  --font-ui: 'Inter', system-ui, sans-serif;
}

.dark {
  --hanji-cream: #1a1208;
  --hanji-warm: #140f07;
  --ink-dark: #f0e6d3;
  --ink-medium: #c4a882;
  --paper-white: #241a10;
  --clay-border: rgba(139, 99, 67, 0.35);
}

/* ── 기본 ── */
html { scroll-behavior: smooth; }

body {
  background-color: var(--hanji-warm);
  color: var(--ink-dark);
  font-family: var(--font-ui);
  /* 미세 괘선 텍스처 */
  background-image: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 28px,
    rgba(139, 99, 67, 0.05) 28px,
    rgba(139, 99, 67, 0.05) 29px
  );
}

/* ── 구절 텍스트 ── */
.verse-text {
  font-family: var(--font-serif);
  font-size: 1.05rem;
  line-height: 1.9;
  color: var(--ink-dark);
  font-style: italic;
}

.verse-label {
  font-family: var(--font-ui);
  font-size: 0.65rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--clay);
}

/* ── 스크롤바 ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--clay-border);
  border-radius: 2px;
}

/* ── 포커스 링 ── */
*:focus-visible {
  outline: 2px solid var(--clay);
  outline-offset: 2px;
}
```

- [ ] **Step 2: `tailwind.config.js` — 커스텀 색상**

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        hanji: {
          cream: '#f5ede0',
          warm: '#ede8e0',
        },
        ink: {
          dark: '#3d2b1f',
          medium: '#7a5c3a',
        },
        clay: {
          DEFAULT: '#8b6343',
          light: 'rgba(139,99,67,0.12)',
          border: 'rgba(139,99,67,0.25)',
        },
      },
      fontFamily: {
        serif: ['var(--font-noto-serif-kr)', 'Georgia', 'serif'],
        ui: ['var(--font-inter)', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 3: `layout.tsx` — 폰트 로드**

```typescript
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Noto_Serif_KR } from 'next/font/google'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const notoSerifKR = Noto_Serif_KR({
  subsets: ['latin'],
  weight: ['400', '600'],
  variable: '--font-noto-serif-kr',
  display: 'swap',
})

export const metadata: Metadata = {
  title: '말씀의 길',
  description: '성경 속 진리를 대화로 탐구합니다',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className={`${inter.variable} ${notoSerifKR.variable}`}>
      <body>{children}</body>
    </html>
  )
}
```

- [ ] **Step 4: 커밋**

```bash
git add -A
git commit -m "feat: hanji design system (tokens, fonts, texture)"
```

---

## Task 3: 타입 + 상수

**Files:**
- Create: `src/lib/types.ts`
- Create: `src/lib/constants.ts`

- [ ] **Step 1: `src/lib/types.ts` 생성**

```typescript
export type TranslationCode = 'KRV' | 'RNKSV' | 'NIV' | 'ESV' | 'KJV' | 'WEB'

export interface VerseRef {
  book: string        // 영문 책명 e.g. "1John"
  chapter: number
  verse: number
  translation: TranslationCode
}

export interface VerseData {
  ref: VerseRef
  text: string
  bookNameKo: string  // 표시용 한국어 이름 e.g. "요한일서"
}

export type MessageRole = 'user' | 'assistant'

export interface SuggestionChip {
  label: string   // 버튼에 표시할 텍스트
  prompt: string  // 클릭 시 채팅에 입력될 텍스트
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string         // 표시용 텍스트 ([[VERSE:...]] 태그 제거됨)
  rawContent?: string     // Gemini 원본 (태그 포함)
  verses: VerseData[]
  suggestions: SuggestionChip[]
  isStreaming?: boolean
}

export type PanelType = 'none' | 'search' | 'browse' | 'themes' | 'compare' | 'original'

export interface AppState {
  messages: ChatMessage[]
  activePanel: PanelType
  activePanelVerse: VerseRef | null
  translation: TranslationCode
  isLoading: boolean
  error: string | null
}

// API 응답 타입
export interface VerseApiResponse {
  text: string
  bookNameKo: string
  ref: VerseRef
}

// SSE 청크 타입
export type StreamChunk =
  | { type: 'text'; content: string }
  | { type: 'verse_ref'; ref: string }     // "1John:1:9:KRV"
  | { type: 'suggestions'; chips: SuggestionChip[] }
  | { type: 'done' }
  | { type: 'error'; message: string }
```

- [ ] **Step 2: `src/lib/constants.ts` 생성**

```typescript
import type { TranslationCode } from './types'

// Bolls.life 책 ID (1-66)
export const BOOK_IDS: Record<string, number> = {
  Genesis: 1, Exodus: 2, Leviticus: 3, Numbers: 4, Deuteronomy: 5,
  Joshua: 6, Judges: 7, Ruth: 8, '1Samuel': 9, '2Samuel': 10,
  '1Kings': 11, '2Kings': 12, '1Chronicles': 13, '2Chronicles': 14,
  Ezra: 15, Nehemiah: 16, Esther: 17, Job: 18, Psalms: 19,
  Proverbs: 20, Ecclesiastes: 21, SongOfSolomon: 22, Isaiah: 23,
  Jeremiah: 24, Lamentations: 25, Ezekiel: 26, Daniel: 27,
  Hosea: 28, Joel: 29, Amos: 30, Obadiah: 31, Jonah: 32,
  Micah: 33, Nahum: 34, Habakkuk: 35, Zephaniah: 36, Haggai: 37,
  Zechariah: 38, Malachi: 39, Matthew: 40, Mark: 41, Luke: 42,
  John: 43, Acts: 44, Romans: 45, '1Corinthians': 46, '2Corinthians': 47,
  Galatians: 48, Ephesians: 49, Philippians: 50, Colossians: 51,
  '1Thessalonians': 52, '2Thessalonians': 53, '1Timothy': 54, '2Timothy': 55,
  Titus: 56, Philemon: 57, Hebrews: 58, James: 59, '1Peter': 60,
  '2Peter': 61, '1John': 62, '2John': 63, '3John': 64, Jude: 65,
  Revelation: 66,
}

// 한국어 책 이름
export const BOOK_NAMES_KO: Record<string, string> = {
  Genesis: '창세기', Exodus: '출애굽기', Leviticus: '레위기',
  Numbers: '민수기', Deuteronomy: '신명기', Joshua: '여호수아',
  Judges: '사사기', Ruth: '룻기', '1Samuel': '사무엘상', '2Samuel': '사무엘하',
  '1Kings': '열왕기상', '2Kings': '열왕기하', '1Chronicles': '역대상',
  '2Chronicles': '역대하', Ezra: '에스라', Nehemiah: '느헤미야',
  Esther: '에스더', Job: '욥기', Psalms: '시편', Proverbs: '잠언',
  Ecclesiastes: '전도서', SongOfSolomon: '아가', Isaiah: '이사야',
  Jeremiah: '예레미야', Lamentations: '예레미야애가', Ezekiel: '에스겔',
  Daniel: '다니엘', Hosea: '호세아', Joel: '요엘', Amos: '아모스',
  Obadiah: '오바댜', Jonah: '요나', Micah: '미가', Nahum: '나훔',
  Habakkuk: '하박국', Zephaniah: '스바냐', Haggai: '학개',
  Zechariah: '스가랴', Malachi: '말라기', Matthew: '마태복음',
  Mark: '마가복음', Luke: '누가복음', John: '요한복음', Acts: '사도행전',
  Romans: '로마서', '1Corinthians': '고린도전서', '2Corinthians': '고린도후서',
  Galatians: '갈라디아서', Ephesians: '에베소서', Philippians: '빌립보서',
  Colossians: '골로새서', '1Thessalonians': '데살로니가전서',
  '2Thessalonians': '데살로니가후서', '1Timothy': '디모데전서',
  '2Timothy': '디모데후서', Titus: '디도서', Philemon: '빌레몬서',
  Hebrews: '히브리서', James: '야고보서', '1Peter': '베드로전서',
  '2Peter': '베드로후서', '1John': '요한일서', '2John': '요한이서',
  '3John': '요한삼서', Jude: '유다서', Revelation: '요한계시록',
}

// Bolls.life 번역 코드
export const TRANSLATION_LABELS: Record<TranslationCode, string> = {
  KRV: '개역한글',
  RNKSV: '새번역',
  NIV: 'NIV',
  ESV: 'ESV',
  KJV: 'KJV',
  WEB: 'WEB',
}

// Bolls.life가 지원하는 번역본 (KJV, WEB은 GetBible 폴백)
export const BOLLS_TRANSLATIONS: TranslationCode[] = ['KRV', 'RNKSV', 'NIV', 'ESV']
export const GETBIBLE_TRANSLATIONS: TranslationCode[] = ['KJV', 'WEB']

export const DEFAULT_TRANSLATION: TranslationCode = 'KRV'
```

- [ ] **Step 3: 커밋**

```bash
git add src/lib/types.ts src/lib/constants.ts
git commit -m "feat: core types and book constants"
```

---

## Task 4: 구절 파서 (TDD)

**Files:**
- Create: `src/lib/verse-parser.ts`
- Create: `src/lib/__tests__/verse-parser.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

`src/lib/__tests__/verse-parser.test.ts` 생성:

```typescript
import { describe, it, expect } from 'vitest'
import { extractVerseRefs, stripVerseTags } from '../verse-parser'

describe('extractVerseRefs', () => {
  it('단일 태그 추출', () => {
    const text = '이 말씀이 있습니다. [[VERSE:1John:1:9:KRV]] 참 위로가 됩니다.'
    expect(extractVerseRefs(text)).toEqual(['1John:1:9:KRV'])
  })

  it('여러 태그 추출', () => {
    const text = '[[VERSE:John:3:16:KRV]] 그리고 [[VERSE:Romans:8:28:KRV]]'
    expect(extractVerseRefs(text)).toEqual(['John:3:16:KRV', 'Romans:8:28:KRV'])
  })

  it('태그 없으면 빈 배열', () => {
    expect(extractVerseRefs('태그 없는 텍스트입니다.')).toEqual([])
  })

  it('중복 태그는 한 번만', () => {
    const text = '[[VERSE:John:3:16:KRV]] 다시 [[VERSE:John:3:16:KRV]]'
    expect(extractVerseRefs(text)).toEqual(['John:3:16:KRV'])
  })
})

describe('stripVerseTags', () => {
  it('태그 제거 후 공백 정리', () => {
    const text = '말씀이 있습니다. [[VERSE:1John:1:9:KRV]] 위로가 됩니다.'
    expect(stripVerseTags(text)).toBe('말씀이 있습니다.  위로가 됩니다.')
  })

  it('태그 없으면 원본 반환', () => {
    expect(stripVerseTags('원본 텍스트')).toBe('원본 텍스트')
  })
})
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
npm test src/lib/__tests__/verse-parser.test.ts
```

Expected: `Cannot find module '../verse-parser'`

- [ ] **Step 3: 구현**

`src/lib/verse-parser.ts` 생성:

```typescript
const VERSE_TAG_RE = /\[\[VERSE:([^\]]+)\]\]/g

export function extractVerseRefs(text: string): string[] {
  const matches = new Set<string>()
  for (const match of text.matchAll(VERSE_TAG_RE)) {
    matches.add(match[1])
  }
  return Array.from(matches)
}

export function stripVerseTags(text: string): string {
  return text.replace(VERSE_TAG_RE, '')
}

export function parseVerseRefString(ref: string): {
  book: string
  chapter: number
  verse: number
  translation: string
} | null {
  const parts = ref.split(':')
  if (parts.length !== 4) return null
  const [book, chStr, vsStr, translation] = parts
  const chapter = parseInt(chStr, 10)
  const verse = parseInt(vsStr, 10)
  if (isNaN(chapter) || isNaN(verse)) return null
  return { book, chapter, verse, translation }
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npm test src/lib/__tests__/verse-parser.test.ts
```

Expected: `3 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/lib/verse-parser.ts src/lib/__tests__/verse-parser.test.ts
git commit -m "feat: verse tag parser with tests"
```

---

## Task 5: Bible API 클라이언트 (TDD)

**Files:**
- Create: `src/lib/bible-api.ts`
- Create: `src/lib/__tests__/bible-api.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

`src/lib/__tests__/bible-api.test.ts` 생성:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchVerse, buildBollsUrl } from '../bible-api'
import type { VerseRef } from '../types'

// fetch 모킹
global.fetch = vi.fn()

beforeEach(() => vi.clearAllMocks())

const ref: VerseRef = { book: '1John', chapter: 1, verse: 9, translation: 'KRV' }

describe('buildBollsUrl', () => {
  it('Bolls.life URL 생성', () => {
    const url = buildBollsUrl(ref)
    // book ID: 1John = 62
    expect(url).toBe('https://bolls.life/get-verse/KRV/62/1/9/')
  })
})

describe('fetchVerse', () => {
  it('구절 데이터 반환', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ text: '만일 우리가 우리 죄를 자백하면...' }),
    } as Response)

    const result = await fetchVerse(ref)
    expect(result.text).toBe('만일 우리가 우리 죄를 자백하면...')
    expect(result.bookNameKo).toBe('요한일서')
    expect(result.ref).toEqual(ref)
  })

  it('API 실패 시 에러', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
    } as Response)

    await expect(fetchVerse(ref)).rejects.toThrow('Bible API 404')
  })
})
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
npm test src/lib/__tests__/bible-api.test.ts
```

Expected: `Cannot find module '../bible-api'`

- [ ] **Step 3: 구현**

`src/lib/bible-api.ts` 생성:

```typescript
import { BOOK_IDS, BOOK_NAMES_KO, BOLLS_TRANSLATIONS } from './constants'
import type { VerseRef, VerseData, TranslationCode } from './types'

export function buildBollsUrl(ref: VerseRef): string {
  const bookId = BOOK_IDS[ref.book]
  if (!bookId) throw new Error(`Unknown book: ${ref.book}`)
  return `https://bolls.life/get-verse/${ref.translation}/${bookId}/${ref.chapter}/${ref.verse}/`
}

export async function fetchVerse(ref: VerseRef): Promise<VerseData> {
  const url = BOLLS_TRANSLATIONS.includes(ref.translation as TranslationCode)
    ? buildBollsUrl(ref)
    : buildGetBibleUrl(ref)

  const res = await fetch(url, { next: { revalidate: 86400 } })
  if (!res.ok) throw new Error(`Bible API ${res.status}`)

  const data = await res.json()
  return {
    ref,
    text: data.text ?? data.verse ?? '',
    bookNameKo: BOOK_NAMES_KO[ref.book] ?? ref.book,
  }
}

function buildGetBibleUrl(ref: VerseRef): string {
  const bookId = BOOK_IDS[ref.book]
  if (!bookId) throw new Error(`Unknown book: ${ref.book}`)
  const trans = ref.translation.toLowerCase()
  return `https://api.getbible.net/v2/${trans}/${bookId}/${ref.chapter}.json`
}

export async function fetchVerseGetBible(ref: VerseRef): Promise<VerseData> {
  const url = buildGetBibleUrl(ref)
  const res = await fetch(url, { next: { revalidate: 86400 } })
  if (!res.ok) throw new Error(`GetBible API ${res.status}`)
  const data = await res.json()
  // GetBible returns chapter object: { verses: { "1": { verse: "..." } } }
  const verseText = data.verses?.[String(ref.verse)]?.verse ?? ''
  return {
    ref,
    text: verseText,
    bookNameKo: BOOK_NAMES_KO[ref.book] ?? ref.book,
  }
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npm test src/lib/__tests__/bible-api.test.ts
```

Expected: `3 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/lib/bible-api.ts src/lib/__tests__/bible-api.test.ts
git commit -m "feat: bible API client (Bolls.life + GetBible) with tests"
```

---

## Task 6: Gemini 클라이언트

**Files:**
- Create: `src/lib/gemini.ts`
- Create: `.env.example`
- Create: `.env.local` (gitignore됨 — GEMINI_API_KEY 직접 입력)

- [ ] **Step 1: `.env.example` 생성**

```bash
GEMINI_API_KEY=your_gemini_api_key_here
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

- [ ] **Step 2: `.env.local` 생성 (실제 키 입력)**

```bash
GEMINI_API_KEY=<실제_Gemini_API_키>
```

- [ ] **Step 3: `src/lib/gemini.ts` 생성**

```typescript
import { GoogleGenerativeAI, type Content } from '@google/generative-ai'
import type { ChatMessage } from './types'

if (!process.env.GEMINI_API_KEY) {
  throw new Error('GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.')
}

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY)

export const SYSTEM_PROMPT = `당신은 '말씀 길잡이'입니다. 성경에 깊이 정통한 따뜻한 영적 동반자로서 다음 원칙을 따르세요:

1. **소크라테스식 접근**: 첫 응답에서 반드시 한 가지 질문으로 사용자의 상황을 파악하세요.
2. **말씀 인용**: 상황을 파악한 후 관련 성경 구절을 인용하세요.
3. **구절 인용 형식**: [[VERSE:영문책명:장:절:번역코드]]
   - 예: [[VERSE:1John:1:9:KRV]], [[VERSE:Psalms:23:1:KRV]]
   - 반드시 이 형식을 정확히 사용하세요. 번역코드는 KRV(개역한글), RNKSV(새번역), NIV, ESV, KJV 중 하나.
4. **다음 방향 제안**: 응답 마지막에 SUGGESTIONS: 로 시작하는 줄에 세미콜론으로 구분된 2-3개 제안을 추가하세요.
   - 예: SUGGESTIONS: 더 깊이 묵상하기;연결된 말씀 보기;다른 주제로
5. **언어**: 항상 한국어로 응답. 구절은 개역한글(KRV) 우선.
6. **한자 병기**: 신학 용어에 한자를 병기하세요. 예: 은혜(恩惠), 속죄(贖罪), 구원(救援).
7. **길이**: 3-4문장 이내로 간결하게. 구절 태그 외 길게 설명하지 마세요.`

export function buildGeminiContents(messages: ChatMessage[]): Content[] {
  return messages
    .filter(m => !m.isStreaming)
    .slice(-10)  // 최근 10턴
    .map(m => ({
      role: m.role === 'user' ? 'user' : 'model',
      parts: [{ text: m.rawContent ?? m.content }],
    }))
}

export function getModel(apiKey?: string) {
  const key = apiKey ?? process.env.GEMINI_API_KEY!
  const ai = new GoogleGenerativeAI(key)
  return ai.getGenerativeModel({
    model: 'gemini-2.5-flash',
    systemInstruction: SYSTEM_PROMPT,
    generationConfig: {
      maxOutputTokens: 1024,
      temperature: 0.7,
    },
  })
}

export function parseSuggestions(text: string): { clean: string; chips: Array<{ label: string; prompt: string }> } {
  const suggLine = text.match(/SUGGESTIONS:\s*(.+)$/m)
  const clean = text.replace(/SUGGESTIONS:\s*.+$/m, '').trim()
  if (!suggLine) return { clean, chips: [] }
  const chips = suggLine[1].split(';').map(s => s.trim()).filter(Boolean).map(label => ({
    label,
    prompt: label,
  }))
  return { clean, chips }
}
```

- [ ] **Step 4: 커밋**

```bash
git add src/lib/gemini.ts .env.example
git commit -m "feat: gemini client with system prompt and suggestion parser"
```

---

## Task 7: `/api/verse` 라우트

**Files:**
- Create: `src/app/api/verse/route.ts`

- [ ] **Step 1: 라우트 생성**

`src/app/api/verse/route.ts` 생성:

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { fetchVerse } from '@/lib/bible-api'
import { BOOK_IDS } from '@/lib/constants'
import type { TranslationCode, VerseRef } from '@/lib/types'

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const ref = searchParams.get('ref')   // e.g. "1John:1:9"
  const translation = (searchParams.get('translation') ?? 'KRV') as TranslationCode

  if (!ref) {
    return NextResponse.json({ error: 'ref 파라미터 필요' }, { status: 400 })
  }

  const parts = ref.split(':')
  if (parts.length !== 3) {
    return NextResponse.json({ error: 'ref 형식: 책명:장:절 (예: 1John:1:9)' }, { status: 400 })
  }

  const [book, chStr, vsStr] = parts
  const chapter = parseInt(chStr, 10)
  const verse = parseInt(vsStr, 10)

  if (!BOOK_IDS[book] || isNaN(chapter) || isNaN(verse)) {
    return NextResponse.json({ error: '알 수 없는 책명 또는 잘못된 장/절' }, { status: 400 })
  }

  const verseRef: VerseRef = { book, chapter, verse, translation }

  try {
    const data = await fetchVerse(verseRef)
    return NextResponse.json(data)
  } catch (err) {
    const message = err instanceof Error ? err.message : '구절 조회 실패'
    return NextResponse.json({ error: message }, { status: 502 })
  }
}
```

- [ ] **Step 2: 수동 테스트**

```bash
npm run dev
# 새 터미널에서:
curl "http://localhost:3000/api/verse?ref=John:3:16&translation=KRV"
```

Expected: `{"ref":{"book":"John","chapter":3,"verse":16,"translation":"KRV"},"text":"...하나님이 세상을 이처럼 사랑하사...","bookNameKo":"요한복음"}`

- [ ] **Step 3: 커밋**

```bash
git add src/app/api/verse/route.ts
git commit -m "feat: /api/verse endpoint (Bolls.life proxy)"
```

---

## Task 8: `/api/chat` 스트리밍 라우트

**Files:**
- Create: `src/app/api/chat/route.ts`

- [ ] **Step 1: 라우트 생성**

`src/app/api/chat/route.ts` 생성:

```typescript
import { NextRequest } from 'next/server'
import { getModel, buildGeminiContents, parseSuggestions } from '@/lib/gemini'
import { extractVerseRefs, stripVerseTags } from '@/lib/verse-parser'
import type { ChatMessage, StreamChunk } from '@/lib/types'

function encode(chunk: StreamChunk): string {
  return `data: ${JSON.stringify(chunk)}\n\n`
}

export async function POST(req: NextRequest) {
  const userApiKey = req.headers.get('x-gemini-api-key') ?? undefined
  const body = await req.json() as { messages: ChatMessage[] }

  if (!body.messages?.length) {
    return new Response(encode({ type: 'error', message: 'messages 필드 필요' }), {
      status: 400,
      headers: { 'Content-Type': 'text/event-stream' },
    })
  }

  const stream = new ReadableStream({
    async start(controller) {
      const send = (chunk: StreamChunk) =>
        controller.enqueue(new TextEncoder().encode(encode(chunk)))

      try {
        const model = getModel(userApiKey)
        const contents = buildGeminiContents(body.messages)

        const result = await model.generateContentStream({ contents })

        let fullText = ''
        for await (const chunk of result.stream) {
          const piece = chunk.text()
          fullText += piece
          // 태그 없는 텍스트 부분만 스트리밍
          const visiblePiece = stripVerseTags(piece)
          if (visiblePiece) send({ type: 'text', content: visiblePiece })
        }

        // 완성 후: 구절 태그 추출 + 제안 파싱
        const verseRefs = extractVerseRefs(fullText)
        for (const ref of verseRefs) {
          send({ type: 'verse_ref', ref })
        }

        const { chips } = parseSuggestions(fullText)
        if (chips.length > 0) {
          send({ type: 'suggestions', chips })
        }

        send({ type: 'done' })
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Gemini 오류'
        send({ type: 'error', message })
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
```

- [ ] **Step 2: 수동 테스트**

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"id":"1","role":"user","content":"용서에 대해 알고 싶어요","verses":[],"suggestions":[]}]}' \
  --no-buffer
```

Expected: SSE 스트림 — `data: {"type":"text","content":"..."}` 라인들 출력, 이후 `verse_ref`, `suggestions`, `done`

- [ ] **Step 3: 커밋**

```bash
git add src/app/api/chat/route.ts
git commit -m "feat: /api/chat Gemini SSE streaming route"
```

---

## Task 9: `VerseCard` 컴포넌트

**Files:**
- Create: `src/components/VerseCard.tsx`
- Create: `src/components/__tests__/VerseCard.test.tsx`

- [ ] **Step 1: 실패 테스트 작성**

`src/components/__tests__/VerseCard.test.tsx` 생성:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import VerseCard from '../VerseCard'
import type { VerseData } from '@/lib/types'

const verse: VerseData = {
  ref: { book: '1John', chapter: 1, verse: 9, translation: 'KRV' },
  text: '만일 우리가 우리 죄를 자백하면 저는 미쁘시고 의로우사...',
  bookNameKo: '요한일서',
}

describe('VerseCard', () => {
  it('구절 텍스트와 참조 렌더링', () => {
    render(<VerseCard verse={verse} onAction={vi.fn()} />)
    expect(screen.getByText(/만일 우리가 우리 죄를/)).toBeInTheDocument()
    expect(screen.getByText(/요한일서 1:9/)).toBeInTheDocument()
  })

  it('번역 비교 버튼 클릭', () => {
    const onAction = vi.fn()
    render(<VerseCard verse={verse} onAction={onAction} />)
    fireEvent.click(screen.getByRole('button', { name: /번역 비교/ }))
    expect(onAction).toHaveBeenCalledWith('compare', verse.ref)
  })
})
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
npm test src/components/__tests__/VerseCard.test.tsx
```

Expected: `Cannot find module '../VerseCard'`

- [ ] **Step 3: 구현**

`src/components/VerseCard.tsx` 생성:

```typescript
'use client'
import type { VerseData, PanelType, VerseRef } from '@/lib/types'
import { TRANSLATION_LABELS } from '@/lib/constants'

interface Props {
  verse: VerseData
  onAction: (panel: PanelType, ref: VerseRef) => void
}

export default function VerseCard({ verse, onAction }: Props) {
  const { ref, text, bookNameKo } = verse
  const displayRef = `${bookNameKo} ${ref.chapter}:${ref.verse}`
  const translationLabel = TRANSLATION_LABELS[ref.translation] ?? ref.translation

  return (
    <div className="rounded-lg border border-[var(--clay-border)] bg-[var(--paper-white)] p-4 my-1">
      <div className="flex items-center justify-between mb-2">
        <span className="verse-label">{displayRef} · {translationLabel}</span>
      </div>
      <p className="verse-text">{text}</p>
      <div className="flex gap-2 mt-3 flex-wrap">
        <ActionTag label="번역 비교" onClick={() => onAction('compare', ref)} />
        <ActionTag label="원어 보기" onClick={() => onAction('original', ref)} />
        <ActionTag label="교차 참조" onClick={() => onAction('search', ref)} />
      </div>
    </div>
  )
}

function ActionTag({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="text-[0.65rem] bg-[var(--clay-light)] text-clay px-3 py-1 rounded-full
                 hover:bg-[rgba(139,99,67,0.2)] transition-colors"
    >
      {label}
    </button>
  )
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npm test src/components/__tests__/VerseCard.test.tsx
```

Expected: `2 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/components/VerseCard.tsx src/components/__tests__/VerseCard.test.tsx
git commit -m "feat: VerseCard component with tests"
```

---

## Task 10: `SuggestionChips` 컴포넌트

**Files:**
- Create: `src/components/SuggestionChips.tsx`
- Create: `src/components/__tests__/SuggestionChips.test.tsx`

- [ ] **Step 1: 실패 테스트 작성**

`src/components/__tests__/SuggestionChips.test.tsx` 생성:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SuggestionChips from '../SuggestionChips'

const chips = [
  { label: '더 깊이 묵상하기', prompt: '더 깊이 묵상하기' },
  { label: '연결된 말씀 보기', prompt: '연결된 말씀 보기' },
]

describe('SuggestionChips', () => {
  it('칩 목록 렌더링', () => {
    render(<SuggestionChips chips={chips} onSelect={vi.fn()} />)
    expect(screen.getByText('더 깊이 묵상하기')).toBeInTheDocument()
    expect(screen.getByText('연결된 말씀 보기')).toBeInTheDocument()
  })

  it('칩 클릭 시 onSelect 호출', () => {
    const onSelect = vi.fn()
    render(<SuggestionChips chips={chips} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('더 깊이 묵상하기'))
    expect(onSelect).toHaveBeenCalledWith('더 깊이 묵상하기')
  })
})
```

- [ ] **Step 2: 구현**

`src/components/SuggestionChips.tsx` 생성:

```typescript
'use client'
import type { SuggestionChip } from '@/lib/types'

interface Props {
  chips: SuggestionChip[]
  onSelect: (prompt: string) => void
}

export default function SuggestionChips({ chips, onSelect }: Props) {
  if (!chips.length) return null
  return (
    <div className="flex gap-2 flex-wrap mt-2">
      {chips.map((chip) => (
        <button
          key={chip.label}
          onClick={() => onSelect(chip.prompt)}
          className="text-[0.75rem] border border-[var(--clay-border)] text-[var(--ink-medium)]
                     bg-[var(--suggestion-bg)] rounded-full px-4 py-1.5
                     hover:border-clay hover:text-clay transition-colors"
        >
          {chip.label}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
npm test src/components/__tests__/SuggestionChips.test.tsx
```

Expected: `2 passed`

- [ ] **Step 4: 커밋**

```bash
git add src/components/SuggestionChips.tsx src/components/__tests__/SuggestionChips.test.tsx
git commit -m "feat: SuggestionChips component with tests"
```

---

## Task 11: `MessageBubble` 컴포넌트

**Files:**
- Create: `src/components/MessageBubble.tsx`
- Create: `src/components/__tests__/MessageBubble.test.tsx`

- [ ] **Step 1: 실패 테스트 작성**

`src/components/__tests__/MessageBubble.test.tsx` 생성:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import MessageBubble from '../MessageBubble'
import type { ChatMessage } from '@/lib/types'

const userMsg: ChatMessage = {
  id: '1', role: 'user',
  content: '용서에 대해 알고 싶어요',
  verses: [], suggestions: [],
}

const aiMsg: ChatMessage = {
  id: '2', role: 'assistant',
  content: '지금 용서가 필요한 상황이신가요?',
  verses: [], suggestions: [{ label: '더 깊이', prompt: '더 깊이' }],
}

describe('MessageBubble', () => {
  it('사용자 메시지 — 우측 정렬', () => {
    const { container } = render(<MessageBubble message={userMsg} onAction={vi.fn()} onSuggestion={vi.fn()} />)
    expect(screen.getByText('용서에 대해 알고 싶어요')).toBeInTheDocument()
    expect(container.firstChild).toHaveClass('items-end')
  })

  it('AI 메시지 — 말씀 길잡이 레이블', () => {
    render(<MessageBubble message={aiMsg} onAction={vi.fn()} onSuggestion={vi.fn()} />)
    expect(screen.getByText(/말씀 길잡이/)).toBeInTheDocument()
    expect(screen.getByText('지금 용서가 필요한 상황이신가요?')).toBeInTheDocument()
    expect(screen.getByText('더 깊이')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 구현**

`src/components/MessageBubble.tsx` 생성:

```typescript
'use client'
import type { ChatMessage, PanelType, VerseRef } from '@/lib/types'
import VerseCard from './VerseCard'
import SuggestionChips from './SuggestionChips'

interface Props {
  message: ChatMessage
  onAction: (panel: PanelType, ref: VerseRef) => void
  onSuggestion: (prompt: string) => void
}

export default function MessageBubble({ message, onAction, onSuggestion }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} gap-1`}>
      {!isUser && (
        <span className="verse-label px-1">✦ 말씀 길잡이</span>
      )}
      <div
        className={`max-w-[80%] rounded-xl px-4 py-3 text-[0.9rem] leading-relaxed ${
          isUser
            ? 'rounded-br-sm bg-[var(--clay-light)] text-[var(--ink-dark)]'
            : 'rounded-bl-sm border-l-2 border-clay bg-[rgba(139,99,67,0.08)] text-[var(--ink-dark)]'
        }`}
      >
        {message.isStreaming ? (
          <span>{message.content}<span className="animate-pulse">▌</span></span>
        ) : (
          message.content
        )}
      </div>
      {message.verses.map((verse) => (
        <VerseCard key={`${verse.ref.book}:${verse.ref.chapter}:${verse.ref.verse}`}
          verse={verse} onAction={onAction} />
      ))}
      {!message.isStreaming && message.suggestions.length > 0 && (
        <SuggestionChips chips={message.suggestions} onSelect={onSuggestion} />
      )}
    </div>
  )
}
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
npm test src/components/__tests__/MessageBubble.test.tsx
```

Expected: `2 passed`

- [ ] **Step 4: 커밋**

```bash
git add src/components/MessageBubble.tsx src/components/__tests__/MessageBubble.test.tsx
git commit -m "feat: MessageBubble component with tests"
```

---

## Task 12: `ChatInput` 컴포넌트

**Files:**
- Create: `src/components/ChatInput.tsx`
- Create: `src/components/__tests__/ChatInput.test.tsx`

- [ ] **Step 1: 실패 테스트 작성**

`src/components/__tests__/ChatInput.test.tsx` 생성:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatInput from '../ChatInput'

describe('ChatInput', () => {
  it('텍스트 입력 후 전송', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={false} />)
    const textarea = screen.getByRole('textbox')
    await userEvent.type(textarea, '용서에 대해')
    await userEvent.keyboard('{Enter}')
    expect(onSend).toHaveBeenCalledWith('용서에 대해')
  })

  it('빈 입력은 전송 안 됨', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} disabled={false} />)
    await userEvent.keyboard('{Enter}')
    expect(onSend).not.toHaveBeenCalled()
  })

  it('disabled 상태에서 비활성화', () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />)
    expect(screen.getByRole('textbox')).toBeDisabled()
  })
})
```

- [ ] **Step 2: 구현**

`src/components/ChatInput.tsx` 생성:

```typescript
'use client'
import { useState, useRef, type KeyboardEvent } from 'react'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }

  return (
    <div className="px-4 py-3 border-t border-[var(--clay-border)] bg-[var(--hanji-cream)]">
      <div className="flex items-end gap-3 bg-[var(--paper-white)] border border-[var(--clay-border)]
                      rounded-3xl px-4 py-2">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={disabled}
          placeholder="말씀을 찾거나, 마음의 질문을 나눠보세요..."
          rows={1}
          className="flex-1 bg-transparent resize-none text-[0.9rem] text-[var(--ink-dark)]
                     placeholder:text-[var(--ink-medium)] placeholder:opacity-60
                     focus:outline-none font-[var(--font-ui)] disabled:opacity-50"
          style={{ maxHeight: '120px' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="w-8 h-8 rounded-full bg-[var(--ink-dark)] text-[var(--hanji-cream)]
                     flex items-center justify-center text-sm flex-shrink-0 mb-0.5
                     hover:bg-clay transition-colors disabled:opacity-40"
        >
          ↑
        </button>
      </div>
      <p className="text-[0.6rem] text-center text-[var(--ink-medium)] opacity-50 mt-1 font-[var(--font-ui)]">
        Enter로 전송 · Shift+Enter 줄바꿈
      </p>
    </div>
  )
}
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
npm test src/components/__tests__/ChatInput.test.tsx
```

Expected: `3 passed`

- [ ] **Step 4: 커밋**

```bash
git add src/components/ChatInput.tsx src/components/__tests__/ChatInput.test.tsx
git commit -m "feat: ChatInput component with tests"
```

---

## Task 13: `TopBar` + `IconSidebar` 컴포넌트

**Files:**
- Create: `src/components/TopBar.tsx`
- Create: `src/components/IconSidebar.tsx`

*(레이아웃 컴포넌트 — 자동화 테스트 생략, 수동 확인)*

- [ ] **Step 1: `TopBar.tsx` 생성**

```typescript
'use client'
import { DEFAULT_TRANSLATION, TRANSLATION_LABELS } from '@/lib/constants'
import type { TranslationCode } from '@/lib/types'

interface Props {
  translation: TranslationCode
  onTranslationChange: (t: TranslationCode) => void
  onNewChat: () => void
}

const TRANSLATIONS: TranslationCode[] = ['KRV', 'RNKSV', 'NIV', 'ESV', 'KJV']

export default function TopBar({ translation, onTranslationChange, onNewChat }: Props) {
  return (
    <header className="flex items-center justify-between px-4 py-2.5
                       border-b border-[var(--clay-border)] bg-[var(--hanji-cream)]
                       sticky top-0 z-10">
      <button onClick={onNewChat} className="text-left hover:opacity-70 transition-opacity">
        <div className="text-[0.75rem] tracking-[0.25em] text-[var(--ink-medium)] font-[var(--font-ui)]">
          말씀의 길
        </div>
        <div className="text-[0.5rem] tracking-[0.4em] text-clay font-[var(--font-ui)] uppercase">
          VERBUM
        </div>
      </button>
      <div className="flex items-center gap-2">
        <select
          value={translation}
          onChange={(e) => onTranslationChange(e.target.value as TranslationCode)}
          className="text-[0.75rem] bg-[var(--clay-light)] text-[var(--ink-medium)] border-none
                     rounded-xl px-3 py-1 font-[var(--font-ui)] focus:outline-none cursor-pointer"
        >
          {TRANSLATIONS.map((t) => (
            <option key={t} value={t}>{TRANSLATION_LABELS[t]}</option>
          ))}
        </select>
      </div>
    </header>
  )
}
```

- [ ] **Step 2: `IconSidebar.tsx` 생성**

```typescript
'use client'
import type { PanelType } from '@/lib/types'

interface Props {
  activePanel: PanelType
  onToggle: (panel: PanelType) => void
}

const ICONS: { panel: PanelType; icon: string; label: string }[] = [
  { panel: 'search',   icon: '🔍', label: '검색' },
  { panel: 'browse',   icon: '📖', label: '탐독' },
  { panel: 'themes',   icon: '🌿', label: '묵상' },
  { panel: 'compare',  icon: '⇄',  label: '비교' },
  { panel: 'original', icon: 'α',  label: '원어' },
]

export default function IconSidebar({ activePanel, onToggle }: Props) {
  return (
    <nav className="hidden md:flex flex-col items-center gap-3 px-1 py-4 w-12
                    border-r border-[var(--clay-border)] bg-[rgba(245,237,224,0.5)]">
      <div className="w-6 h-6 rounded-full bg-[var(--ink-dark)] flex items-center
                      justify-center text-[var(--hanji-cream)] text-xs mb-1">
        ✦
      </div>
      <div className="w-5 h-px bg-[var(--clay-border)]" />
      {ICONS.map(({ panel, icon, label }) => (
        <button
          key={panel}
          onClick={() => onToggle(panel)}
          title={label}
          className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm
                      transition-colors ${
                        activePanel === panel
                          ? 'bg-[var(--clay-light)] text-clay'
                          : 'text-[var(--ink-medium)] hover:bg-[var(--clay-light)]'
                      }`}
        >
          {icon}
        </button>
      ))}
    </nav>
  )
}
```

- [ ] **Step 3: 커밋**

```bash
git add src/components/TopBar.tsx src/components/IconSidebar.tsx
git commit -m "feat: TopBar and IconSidebar layout components"
```

---

## Task 14: `ChatInterface` — 메인 컨테이너

**Files:**
- Create: `src/components/ChatInterface.tsx`

*(통합 컴포넌트 — 단위 테스트보다 E2E가 적합, 여기선 수동 테스트)*

- [ ] **Step 1: `ChatInterface.tsx` 생성**

```typescript
'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { nanoid } from 'nanoid'
import type { ChatMessage, AppState, PanelType, VerseRef, VerseData, SuggestionChip } from '@/lib/types'
import { DEFAULT_TRANSLATION } from '@/lib/constants'
import { parseVerseRefString } from '@/lib/verse-parser'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import TopBar from './TopBar'
import IconSidebar from './IconSidebar'

// nanoid 설치: npm install nanoid
// (아래 Step 0에서 설치)

const WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: '안녕하세요. 저는 말씀 길잡이입니다.\n어떤 말씀이나 주제에 대해 함께 나눠보고 싶으신가요?',
  verses: [],
  suggestions: [
    { label: '용서에 대해', prompt: '용서에 대해 알고 싶어요' },
    { label: '소망의 말씀', prompt: '소망에 대한 말씀을 찾고 싶어요' },
    { label: '오늘의 위로', prompt: '오늘 마음이 힘드네요. 위로의 말씀이 필요해요' },
  ],
}

export default function ChatInterface() {
  const [state, setState] = useState<AppState>({
    messages: [WELCOME_MESSAGE],
    activePanel: 'none',
    activePanelVerse: null,
    translation: DEFAULT_TRANSLATION,
    isLoading: false,
    error: null,
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const userScrolledUp = useRef(false)

  // 자동 스크롤
  useEffect(() => {
    if (!userScrolledUp.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [state.messages])

  const handleSend = useCallback(async (text: string) => {
    const userMsg: ChatMessage = {
      id: nanoid(), role: 'user', content: text, verses: [], suggestions: [],
    }
    const assistantId = nanoid()
    const assistantMsg: ChatMessage = {
      id: assistantId, role: 'assistant', content: '',
      verses: [], suggestions: [], isStreaming: true,
    }

    setState(s => ({
      ...s,
      messages: [...s.messages, userMsg, assistantMsg],
      isLoading: true, error: null,
    }))

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...state.messages, userMsg].map(m => ({
            id: m.id, role: m.role, content: m.rawContent ?? m.content,
            verses: [], suggestions: [],
          })),
        }),
      })

      if (!res.body) throw new Error('스트림 없음')
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const json = JSON.parse(line.slice(6))

          if (json.type === 'text') {
            setState(s => ({
              ...s,
              messages: s.messages.map(m =>
                m.id === assistantId ? { ...m, content: m.content + json.content } : m
              ),
            }))
          } else if (json.type === 'verse_ref') {
            const parsed = parseVerseRefString(json.ref)
            if (!parsed) continue
            const verseRef: VerseRef = {
              book: parsed.book, chapter: parsed.chapter,
              verse: parsed.verse, translation: parsed.translation as any,
            }
            // 구절 텍스트 조회
            const verseRes = await fetch(
              `/api/verse?ref=${verseRef.book}:${verseRef.chapter}:${verseRef.verse}&translation=${verseRef.translation}`
            )
            if (verseRes.ok) {
              const verseData: VerseData = await verseRes.json()
              setState(s => ({
                ...s,
                messages: s.messages.map(m =>
                  m.id === assistantId ? { ...m, verses: [...m.verses, verseData] } : m
                ),
              }))
            }
          } else if (json.type === 'suggestions') {
            setState(s => ({
              ...s,
              messages: s.messages.map(m =>
                m.id === assistantId
                  ? { ...m, suggestions: json.chips, isStreaming: false }
                  : m
              ),
            }))
          } else if (json.type === 'done') {
            setState(s => ({
              ...s,
              messages: s.messages.map(m =>
                m.id === assistantId ? { ...m, isStreaming: false } : m
              ),
              isLoading: false,
            }))
          } else if (json.type === 'error') {
            throw new Error(json.message)
          }
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '오류가 발생했습니다'
      setState(s => ({
        ...s,
        messages: s.messages.map(m =>
          m.id === assistantId
            ? { ...m, content: `오류: ${message}`, isStreaming: false }
            : m
        ),
        isLoading: false,
        error: message,
      }))
    }
  }, [state.messages])

  const handlePanelToggle = (panel: PanelType) => {
    setState(s => ({ ...s, activePanel: s.activePanel === panel ? 'none' : panel }))
  }

  const handleAction = (panel: PanelType, ref: VerseRef) => {
    setState(s => ({ ...s, activePanel: panel, activePanelVerse: ref }))
  }

  const handleNewChat = () => {
    setState(s => ({ ...s, messages: [WELCOME_MESSAGE], activePanel: 'none', error: null }))
  }

  return (
    <div className="flex flex-col h-screen bg-[var(--hanji-warm)]">
      <TopBar
        translation={state.translation}
        onTranslationChange={(t) => setState(s => ({ ...s, translation: t }))}
        onNewChat={handleNewChat}
      />
      <div className="flex flex-1 overflow-hidden">
        <IconSidebar activePanel={state.activePanel} onToggle={handlePanelToggle} />
        <main className="flex flex-col flex-1 overflow-hidden">
          <div
            className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
            onScroll={(e) => {
              const el = e.currentTarget
              userScrolledUp.current = el.scrollTop < el.scrollHeight - el.clientHeight - 100
            }}
          >
            {state.messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onAction={handleAction}
                onSuggestion={handleSend}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
          <ChatInput onSend={handleSend} disabled={state.isLoading} />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 0: nanoid 설치** (Step 1 전에)

```bash
npm install nanoid
```

- [ ] **Step 2: 커밋**

```bash
git add src/components/ChatInterface.tsx
git commit -m "feat: ChatInterface main container with streaming"
```

---

## Task 15: `page.tsx` + 최종 확인 + Vercel 배포

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: `page.tsx` 단순화**

```typescript
import ChatInterface from '@/components/ChatInterface'

export default function Home() {
  return <ChatInterface />
}
```

- [ ] **Step 2: 전체 테스트 통과 확인**

```bash
npm test
```

Expected: `10 passed` (verse-parser 4 + bible-api 3 + VerseCard 2 + SuggestionChips 2 + MessageBubble 2 + ChatInput 3)

- [ ] **Step 3: 빌드 확인**

```bash
npm run build
```

Expected: `✓ Compiled successfully` — 빌드 오류 0개

- [ ] **Step 4: 로컬 실제 사용 테스트**

```bash
npm run dev
```

브라우저에서 `http://localhost:3000` 접속 후:
1. "용서에 대해 알고 싶어요" 전송 → Gemini 응답 스트리밍 확인
2. 구절 카드 표시 확인 (요한일서 1:9 등)
3. 제안 칩 표시 확인 + 칩 클릭 동작 확인
4. 번역본 드롭다운 변경 확인

- [ ] **Step 5: Vercel 배포 설정**

```bash
npm install -g vercel
vercel login
vercel
# 프롬프트:
#   Set up and deploy: Yes
#   Which scope: 계정 선택
#   Link to existing project: No
#   Project name: malsseum-ui
#   Directory: ./
#   Override settings: No
```

Vercel 대시보드 → Environment Variables → `GEMINI_API_KEY` 추가

```bash
vercel --prod
```

- [ ] **Step 6: 최종 커밋 + 태그**

```bash
git add src/app/page.tsx
git commit -m "feat: Phase 1 MVP complete — Gemini chat + verse cards + hanji design"
git tag v0.1.0-phase1
```

---

## 전체 테스트 실행

```bash
npm test
```

Expected 최종:
```
✓ src/lib/__tests__/verse-parser.test.ts (4)
✓ src/lib/__tests__/bible-api.test.ts (3)
✓ src/components/__tests__/VerseCard.test.tsx (2)
✓ src/components/__tests__/SuggestionChips.test.tsx (2)
✓ src/components/__tests__/MessageBubble.test.tsx (2)
✓ src/components/__tests__/ChatInput.test.tsx (3)

Test Files  6 passed
Tests      16 passed
```

---

## Phase 2 예고 (별도 플랜)

- SlidePanel 프레임워크 (우측 슬라이드인)
- TranslationComparePanel (번역 비교)
- SearchPanel (Gemini 추천 검색)
- BrowsePanel (성경 탐독)
