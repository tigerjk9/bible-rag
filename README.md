# Bible RAG

A multilingual Bible study platform powered by semantic search, supporting English and Korean with deep integration of original biblical languages.

## Overview

Bible RAG is a Retrieval-Augmented Generation (RAG) system that transforms Bible study through intelligent semantic search. Ask natural questions in English or Korean and receive contextually relevant passages with cross-translation comparisons, original language insights, and AI-powered interpretations — delivered through a conversational chat interface with streaming responses.

### Key Features

- **Chat Interface**: Conversational search with multi-turn context and streaming AI responses
  - "What does Jesus say about forgiveness?"
  - "용서에 대한 예수님의 말씀"
  - Handles code-switching: "요한복음에서 love에 대한 구절"

- **Multi-Translation Support** (10+ translations)
  - **English**: NIV, ESV, NASB, KJV, NKJV, NLT, WEB
  - **Korean**: 개역한글 (KRV), 새번역 (RNKSV), 개역개정 (NKRV - optional)
  - **Original Languages**: Hebrew (OT), Greek (NT), Aramaic (Daniel, Ezra portions)
  - All via free APIs - no API keys required!

- **Hybrid Search Pipeline**
  - Vector similarity (multilingual-e5-large) + full-text search (PostgreSQL tsvector)
  - Reciprocal Rank Fusion (RRF) combining both signal types
  - Cross-encoder reranking (BAAI/bge-reranker-v2-m3) on top-30 candidates
  - LLM query expansion for improved recall

- **Parallel Translation View**: Compare verses side-by-side across translations

- **Original Language Integration** (442,413 words ingested)
  - **Greek New Testament**: OpenGNT (~137,500 words, 99.9% Strong's coverage)
  - **Hebrew Old Testament**: OSHB/WLC (~299,487 words, 98.1% Strong's coverage)
  - **Aramaic Portions**: Daniel 2-7, Ezra 4-7, Jeremiah 10:11, Genesis 31:47 (~4,913 words, 98.0% coverage)
  - Strong's Concordance numbers (G1-G5624 Greek, H1-H8674 Hebrew/Aramaic)
  - Morphological parsing (tense, voice, mood, case, gender, number)
  - Transliteration and pronunciation guides
  - Interlinear word-by-word analysis
  - Clickable Strong's links to Blue Letter Bible
  - **"Find all verses"** lookup by Strong's number via `/api/strongs/{number}`

- **Cross-Reference Discovery**: Automatically surface related passages, grouped by relationship type (quotation, parallel, allusion, thematic) with confidence qualifiers

- **Context Expansion**: View ±2 surrounding verses around any result inline

- **Inline Verse Citations**: AI response text auto-links verse references (e.g. "John 3:16") to clickable verse cards

- **Korean-Specific Features**
  - Hanja (한자) display for theological terms
  - Romanization (via `aromanize`) for pronunciation
  - Optimized Korean typography (Noto Sans KR)
  - Respectful honorific language handling

- **Theological Term Glossary**: Multilingual term mapping
  ```
  속죄 (sokjoe) = Atonement = כָּפַר (kaphar, H3722)
  구원 (guwon) = Salvation = σωτηρία (soteria, G4991)
  은혜 (eunhye) = Grace = χάρις (charis, G5485)
  ```

- **User API Keys**: Bring-your-own Gemini/Groq keys via settings panel; keys sent as request headers, never stored server-side

- **Dark Mode**: System-aware dark/light theme toggle

## Tech Stack

### Backend
- **FastAPI** (Python 3.12+) - High-performance async API server with streaming NDJSON
- **PostgreSQL + pgvector** - Vector + full-text search (ivfflat index)
- **Redis** - Query result caching (24h TTL, normalized keys)
- **multilingual-e5-large** - Self-hosted embedding model (1024-dim)
- **BAAI/bge-reranker-v2-m3** - Cross-encoder reranker for top-30 candidates
- **Google Gemini 2.5 Flash** - Primary LLM for contextual responses
- **Groq Llama 3.3 70B** - Fallback LLM when Gemini is rate-limited

### Frontend
- **Next.js 15** - React framework with App Router
- **React 19** - UI library
- **TypeScript 5.7** - Type-safe development
- **Tailwind CSS 3** - Utility-first styling
- **Noto Sans KR** - Optimized Korean font support
- **aromanize** - Korean romanization library

### Deployment
- **Development**: Local PostgreSQL, Redis, FastAPI, Next.js
- **Production**: Supabase (database), Vercel (frontend), Railway/Vercel (backend)

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 22 LTS (or Node.js 20 LTS)
- Docker & Docker Compose
- 8GB RAM minimum (16GB recommended for embedding model + reranker)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/calebyhan/bible-rag.git
   cd bible-rag
   ```

2. **Start local infrastructure**
   ```bash
   docker-compose up -d  # Starts PostgreSQL + Redis
   ```

3. **Backend setup**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env  # Configure your environment variables

   # Ingest Bible data (fetches 9 translations automatically - ~90 min)
   python scripts/data_ingestion.py

   # Ingest original languages (Hebrew, Greek, Aramaic - ~1 min)
   python scripts/original_ingestion.py

   # Generate embeddings (15-30 min one-time)
   python scripts/embeddings.py

   # Start API server
   uvicorn main:app --reload  # http://localhost:8000
   ```

4. **Frontend setup**
   ```bash
   cd ../frontend
   npm install
   cp .env.example .env.local  # Configure environment variables
   npm run dev  # Start Next.js at http://localhost:3000
   ```

5. **Visit the application**
   Open [http://localhost:3000](http://localhost:3000) in your browser

## Example Queries

### English Semantic Search
```
"Jesus teaching about love"
"Where does the Bible talk about faith?"
"What did Paul say about grace?"
```

### Korean Semantic Search
```
"사랑에 대한 예수님의 가르침"
"믿음에 관한 성경 구절"
"바울이 은혜에 대해 말한 것"
```

### Mixed Language Search
```
"요한복음에서 love에 대한 구절"
"Genesis의 creation story"
```

## Project Structure

```
bible-rag/
├── backend/                              # FastAPI backend
│   ├── main.py                           # API entry point, CORS, router registration
│   ├── config.py                         # Settings via pydantic-settings
│   ├── database.py                       # SQLAlchemy async models + connection
│   ├── search.py                         # Hybrid search: vector + FTS → RRF → rerank
│   ├── embeddings.py                     # multilingual-e5-large embedding wrapper
│   ├── reranker.py                       # BAAI/bge-reranker-v2-m3 cross-encoder
│   ├── llm.py                            # Gemini (primary) / Groq (fallback) LLM
│   ├── llm_batcher.py                    # Batch LLM request accumulator
│   ├── cache.py                          # Redis caching layer
│   ├── original_language.py              # Strong's concordance integration
│   ├── cross_references.py               # Verse reference linking
│   ├── data_fetchers.py                  # Bible data fetchers (Hebrew/Greek)
│   ├── schemas.py                        # Pydantic request/response models
│   ├── init.sql                          # Initial DB schema SQL
│   ├── routers/                          # API route modules
│   │   ├── search.py                     # POST /api/search (streaming NDJSON)
│   │   ├── verses.py                     # GET /api/verse, /api/chapter, /api/strongs
│   │   ├── themes.py                     # POST /api/themes
│   │   ├── metadata.py                   # GET /api/translations, /api/books
│   │   └── health.py                     # GET /health
│   ├── scripts/                          # Data ingestion and utilities
│   │   ├── data_ingestion.py             # Bible text ingestion (9 translations)
│   │   ├── embeddings.py                 # Embedding generation
│   │   ├── original_ingestion.py         # Original language ingestion
│   │   ├── ingest_aramaic.py             # Aramaic-specific ingestion
│   │   ├── fetch_nkrv.py                 # Korean NKRV fetcher
│   │   └── verify_*.py                   # Verification utilities
│   ├── data/                             # Static data
│   │   └── books_metadata.py             # Bible book metadata
│   └── tests/                            # Test suite
│       ├── test_search.py
│       ├── test_cache.py
│       ├── test_llm.py
│       └── test_api_endpoints.py
├── frontend/                             # Next.js frontend
│   └── src/
│       ├── app/                          # Next.js pages (App Router)
│       │   ├── page.tsx                  # Home/chat page (main search interface)
│       │   ├── verse/[book]/[chapter]/[verse]/page.tsx  # Verse detail
│       │   ├── browse/page.tsx           # Browse by book
│       │   ├── compare/page.tsx          # Parallel translation comparison
│       │   └── themes/page.tsx           # Thematic search
│       ├── components/                   # React components
│       │   ├── ChatInput.tsx             # Chat message input bar
│       │   ├── ChatMessageBubble.tsx     # User/AI chat message display w/ inline citations
│       │   ├── VerseCard.tsx             # Verse display with context expand + cross-refs
│       │   ├── WelcomeScreen.tsx         # Initial landing state
│       │   ├── ParallelView.tsx          # Multi-translation side-by-side
│       │   ├── OriginalLanguage.tsx      # Greek/Hebrew interlinear display
│       │   ├── ChapterView.tsx           # Full chapter display
│       │   ├── KoreanToggle.tsx          # Hanja/romanization toggle
│       │   ├── APIKeySettings.tsx        # User API key configuration
│       │   ├── DarkModeToggle.tsx        # Dark/light theme toggle
│       │   ├── SearchMethodWarning.tsx   # Search method indicator
│       │   ├── Toast.tsx                 # Notification toasts
│       │   ├── Navbar.tsx                # Site navigation
│       │   └── TranslationsPreloader.tsx # Background translation fetcher
│       └── lib/
│           ├── api.ts                    # Typed API client (axios + streaming fetch)
│           └── verseParser.tsx           # Regex-based inline verse citation parser
├── docs/                                 # Comprehensive documentation
│   ├── ARCHITECTURE.md                   # System design
│   ├── DATABASE.md                       # Database schema
│   ├── API.md                            # API reference
│   ├── SETUP.md                          # Detailed setup guide
│   ├── DEPLOYMENT.md                     # Production deployment
│   ├── FEATURES.md                       # Feature documentation
│   ├── KOREAN.md                         # Korean-specific docs
│   └── DATA_SOURCES.md                   # Licensing and attribution
├── docker-compose.yml                    # Local development environment
└── README.md                             # This file
```

## Performance

- **Query Response Time**: < 2 seconds for initial search, < 500ms for cached queries
- **Reranking**: BAAI/bge-reranker-v2-m3 on top-30 RRF candidates (~50-200ms additional)
- **Embedding Generation**: ~15-30 minutes one-time setup for full Bible (~31,000 verses)
- **Vector Search**: pgvector ivfflat indexes for efficient cosine similarity
- **Caching**: Redis with fully normalized keys (lowercase, sorted translations, canonical JSON → MD5)

## Original Language Data Statistics

The project includes comprehensive original language coverage for the entire Bible:

| Language | Words Ingested | Verses Covered | Strong's Coverage | Source |
|----------|----------------|----------------|-------------------|--------|
| Greek (NT) | 137,500 | 7,957 | 99.9% | OpenGNT |
| Hebrew (OT) | 299,487 | ~23,145 | 98.1% | OSHB/WLC |
| Aramaic | 4,913 | ~68 | 98.0% | OSHB/WLC |
| **Total** | **442,413** | **~31,170** | **98.3%** | — |

**Aramaic Portions Covered**:
- Daniel 2:4-7:28 (Aramaic chapters)
- Ezra 4:8-6:18, 7:12-26 (official correspondence)
- Jeremiah 10:11 (single verse)
- Genesis 31:47 (two Aramaic words)

**Data Processing Speed**: ~8,043 words/second during ingestion

**Known Issues**: ~0.17% of Hebrew verses have numbering discrepancies between Hebrew and English versification systems (e.g., Joel 3 vs Joel 4, Daniel 3:31-33 vs Daniel 4:1-3). These verses are documented but not critical for overall functionality.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Bible Translations**:
  - [Bolls.life API](https://bolls.life) - Free access to NIV, ESV, NASB, KRV, and 100+ translations
  - [GetBible API](https://get.bible) - Public domain translations (KJV, WEB, RKV)
  - [SIR.kr Community](https://sir.kr) - 개역개정 (NKRV) MySQL database
  - 대한성서공회 (Korean Bible Society) - Korean translations copyright holder
- **Original Languages**:
  - [OpenGNT](https://github.com/eliranwong/OpenGNT) - Greek New Testament with Strong's numbers (CC BY 4.0)
  - [OSHB](https://github.com/openscriptures/morphhb) - Open Scriptures Hebrew Bible/Westminster Leningrad Codex (CC BY 4.0)
  - [OpenScriptures Strong's](https://github.com/openscriptures/strongs) - Strong's Concordance data (Public Domain)
  - Aramaic portions integrated via OSHB/WLC with manual detection
- **Cross-References**: [OpenBible.info](https://openbible.info) - 63,779+ verse connections (CC BY 4.0)
- **Embedding Model**: [intfloat/multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large)
- **Reranker Model**: [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- **LLM**: Google Gemini 2.5 Flash (primary), Groq Llama 3.3 70B (fallback)
