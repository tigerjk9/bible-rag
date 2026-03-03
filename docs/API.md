# Bible RAG - API Reference

Complete REST API documentation for the Bible RAG system.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [Search (Streaming)](#post-apisearch)
  - [Verse Lookup](#get-apiversebookchapterverse)
  - [Chapter Lookup](#get-apichapterbookchapter)
  - [Strong's Number Lookup](#get-apistrongsstrongs_number)
  - [Thematic Search](#post-apithemes)
  - [List Translations](#get-apitranslations)
  - [List Books](#get-apibooks)
  - [Health Check](#get-health)
- [Code Examples](#code-examples)

---

## Base URL

### Development
```
http://localhost:8000
```

### Production
```
https://api.bible-rag.yourdomain.com
```

All API endpoints are prefixed with `/api` unless otherwise noted.

---

## Authentication

The API does not require authentication for public read operations.

**User API Keys**: For LLM-powered responses, users can supply their own Gemini or Groq API keys via request headers. These are never stored server-side.

```http
X-Gemini-API-Key: AIza...
X-Groq-API-Key: gsk_...
```

When provided, these keys take priority over server-level environment keys.

---

## Rate Limiting

### LLM Rate Limits (Backend)

The backend enforces soft rate limits for LLM generation:

| Provider | RPM Limit |
|----------|-----------|
| Gemini 2.5 Flash (primary) | 10 |
| Groq Llama 3.3 70B (fallback) | 30 |

When both providers are rate-limited, search results are still returned — only the AI-generated response is skipped.

### Per-IP Limits (Production)

- **Per IP**: 60 requests/minute

### Rate Limit Response

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again in 30 seconds.",
    "retry_after": 30
  }
}
```

---

## Response Format

### Standard Success Response

Non-streaming endpoints return JSON with appropriate HTTP status codes.

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

### Streaming Response (Search)

`POST /api/search` returns **NDJSON** (newline-delimited JSON):

```http
HTTP/1.1 200 OK
Content-Type: application/x-ndjson
Transfer-Encoding: chunked
```

Each line is a complete JSON object:

| Event type | When emitted | Shape |
|------------|--------------|-------|
| `results` | After retrieval + reranking | `{"type": "results", "data": {...}}` |
| `token` | During LLM streaming | `{"type": "token", "content": "..."}` |
| `error` | On unhandled exception | `{"type": "error", "message": "..."}` |

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "query",
      "issue": "Query must be between 1 and 500 characters"
    }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `VERSE_NOT_FOUND` | 404 | Requested verse not found |
| `CHAPTER_NOT_FOUND` | 404 | Requested chapter not found |
| `STRONGS_NOT_FOUND` | 404 | No verses found for that Strong's number |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Endpoints

### POST /api/search

Performs hybrid semantic search across Bible translations with streaming response.

**Search pipeline**: Query expansion → vector + full-text hybrid retrieval → RRF fusion → cross-encoder reranking → LLM response generation.

#### Request

**Headers:**
```http
Content-Type: application/json
X-Gemini-API-Key: AIza...   (optional)
X-Groq-API-Key: gsk_...     (optional)
```

**Body:**
```json
{
  "query": "사랑과 용서",
  "languages": ["ko", "en"],
  "translations": ["개역개정", "NIV"],
  "include_original": true,
  "max_results": 10,
  "search_type": "semantic",
  "filters": {
    "testament": "NT",
    "genre": null,
    "books": null
  },
  "conversation_history": [
    {"role": "user", "content": "Tell me about grace"},
    {"role": "assistant", "content": "Grace is..."}
  ]
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | — | Search query (1-500 chars) |
| `languages` | string[] | No | `["en"]` | Language codes for response: `"en"`, `"ko"` |
| `translations` | string[] | Yes | — | Translation abbreviations (e.g. `"NIV"`, `"KRV"`) |
| `include_original` | boolean | No | `false` | Include Greek/Hebrew word data |
| `max_results` | integer | No | `10` | Max results (1-100) |
| `search_type` | string | No | `"semantic"` | `"semantic"` or `"keyword"` |
| `filters.testament` | string | No | `null` | `"OT"`, `"NT"`, or `"both"` |
| `filters.genre` | string | No | `null` | Filter by genre |
| `filters.books` | string[] | No | `null` | Filter by book abbreviations |
| `conversation_history` | ConversationTurn[] | No | `null` | Previous turns for multi-turn context |

**ConversationTurn:**
```json
{"role": "user" | "assistant", "content": "string (max 2000 chars)"}
```

#### Response (Streaming NDJSON)

The response is a stream of newline-delimited JSON objects. Consume line by line.

**Event 1 — Search results** (emitted first, before LLM):
```json
{
  "type": "results",
  "data": {
    "query_time_ms": 1245,
    "results": [
      {
        "reference": {
          "book": "Matthew",
          "book_korean": "마태복음",
          "book_abbrev": "Matt",
          "chapter": 6,
          "verse": 14,
          "testament": "NT",
          "genre": "gospel"
        },
        "translations": {
          "NIV": "For if you forgive other people...",
          "개역개정": "너희가 사람의 잘못을 용서하면..."
        },
        "relevance_score": 0.94,
        "cross_references": [
          {
            "book": "Mark",
            "book_korean": "마가복음",
            "chapter": 11,
            "verse": 25,
            "relationship": "parallel",
            "confidence": 0.9
          }
        ],
        "original": {
          "language": "greek",
          "words": [
            {
              "word": "ἀφῆτε",
              "transliteration": "aphēte",
              "strongs": "G863",
              "morphology": "V-AAS-2P",
              "definition": "to send away, forgive"
            }
          ]
        }
      }
    ],
    "search_metadata": {
      "total_results": 47,
      "embedding_model": "multilingual-e5-large",
      "generation_model": null,
      "cached": false,
      "search_method": "hybrid-rrf+rerank"
    }
  }
}
```

**Event 2+ — LLM tokens** (streamed as generated):
```json
{"type": "token", "content": "Based"}
{"type": "token", "content": " on"}
{"type": "token", "content": " these"}
```

**Error event:**
```json
{"type": "error", "message": "Database connection failed"}
```

**`search_metadata.search_method` values:**
- `"semantic"` — vector search only
- `"hybrid-rrf"` — vector + FTS merged via RRF, no reranker
- `"hybrid-rrf+rerank"` — full pipeline with cross-encoder reranking

#### cURL Example

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "love and forgiveness",
    "languages": ["en"],
    "translations": ["NIV"],
    "max_results": 5
  }' | while IFS= read -r line; do echo "$line" | python3 -m json.tool; done
```

---

### GET /api/verse/{book}/{chapter}/{verse}

Retrieves a specific verse in multiple translations with optional enrichments.

#### Request

**Path Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `book` | string | Book name or abbreviation | `John`, `요한복음`, `Matt` |
| `chapter` | integer | Chapter number | `3` |
| `verse` | integer | Verse number | `16` |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `translations` | string | No | All | Comma-separated abbreviations (e.g. `NIV,KRV`) |
| `include_original` | boolean | No | `false` | Include Greek/Hebrew data |
| `include_cross_refs` | boolean | No | `true` | Include cross-references |

#### Response

**Success (200 OK):**

```json
{
  "reference": {
    "book": "John",
    "book_korean": "요한복음",
    "book_abbrev": "John",
    "chapter": 3,
    "verse": 16,
    "testament": "NT",
    "genre": "gospel"
  },
  "translations": {
    "NIV": "For God so loved the world that he gave his one and only Son...",
    "ESV": "For God so loved the world, that he gave his only Son...",
    "KRV": "하나님이 세상을 이처럼 사랑하사 독생자를 주셨으니..."
  },
  "original": {
    "language": "greek",
    "words": [
      {
        "word": "ἠγάπησεν",
        "transliteration": "ēgapēsen",
        "strongs": "G25",
        "morphology": "V-AAI-3S",
        "definition": "to love, have affection for"
      }
    ]
  },
  "cross_references": [
    {
      "book": "1 John",
      "book_korean": "요한일서",
      "chapter": 4,
      "verse": 9,
      "relationship": "thematic",
      "confidence": 0.85
    }
  ],
  "context": null
}
```

#### cURL Example

```bash
curl "http://localhost:8000/api/verse/John/3/16?translations=NIV,KRV&include_original=true"
```

---

### GET /api/chapter/{book}/{chapter}

Retrieves all verses in a chapter.

#### Request

**Path Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `book` | string | Book name or abbreviation | `John`, `요한복음` |
| `chapter` | integer | Chapter number | `3` |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `translations` | string | No | All | Comma-separated abbreviations |
| `include_original` | boolean | No | `false` | Include Greek/Hebrew data |

#### Response

**Success (200 OK):**

```json
{
  "book": "John",
  "book_korean": "요한복음",
  "chapter": 3,
  "total_verses": 36,
  "verses": [
    {
      "verse": 1,
      "translations": {
        "NIV": "Now there was a Pharisee, a man named Nicodemus...",
        "KRV": "바리새인 중에 니고데모라 하는 사람이 있으니..."
      }
    }
  ]
}
```

Used by the frontend "± Context" button on VerseCard to display surrounding verses.

#### cURL Example

```bash
curl "http://localhost:8000/api/chapter/John/3?translations=NIV,KRV"
```

---

### GET /api/strongs/{strongs_number}

Looks up all Bible verses containing a specific Strong's concordance number.

#### Request

**Path Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `strongs_number` | string | Strong's number | `G25`, `H157`, `g25` (case-insensitive) |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `translations` | string | No | All non-original | Comma-separated abbreviations |
| `limit` | integer | No | `20` | Max verses to return (1-50) |

#### Response

**Success (200 OK):**

```json
{
  "strongs_number": "G25",
  "language": "greek",
  "definition": "to love, have affection for",
  "transliteration": "agapaō",
  "total_count": 143,
  "verses": [
    {
      "reference": {
        "book": "Matthew",
        "book_korean": "마태복음",
        "chapter": 5,
        "verse": 43,
        "testament": "NT",
        "genre": "gospel"
      },
      "translations": {
        "NIV": "You have heard that it was said, 'Love your neighbor...'",
        "KRV": "또 네 이웃을 사랑하고..."
      }
    }
  ]
}
```

**Error (404 Not Found):**
```json
{
  "error": {
    "code": "STRONGS_NOT_FOUND",
    "message": "No verses found for Strong's number G99999"
  }
}
```

Used by the frontend "Find all verses" link on Strong's number chips in OriginalLanguage.

#### cURL Example

```bash
curl "http://localhost:8000/api/strongs/G25?translations=NIV,KRV&limit=10"
```

---

### POST /api/themes

Performs thematic search across the Bible.

#### Request

**Body:**

```json
{
  "theme": "covenant",
  "testament": "both",
  "languages": ["en", "ko"],
  "translations": ["NIV", "KRV"],
  "max_results": 20
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `theme` | string | Yes | — | Theme keyword or phrase (1-100 chars) |
| `testament` | string | No | `"both"` | `"OT"`, `"NT"`, or `"both"` |
| `languages` | string[] | No | `["en"]` | Language codes |
| `translations` | string[] | Yes | — | Translation abbreviations |
| `max_results` | integer | No | `20` | Max results (1-100) |

#### Response

**Success (200 OK):**

```json
{
  "theme": "covenant",
  "testament_filter": "both",
  "query_time_ms": 890,
  "results": [
    {
      "reference": {...},
      "translations": {...},
      "relevance_score": 0.91,
      "cross_references": [...]
    }
  ],
  "related_themes": ["promise", "agreement", "testament"],
  "total_results": 156
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8000/api/themes \
  -H "Content-Type: application/json" \
  -d '{"theme": "faith", "testament": "NT", "translations": ["NIV"]}'
```

---

### GET /api/translations

Lists all available Bible translations.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `language` | string | No | All | Filter by language code (`en`, `ko`, `he`, `gr`) |

#### Response

**Success (200 OK):**

```json
{
  "translations": [
    {
      "id": "a1b2c3d4-...",
      "name": "New International Version",
      "abbreviation": "NIV",
      "language_code": "en",
      "language_name": "English",
      "description": null,
      "is_original_language": false,
      "verse_count": 31102
    },
    {
      "id": "b2c3d4e5-...",
      "name": "개역한글",
      "abbreviation": "KRV",
      "language_code": "ko",
      "language_name": "한국어",
      "description": null,
      "is_original_language": false,
      "verse_count": 31103
    }
  ],
  "total_count": 9
}
```

#### cURL Example

```bash
curl http://localhost:8000/api/translations
curl "http://localhost:8000/api/translations?language=ko"
```

---

### GET /api/books

Lists all 66 Bible books with metadata.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `testament` | string | No | All | Filter: `"OT"` or `"NT"` |
| `genre` | string | No | All | Filter by genre |

#### Response

**Success (200 OK):**

```json
{
  "books": [
    {
      "id": "d4e5f6g7-...",
      "name": "Genesis",
      "name_korean": "창세기",
      "abbreviation": "Gen",
      "testament": "OT",
      "genre": "law",
      "book_number": 1,
      "total_chapters": 50,
      "total_verses": 1533
    }
  ],
  "total_count": 66
}
```

#### cURL Example

```bash
curl http://localhost:8000/api/books
curl "http://localhost:8000/api/books?testament=NT&genre=gospel"
```

---

### GET /health

Health check endpoint for uptime monitoring.

#### Response

**Success (200 OK):**

```json
{
  "status": "healthy",
  "timestamp": "2026-03-02T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "embedding_model": "loaded"
  },
  "stats": {
    "total_verses": 31103,
    "total_translations": 9,
    "cache_hit_rate": 0.67
  }
}
```

**Unhealthy (503 Service Unavailable):**

```json
{
  "status": "unhealthy",
  "timestamp": "2026-03-02T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "unhealthy",
    "redis": "healthy",
    "embedding_model": "loaded"
  },
  "errors": ["Database connection failed"]
}
```

#### cURL Example

```bash
curl http://localhost:8000/health
```

---

## Code Examples

### JavaScript — Consuming Streaming Search

```javascript
const API_BASE = 'http://localhost:8000';

async function* streamSearch(query, translations = ['NIV']) {
  const response = await fetch(`${API_BASE}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, languages: ['en'], translations, max_results: 10 }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // incomplete line
    for (const line of lines) {
      if (line.trim()) yield JSON.parse(line);
    }
  }
}

// Usage
let aiText = '';
for await (const event of streamSearch('love and forgiveness')) {
  if (event.type === 'results') {
    console.log('Verses:', event.data.results);
  } else if (event.type === 'token') {
    aiText += event.content;
    process.stdout.write(event.content);
  }
}
```

### TypeScript — Typed API Client

```typescript
interface SearchRequest {
  query: string;
  languages?: string[];
  translations: string[];
  include_original?: boolean;
  max_results?: number;
  filters?: { testament?: string; genre?: string; books?: string[] };
  conversation_history?: Array<{ role: 'user' | 'assistant'; content: string }>;
}

interface VerseResult {
  reference: { book: string; book_korean?: string; chapter: number; verse: number; testament?: string; genre?: string };
  translations: Record<string, string>;
  relevance_score: number;
  cross_references?: Array<{ book: string; chapter: number; verse: number; relationship: string; confidence?: number }>;
  original?: { language: string; words: Array<{ word: string; transliteration?: string; strongs?: string; morphology?: string; definition?: string }> };
}

interface SearchResultsEvent {
  type: 'results';
  data: { query_time_ms: number; results: VerseResult[]; search_metadata: { total_results: number; cached: boolean; search_method: string } };
}

interface TokenEvent { type: 'token'; content: string; }
interface ErrorEvent { type: 'error'; message: string; }

type SearchEvent = SearchResultsEvent | TokenEvent | ErrorEvent;

async function* search(req: SearchRequest): AsyncGenerator<SearchEvent> {
  const resp = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  const reader = resp.body!.getReader();
  const dec = new TextDecoder();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop()!;
    for (const line of lines) {
      if (line.trim()) yield JSON.parse(line) as SearchEvent;
    }
  }
}
```

### Python — requests

```python
import requests
import json

API_BASE = 'http://localhost:8000'

def search_stream(query: str, translations: list[str] = None):
    """Stream search results from the Bible RAG API."""
    if translations is None:
        translations = ['NIV']

    with requests.post(
        f'{API_BASE}/api/search',
        json={'query': query, 'languages': ['en'], 'translations': translations},
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                event = json.loads(line)
                yield event

# Usage
ai_text = ''
for event in search_stream('love and forgiveness', ['NIV', 'KRV']):
    if event['type'] == 'results':
        for v in event['data']['results']:
            print(v['reference']['book'], v['reference']['chapter'], v['reference']['verse'])
    elif event['type'] == 'token':
        ai_text += event['content']
        print(event['content'], end='', flush=True)
```

### cURL — Full Flow

```bash
# Streaming search (NDJSON)
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "love and forgiveness", "languages": ["en"], "translations": ["NIV"], "max_results": 5}'

# Single verse
curl "http://localhost:8000/api/verse/John/3/16?translations=NIV,KRV&include_original=true" | jq

# Chapter
curl "http://localhost:8000/api/chapter/John/3?translations=NIV" | jq

# Strong's lookup
curl "http://localhost:8000/api/strongs/G25?translations=NIV&limit=10" | jq

# Translations list
curl http://localhost:8000/api/translations | jq

# Health check
curl http://localhost:8000/health | jq
```
