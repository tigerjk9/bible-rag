# 말씀의 길 (VERBUM) — 설계 문서

**날짜**: 2026-04-27  
**상태**: 승인됨  
**배포 대상**: Vercel (신규 프로젝트, bible-rag와 별도)

---

## 1. 프로젝트 목적

Gemini API 단독으로 구동되는 한국어 중심 성경 대화형 웹앱.  
사용자가 말씀을 통해 진리에 **소크라테스식 질문 + 따뜻한 영적 동반자** 방식으로 접근하도록 돕는다.  
기존 bible-rag의 기능(번역 비교, 원어, 교차 참조 등)을 한지(韓紙) 미감으로 재설계하여 제공한다.

---

## 2. 기술 스택

| 항목 | 선택 | 이유 |
|------|------|------|
| 프레임워크 | Next.js 15 (App Router) | 기존 프로젝트와 동일, Vercel 최적화 |
| 언어 | TypeScript 5.7 | 타입 안전성 |
| 스타일링 | Tailwind CSS 3 + CSS Variables | 한지 테마 토큰 관리 |
| AI | Google Generative AI SDK (`@google/generative-ai`) | Gemini 2.5 Flash |
| 성경 데이터 | Bolls.life API + GetBible API | 무료, DB 불필요 |
| 교차 참조 | OpenBible.info API | 63,779개 연결, 무료 |
| 폰트 | Noto Serif KR (본문) + Inter (UI) | 한국어 세리프 최적화 |
| 배포 | Vercel | 자동 배포 |

**제거된 의존성**: PostgreSQL, pgvector, Redis, 로컬 임베딩 모델, 리랭커 — 모두 Gemini가 대체

---

## 3. 디자인 시스템 — 한지(韓紙)

### 컬러 팔레트

```css
--hanji-cream:    #f5ede0   /* 배경 (한지 크림) */
--hanji-warm:     #ede8e0   /* 페이지 배경 */
--ink-dark:       #3d2b1f   /* 주 텍스트 (먹색) */
--ink-medium:     #7a5c3a   /* 보조 텍스트 */
--clay:           #8b6343   /* 액센트 (황토) */
--clay-light:     rgba(139,99,67,0.12)  /* 배경 틴트 */
--paper-white:    #ffffff   /* 카드 배경 */

/* 다크모드 */
--hanji-cream-dark: #1a1208
--ink-dark-dark:    #f0e6d3
```

### 타이포그래피

- **본문/구절**: `Noto Serif KR`, `Georgia`, serif — 묵상하는 느낌
- **UI/레이블**: `Inter`, sans-serif — 명료함
- **구절 크기**: 1.05rem, line-height 1.9
- **레이블**: 0.65rem, letter-spacing 0.2em, uppercase

### 텍스처

- 배경에 미세 괘선: `repeating-linear-gradient(0deg, transparent 28px, rgba(139,99,67,0.05) 29px)`
- 그림자 없음 — 1px 테두리 중심
- 구절 카드 좌측: 2px `#8b6343` 선

---

## 4. 앱 구조 — 대화 중심(Chat-First)

### 라우트

```
/                  → 메인 채팅 (기본 진입점)
/browse            → 성경 탐독 (책/장/절)
/themes            → 주제별 묵상
/verse/[ref]       → 구절 상세 (공유 URL용)
/api/chat          → Gemini 스트리밍 API 라우트
/api/verse         → 구절 조회 (Bolls.life 프록시)
/api/search        → 구절 검색 (Gemini 활용)
/api/translations  → 번역본 목록
/api/cross-refs    → 교차 참조 (OpenBible 프록시)
```

### 레이아웃 (데스크탑)

```
┌─────────────────────────────────────────────────────┐
│  상단바: 앱 이름 · 번역본 선택 · 다크모드             │
├──┬──────────────────────────────────┬───────────────┤
│  │                                  │               │
│아│        채팅 메시지 영역           │  슬라이드     │
│이│  (사용자 메시지 + AI 응답 +      │  패널         │
│콘│   구절 카드 + 제안 칩)           │  (기능별)     │
│바│                                  │               │
│  ├──────────────────────────────────┤               │
│  │        채팅 입력창               │               │
└──┴──────────────────────────────────┴───────────────┘
```

### 레이아웃 (모바일)

```
┌─────────────────┐
│  상단바          │
├─────────────────┤
│                 │
│  채팅 메시지    │
│                 │
├─────────────────┤
│  채팅 입력창    │
├─────────────────┤
│ ✦ 🔍 📖 🌿 ⇄  │  ← 하단 탭
└─────────────────┘
```

---

## 5. 핵심 컴포넌트

### `ChatInterface` (메인)
- 메시지 목록 렌더링 (스크롤 자동)
- 사용자 입력 → `/api/chat` 스트리밍
- 구절 카드 인라인 렌더링
- 슬라이드 패널 상태 관리

### `MessageBubble`
- 사용자: 우측 정렬, 크림 배경
- AI: 좌측 정렬, 황토 좌측 테두리 + 로고 레이블
- 구절 카드 포함 가능

### `VerseCard`
- 구절 텍스트 (현재 번역본)
- 하단 액션: 번역 비교 | 원어 보기 | 교차 참조
- 한자 토글 버튼 (신학 용어)
- 클릭 시 해당 슬라이드 패널 열림

### `SuggestionChips`
- AI 응답 후 다음 단계 제안
- "더 깊이", "연결된 말씀", "다른 주제" 등
- 클릭 시 해당 메시지를 채팅에 자동 입력

### `SlidePanel`
- 우측에서 슬라이드인 (240px, 오버레이 없음)
- 패널 종류: Search | Browse | Themes | Compare | Original
- 각 패널은 독립 컴포넌트

### `TranslationComparePanel`
- 현재 구절을 4개 번역본으로 나란히
- 번역본: 개역한글, 새번역, 개역개정, NIV, ESV, KJV
- Bolls.life + GetBible API

### `OriginalLanguagePanel`
- Strong's 번호, 발음, 형태소
- 히브리어(구약) / 헬라어(신약)
- Gemini가 설명 생성

### `IconSidebar` (데스크탑) / `BottomNav` (모바일)
- 아이콘: ✦ 대화 | 🔍 검색 | 📖 탐독 | 🌿 묵상 | ⇄ 비교 | α 원어
- 활성 아이콘 클릭 시 해당 슬라이드 패널 토글

---

## 6. Gemini 대화 설계

### 시스템 프롬프트

```
당신은 '말씀 길잡이'입니다. 성경에 깊이 정통한 따뜻한 영적 동반자로서:

1. 먼저 한 가지 질문으로 상황을 파악하세요 (소크라테스식)
2. 답변을 들은 후 관련 성경 구절을 인용하세요
3. 구절 인용 형식: [[VERSE:책영문명:장:절:번역코드]]
   예) [[VERSE:1John:1:9:KRV]]
   (Bolls.life API가 영문 책명을 요구하므로 영문 사용, 표시는 한국어로 변환)
4. 대화 후 2-3가지 다음 방향을 제안하세요
5. 항상 한국어로 응답하세요 (구절은 한국어 번역본 우선)
6. 신학적 용어에 한자를 병기하세요: 은혜(恩惠), 속죄(贖罪)
7. 길이: 응답은 3-4문장 이내로 간결하게
```

### 구절 파싱

AI 응답에서 `[[VERSE:...]]` 태그를 추출 → Bolls.life API로 실제 구절 조회 → `VerseCard`로 렌더링

### 멀티턴 컨텍스트

- 최근 10턴 대화를 컨텍스트로 유지
- 새 대화 시작 시 초기화 (우측 상단 버튼)
- 컨텍스트 압축: 10턴 초과 시 Gemini로 요약 후 유지

---

## 7. API 라우트

### `POST /api/chat`

```typescript
// Request
{ messages: Message[], translation: string }

// Response: Server-Sent Events (text/event-stream)
// data: {"type": "text", "content": "..."}
// data: {"type": "verse", "ref": "요한일서:1:9:KRV"}
// data: {"type": "suggestions", "chips": ["더 깊이", "연결된 말씀"]}
// data: {"type": "done"}
```

### `GET /api/verse?ref=요한일서:1:9&translation=KRV`

Bolls.life / GetBible API 프록시. 캐싱: `revalidate: 86400`

### `GET /api/cross-refs?ref=1John:1:9`

**MVP**: Gemini에게 관련 구절 3-5개 추천 요청 (OpenBible.info는 REST API 없이 CSV만 제공 → DB 없이는 직접 사용 불가).  
**Phase 3 개선**: OpenBible CSV를 압축 정적 JSON으로 번들링 후 in-memory 조회로 교체.

### `GET /api/search?q=용서`

Gemini에게 검색어와 관련된 성경 구절 5개 추천 요청 → 구절 조회

---

## 8. 데이터 흐름

```
사용자 입력
  → ChatInterface (클라이언트)
  → POST /api/chat (Next.js API Route)
  → Gemini 2.5 Flash (시스템 프롬프트 + 멀티턴 컨텍스트)
  → SSE 스트리밍 응답
  → 클라이언트에서 [[VERSE:...]] 태그 감지
  → GET /api/verse (Bolls.life 프록시)
  → VerseCard 렌더링
  → SuggestionChips 표시
```

---

## 9. 에러 처리

| 상황 | 처리 |
|------|------|
| Gemini API 오류 | "잠시 후 다시 시도해주세요" 토스트 + 재시도 버튼 |
| Bible API 실패 | 구절 텍스트 없이 참조만 표시, 링크 제공 |
| 네트워크 끊김 | 입력창 비활성화 + 재연결 안내 |
| API 키 미설정 | 환경변수 체크 → 명확한 오류 메시지 (개발 환경) |

---

## 10. 환경 변수

```bash
GEMINI_API_KEY=          # 필수: Gemini API 키
NEXT_PUBLIC_APP_URL=     # 선택: 배포 URL
```

사용자 API 키 입력 지원: 설정 패널에서 입력 → `localStorage` 저장 → 요청 헤더로 전달 (서버사이드에서 우선 사용)

---

## 11. 폴더 구조

```
malsseum-ui/                    ← 새 레포
├── src/
│   ├── app/
│   │   ├── page.tsx            ← 메인 채팅
│   │   ├── browse/page.tsx
│   │   ├── themes/page.tsx
│   │   ├── verse/[ref]/page.tsx
│   │   ├── layout.tsx          ← 한지 폰트/테마 로드
│   │   ├── globals.css         ← 한지 디자인 토큰
│   │   └── api/
│   │       ├── chat/route.ts
│   │       ├── verse/route.ts
│   │       ├── search/route.ts
│   │       └── cross-refs/route.ts
│   ├── components/
│   │   ├── ChatInterface.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── VerseCard.tsx
│   │   ├── SuggestionChips.tsx
│   │   ├── SlidePanel.tsx
│   │   ├── panels/
│   │   │   ├── TranslationComparePanel.tsx
│   │   │   ├── OriginalLanguagePanel.tsx
│   │   │   ├── SearchPanel.tsx
│   │   │   ├── BrowsePanel.tsx
│   │   │   └── ThemesPanel.tsx
│   │   ├── IconSidebar.tsx
│   │   ├── BottomNav.tsx
│   │   ├── HanjaToggle.tsx
│   │   └── DarkModeToggle.tsx
│   └── lib/
│       ├── gemini.ts           ← Gemini 클라이언트
│       ├── bible-api.ts        ← Bolls.life + GetBible
│       ├── verse-parser.ts     ← [[VERSE:...]] 파서
│       └── types.ts
├── tailwind.config.js
├── next.config.js
└── .env.example
```

---

## 12. 구현 우선순위

**Phase 1 — 핵심 대화 (MVP)**
1. 한지 디자인 시스템 (globals.css, Tailwind 토큰)
2. ChatInterface + MessageBubble
3. `/api/chat` Gemini 스트리밍
4. VerseCard + `[[VERSE:...]]` 파서
5. SuggestionChips

**Phase 2 — 기능 패널**
6. SlidePanel 프레임워크
7. TranslationComparePanel (Bolls.life)
8. SearchPanel (Gemini 추천)
9. BrowsePanel (성경 탐독)

**Phase 3 — 심화**
10. OriginalLanguagePanel (Gemini 설명)
11. ThemesPanel
12. CrossReferences
13. HanjaToggle
14. 다크모드
15. 반응형 BottomNav

---

## 13. 성공 기준

- [ ] 첫 Gemini 응답 < 2초 (스트리밍 첫 토큰)
- [ ] 구절 카드 표시 정확도 > 95%
- [ ] 모바일 Lighthouse 성능 > 90
- [ ] 한국어 쿼리 처리 정확도 체감 우수
- [ ] 한지 디자인이 기존 bible-rag보다 심미적으로 명확히 향상
