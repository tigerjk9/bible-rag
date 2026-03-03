# Bible RAG - Features Documentation

Comprehensive guide to all features of the Bible RAG system with examples and usage tips.

## Table of Contents

- [Chat Interface](#chat-interface)
- [Semantic Search](#semantic-search)
- [Multi-Translation Support](#multi-translation-support)
- [Parallel Translation View](#parallel-translation-view)
- [Original Language Integration](#original-language-integration)
- [Korean-Specific Features](#korean-specific-features)
- [Cross-Reference Discovery](#cross-reference-discovery)
- [Context Expansion](#context-expansion)
- [Inline Verse Citations](#inline-verse-citations)
- [Strong's Number Lookup](#strongs-number-lookup)
- [Theological Term Glossary](#theological-term-glossary)
- [Smart Query Understanding](#smart-query-understanding)
- [Browse & Navigation](#browse--navigation)
- [Advanced Search Filters](#advanced-search-filters)
- [User API Keys](#user-api-keys)
- [Dark Mode](#dark-mode)

---

## Chat Interface

Bible RAG uses a **conversational chat interface** as its primary UX. Searches feel like a dialogue, not a form submission.

### How It Works

1. Type a question or query in the message input
2. Verse results appear immediately (while AI is still generating)
3. AI response streams in token by token below the verse cards
4. Follow-up questions can reference the previous context

### Conversation History

The system maintains conversation context within a session. Follow-up queries are sent with `conversation_history`, allowing the LLM to give contextually aware responses:

```
Turn 1: "What does the Bible say about forgiveness?"
         → 10 relevant verses + AI explanation

Turn 2: "What about forgiving enemies specifically?"
         → Refined results with context from Turn 1
```

### Streaming Response

The API returns a streaming NDJSON response:
1. **Verse cards** render immediately when retrieval completes (~1-2s)
2. **AI tokens** stream in gradually as the LLM generates them

This keeps the interface responsive even for long AI responses.

---

## Semantic Search

### How It Works

Semantic search understands the **meaning** of your query, not just keywords. The system uses a multi-stage pipeline:

1. **Query expansion**: LLM generates 3 alternative phrasings of your query
2. **Embedding**: multilingual-e5-large converts all phrasings to 1024-dim vectors
3. **Hybrid retrieval**: vector similarity + full-text search run in parallel
4. **RRF fusion**: Reciprocal Rank Fusion merges both result lists
5. **Reranking**: BAAI/bge-reranker-v2-m3 cross-encoder rescores top-30 candidates

**Traditional keyword search:**
- Query: "love" → Only finds verses containing the exact word "love"

**Semantic search:**
- Query: "love" → Finds verses about love, compassion, charity, affection, devotion

### Example Queries

#### English Queries

```
"What does Jesus say about forgiveness?"
→ Matthew 6:14-15, Luke 6:37, Mark 11:25, Matthew 18:21-22

"faith and works"
→ James 2:14-26, Ephesians 2:8-10, Galatians 5:6

"comfort during difficult times"
→ Psalm 23, Matthew 11:28-30, 2 Corinthians 1:3-4
```

#### Korean Queries (한국어 검색)

```
"사랑에 대한 예수님의 가르침"
→ 요한복음 13:34-35, 마태복음 22:37-40, 요한일서 4:7-12

"어려울 때 위로받는 말씀"
→ 시편 23편, 마태복음 11:28-30, 고린도후서 1:3-4
```

#### Mixed Language Queries (코드 스위칭)

```
"요한복음에서 love에 대한 구절"
→ John 13:34-35, John 15:12-13

"What did 바울 say about grace?"
→ Romans 3:23-24, Ephesians 2:8-9
```

### Tips for Best Results

1. **Be specific**: "God's unconditional love for humanity" over "love"
2. **Ask questions naturally**: "What does the Bible say about worry?"
3. **Use context**: "Jesus' teaching about prayer in the Sermon on the Mount"
4. **Combine concepts**: "faith, hope, and love"

---

## Multi-Translation Support

### Available Translations

#### English Translations

| Abbreviation | Name | Style | Year |
|--------------|------|-------|------|
| **NIV** | New International Version | Contemporary, balanced | 2011 |
| **ESV** | English Standard Version | Literal, literary | 2001 |
| **NASB** | New American Standard Bible | Very literal | 1995 |
| **KJV** | King James Version | Classical | 1611 |
| **WEB** | World English Bible | Modern public domain | 2000 |

#### Korean Translations (한국어 번역)

| Abbreviation | Name | Style | Year |
|--------------|------|-------|------|
| **KRV** | 개역한글 | Traditional Korean Protestant | 1961 |
| **RNKSV** | 새번역 | Contemporary Korean | 2004 |
| **NKRV** | 개역개정 | Standard Korean Protestant (optional) | 1998 |

#### Original Languages

| Abbreviation | Name | Testament |
|--------------|------|-----------|
| **SBLGNT** | SBL Greek New Testament | NT |
| **WLC** | Westminster Leningrad Codex | OT |

### Translation Comparison

Different translations provide different perspectives:

**Example: Philippians 4:13**

- **NIV:** "I can do all this through him who gives me strength."
- **ESV:** "I can do all things through him who strengthens me."
- **개역한글:** "내게 능력 주시는 자 안에서 내가 모든 것을 할 수 있느니라"
- **새번역:** "나를 능력 있게 하시는 분 안에서, 나는 모든 것을 할 수 있습니다"

---

## Parallel Translation View

View the same verse in multiple translations side-by-side.

```
┌─────────────────────────────────────────────────────────────────┐
│ John 3:16 (요한복음 3:16)                                         │
├─────────────────────────────────────────────────────────────────┤
│ [EN-NIV]                                                         │
│ For God so loved the world that he gave his one and only Son,   │
│ that whoever believes in him shall not perish but have eternal  │
│ life.                                                            │
├─────────────────────────────────────────────────────────────────┤
│ [KO-개역한글]                                                     │
│ 하나님이 세상을 이처럼 사랑하사 독생자를 주셨으니 이는 그를      │
│ 믿는 자마다 멸망하지 않고 영생을 얻게 하려 하심이라              │
├─────────────────────────────────────────────────────────────────┤
│ [GR-Original]                                                    │
│ οὕτως γὰρ ἠγάπησεν ὁ θεὸς τὸν κόσμον                          │
└─────────────────────────────────────────────────────────────────┘
```

The `/compare` page offers a dedicated parallel view for any verse reference across all selected translations.

---

## Original Language Integration

### Greek (New Testament)

**Strong's numbers** (G1-G5624) tag every Greek word.

**Example: ἀγαπάω (agapaō) — "to love"**

```
Strong's: G25
Transliteration: agapaō
Morphology: V-AAI-3S (Verb, Aorist, Active, Indicative, 3rd person, Singular)
Definition: to love, to have affection for, to welcome, to be fond of
```

**Morphological Parsing Codes:**

| Code | Meaning |
|------|---------|
| V | Verb |
| N | Noun |
| A | Adjective |
| AAI | Aorist, Active, Indicative |
| 3S | 3rd person, Singular |
| NSM | Nominative, Singular, Masculine |

### Hebrew (Old Testament)

**Strong's numbers** (H1-H8674) tag every Hebrew word.

**Example: אָהַב (ahav) — "to love"**

```
Strong's: H157
Transliteration: 'ahab
Root: אהב
Definition: to love, to have affection
```

### Aramaic (Daniel, Ezra portions)

Aramaic words in Daniel 2-7, Ezra 4-7, Jeremiah 10:11, and Genesis 31:47 are tagged with the same H-series Strong's numbers used for Hebrew.

### Word Study Example

**John 21:15-17 — Two Greek Words for "Love"**

This passage uses two different Greek verbs:
- `ἀγαπάω` (agapaō, G25) — divine/unconditional love
- `φιλέω` (phileō, G5368) — friendship/natural affection

The distinction is visible in the original language panel, showing how translation choices obscure a theologically significant nuance.

---

## Korean-Specific Features

### Hanja (한자) Display

Shows Chinese characters for theological terms, revealing their literal meaning:

```
속죄 (贖罪) — 贖 = to ransom, 罪 = sin/crime
구원 (救援) — 救 = to save, 援 = to aid
은혜 (恩惠) — 恩 = grace/favor, 惠 = benefit
믿음 (信)   — 信 = faithfulness/trust
```

Toggle on in the Korean settings panel.

### Romanization

Displays Korean pronunciation in Roman letters, generated via the `aromanize` library:

```
Original:    하나님이 세상을 이처럼 사랑하사
Romanized:   Hananim-i sesang-eul icheoreom saranghasa
```

Useful for Korean learners and pronunciation practice.

### Typography Optimization

Korean text has special formatting requirements:

| Setting | Korean | English |
|---------|--------|---------|
| Line height | 1.8-2.0 | 1.5 |
| Min font size | 16px | 14px |
| Font | Noto Sans KR | System sans-serif |

### Honorific Language

Korean speech level is context-sensitive. The system uses appropriate honorifics when referring to God and biblical figures:

- **하나님께서** (honorific subject marker, not 하나님이)
- **말씀하시다** (honorific verb, not 말하다)
- **드리다** (humble form of give)

---

## Cross-Reference Discovery

Cross-references are sourced from OpenBible.info (63,779+ connections). They are grouped by relationship type in the VerseCard.

### Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| **quotation** | NT directly quotes OT | Matt 22:37 quoting Deut 6:5 |
| **prophecy-fulfillment** | OT prophecy + NT fulfillment | Isaiah 7:14 → Matthew 1:23 |
| **parallel** | Same event in different gospels | Matthew 14:13-21 ∥ Mark 6:30-44 |
| **allusion** | Indirect reference | Many Psalm echoes in NT |
| **thematic** | Related concept | Hebrews 11:1 with Romans 10:17 |

### Display

Cross-references appear below the verse text with:
- Colored relationship type labels (e.g. blue = parallel, orange = prophecy)
- Confidence qualifier when `confidence < 0.8` (e.g. "possible")
- Click to navigate to the referenced verse

---

## Context Expansion

The **"± Context"** button on each VerseCard shows the surrounding passage inline.

### How It Works

1. Click "± Context" on any verse card
2. The frontend calls `GET /api/chapter/{book}/{chapter}`
3. Slices ±2 verses around the target verse
4. Renders them **dimmed** above and below the highlighted target verse

**Example for Matthew 6:14:**
```
(dimmed) Matt 6:12 — And forgive us our debts...
(dimmed) Matt 6:13 — And lead us not into temptation...
[HIGHLIGHTED] Matt 6:14 — For if you forgive other people...
(dimmed) Matt 6:15 — But if you do not forgive others...
(dimmed) Matt 6:16 — When you fast, do not look somber...
```

---

## Inline Verse Citations

After the AI response finishes streaming, `verseParser.tsx` scans the text for verse references and converts them into **clickable inline VerseCard components**.

### Recognized Formats

- `John 3:16` / `John 3:16-18`
- `요한복음 3:16` / `요한복음 3:16-18`
- `Matt 6:14`, `Ps 23:1`, `Gen 1:1`

### Behavior

- References become expandable inline cards
- Cards show the verse in the currently selected translations
- All VerseCard features (original language, cross-refs, context expand) are available inline

---

## Strong's Number Lookup

From any word in the original language panel, click the Strong's number chip (e.g. **G25**) to open a "Find all verses" panel.

### How It Works

1. Click a Strong's number (e.g. `G25 ἀγαπάω`)
2. The app navigates to `/?strongs=G25`
3. Calls `GET /api/strongs/G25`
4. Displays word definition, language, transliteration
5. Lists all verses containing that word (up to 50, paginated)

### Use Cases

- Study every occurrence of a key word across the entire Bible
- Compare how a Greek/Hebrew concept appears in different contexts
- Build word studies without a separate concordance tool

---

## Theological Term Glossary

Korean → English → Original Language mapping:

```
속죄 (sokjoe)        = Atonement      = כָּפַר (kaphar, H3722)
구원 (guwon)         = Salvation      = σωτηρία (soteria, G4991)
은혜 (eunhye)        = Grace          = χάρις (charis, G5485)
믿음 (mideum)        = Faith          = πίστις (pistis, G4102)
의 (ui)              = Righteousness  = δικαιοσύνη (dikaiosunē, G1343)
성령 (seongryeong)   = Holy Spirit    = πνεῦμα ἅγιον (pneuma hagion)
회개 (hoegae)        = Repentance     = μετάνοια (metanoia, G3341)
구속 (gusok)         = Redemption     = ἀπολύτρωσις (apolytrōsis, G629)
```

---

## Smart Query Understanding

### Language Detection

The system automatically detects query language:

```
"love"                   → en → search English translations
"사랑"                   → ko → search Korean translations
"love and 믿음"          → mixed → search both
```

### Query Expansion

Before searching, the LLM generates 3 alternative phrasings to improve recall:

**Query:** "What did Jesus say about prayer?"

**Expanded to:**
1. "Jesus teaching on prayer mountain sermon"
2. "pray without ceasing disciples ask"
3. "Lord's Prayer Our Father kingdom come"

All four phrasings are searched in parallel; results are merged via RRF.

---

## Browse & Navigation

### Browse by Book (`/browse`)

Navigate the Bible by testament → book → chapter → verse. Useful for reading passages in context rather than searching.

### Browse by Genre

Filter books by literary genre:

**Old Testament:** law, history, wisdom, poetry, prophecy
**New Testament:** gospel, history, epistle, prophecy

### Verse Detail Page (`/verse/{book}/{chapter}/{verse}`)

Full detail view for any verse: all translations side-by-side, complete original language panel, all cross-references, surrounding context.

### Compare Page (`/compare`)

Enter any verse reference to see all available translations in a clean parallel grid.

### Themes Page (`/themes`)

Browse Bible by theological theme. Calls `POST /api/themes` for curated thematic results.

---

## Advanced Search Filters

### Filter by Testament

```
Filters: { testament: "NT" }
→ Results limited to New Testament verses
```

### Filter by Genre

```
Filters: { genre: "wisdom" }
→ Results from Proverbs, Ecclesiastes, Job, Psalms (wisdom psalms)
```

### Filter by Specific Books

```
Filters: { books: ["Romans", "Hebrews", "James"] }
→ Results only from these three books
```

### Combine Filters

```
Query: "Jesus healing"
Filters: { testament: "NT", genre: "gospel" }
→ Gospel healing accounts only
```

---

## User API Keys

Users can provide their own Gemini and/or Groq API keys for LLM-powered responses.

### How It Works

1. Click the settings icon in the interface
2. Enter your personal Gemini API key and/or Groq API key
3. Keys are held in frontend state for the session
4. Each search request sends keys as HTTP headers:
   ```http
   X-Gemini-API-Key: AIza...
   X-Groq-API-Key: gsk_...
   ```
5. Keys are **never** stored server-side or in localStorage
6. Clearing the field removes the key from requests

### Why Provide Your Own Keys?

- Remove server-level rate limits (shared across all users)
- Use higher-quota tiers
- Keep usage billed to your own account

---

## Dark Mode

The interface supports system-aware dark and light themes.

- Automatically matches system preference on first load
- Toggle manually via the moon/sun icon in the navbar
- Preference persists via localStorage across page reloads
- Applied to all pages: chat, browse, compare, themes, verse detail
