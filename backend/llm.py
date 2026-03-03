"""LLM integration for generating contextual responses.

Supports Google Gemini (primary) and Groq (fallback) for generating
AI-powered contextual responses based on search results.
"""

import logging
import time
from typing import Optional

from config import get_settings

settings = get_settings()

# Configure logging
logger = logging.getLogger(__name__)

# Rate limiting state
_rate_limit_state = {
    "gemini": {"count": 0, "reset_time": 0},
    "groq": {"count": 0, "reset_time": 0},
}


def _check_rate_limit(provider: str, limit: int) -> bool:
    """Check if we're within rate limits for a provider.

    Args:
        provider: 'gemini' or 'groq'
        limit: Requests per minute limit

    Returns:
        True if within limits, False if rate limited
    """
    current_time = time.time()
    state = _rate_limit_state[provider]

    # Reset counter if minute has passed
    if current_time - state["reset_time"] >= 60:
        state["count"] = 0
        state["reset_time"] = current_time

    if state["count"] >= limit:
        logger.warning(f"{provider.capitalize()} rate limit exceeded ({limit} RPM)")
        return False

    state["count"] += 1
    return True


async def expand_query(
    query: str,
    language: str = "en",
    groq_api_key: str | None = None,
    gemini_api_key: str | None = None,
) -> list[str]:
    """Expand a user query into multiple search-optimized sub-queries.

    Uses LLM to generate alternative phrasings that capture different
    semantic aspects of the question, improving retrieval recall.

    Args:
        query: Original user query
        language: Query language ('en' or 'ko')
        groq_api_key: Groq API key
        gemini_api_key: Gemini API key

    Returns:
        List of 3 alternative search queries, or empty list on failure.
    """
    import json as _json
    import re as _re

    if language == "ko":
        lang_instruction = (
            "Generate the queries in Korean, since the search index includes Korean Bible text.\n"
            "Example for '미지근한 믿음이란 무엇인가':\n"
            '["영적 무관심 하나님 헌신하지 않음", "라오디게아 교회 열정 없는 신앙", "온전한 헌신 열정 성화"]'
        )
    else:
        lang_instruction = (
            "Example for 'what does it mean to be lukewarm':\n"
            '["spiritual indifference half-hearted commitment God", "neither devoted nor opposed Laodicea church", '
            '"zeal fervency wholehearted faith obedience"]'
        )

    prompt = (
        "You are a Bible study assistant improving search retrieval. "
        "Generate exactly 3 short search queries (3-8 words each) to find the most relevant Bible verses.\n\n"
        "Rules:\n"
        "1. If the question uses a metaphor, symbol, or figurative language (e.g. 'lukewarm', 'salt of the earth', "
        "'born again', 'prodigal'), translate it to the underlying spiritual or theological concept first "
        "(e.g. 'lukewarm' → 'spiritual indifference half-hearted faith commitment').\n"
        "2. Use vocabulary that would actually appear in Bible verses — "
        "not the user's metaphor, but the concepts behind it.\n"
        "3. Cover three distinct angles: the core spiritual concept, a related biblical theme, "
        "and a practical/moral dimension.\n\n"
        f"Question: {query}\n\n"
        f"{lang_instruction}\n\n"
        "Respond with ONLY a JSON array of 3 strings, no other text."
    )

    # Try Groq first (faster)
    groq_key = groq_api_key or settings.groq_api_key
    if groq_key and _check_rate_limit("groq", settings.groq_rpm):
        try:
            from groq import AsyncGroq

            client = AsyncGroq(api_key=groq_key)
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()
            # Strip markdown code fences if present (e.g. ```json ... ```)
            text = _re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
            parsed = _json.loads(text)
            if isinstance(parsed, list) and all(isinstance(q, str) for q in parsed):
                logger.info(f"Query expansion (Groq): {query!r} → {parsed}")
                return parsed[:3]
        except Exception as e:
            logger.warning(f"Groq query expansion failed: {e}")

    # Fallback to Gemini
    gemini_key = gemini_api_key or settings.gemini_api_key
    if gemini_key and _check_rate_limit("gemini", settings.gemini_rpm):
        try:
            import google.generativeai as genai

            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = await model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=200,
                    temperature=0.3,
                ),
            )
            text = response.text.strip()
            text = _re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
            parsed = _json.loads(text)
            if isinstance(parsed, list) and all(isinstance(q, str) for q in parsed):
                logger.info(f"Query expansion (Gemini): {query!r} → {parsed}")
                return parsed[:3]
        except Exception as e:
            logger.warning(f"Gemini query expansion failed: {e}")

    logger.info(f"Query expansion skipped for: {query!r}")
    return []


def _format_conversation_history(
    conversation_history: list[dict] | None, language: str = "en"
) -> str:
    """Format conversation history for inclusion in the prompt.

    Takes the last 5 turns and truncates long messages.
    """
    if not conversation_history:
        return ""

    recent = conversation_history[-10:]  # last 5 pairs max
    lines = []
    for turn in recent:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        # Truncate long assistant responses to preserve follow-up context
        if len(content) > 600:
            content = content[:600] + "..."
        label = "User" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")

    history_text = "\n".join(lines)

    if language == "ko":
        return f"\n이전 대화:\n{history_text}\n"
    else:
        return f"\nPrevious conversation:\n{history_text}\n"


def _build_prompt(
    query: str,
    verses: list[dict],
    language: str = "en",
    conversation_history: list[dict] | None = None,
) -> str:
    """Build the prompt for LLM response generation.

    Args:
        query: User's search query
        verses: List of verse result dictionaries
        language: Response language ('en' or 'ko')
        conversation_history: Previous conversation turns for context

    Returns:
        Formatted prompt string
    """
    verse_context = []
    for i, v in enumerate(verses, 1):
        ref = v.get("reference", {})
        translations = v.get("translations", {})
        cross_refs = v.get("cross_references", [])
        relevance = v.get("relevance_score")
        original = v.get("original")

        # Build ref label with genre/testament and relevance score
        book = ref.get("book", "")
        chapter = ref.get("chapter", "")
        verse_num = ref.get("verse", "")
        testament = ref.get("testament", "")
        genre = ref.get("genre", "")

        ref_label = f"{book} {chapter}:{verse_num}"
        meta_parts = []
        if testament:
            meta_parts.append(testament)
        if genre:
            meta_parts.append(genre.capitalize())
        if relevance is not None:
            meta_parts.append(f"relevance: {relevance:.2f}")
        if meta_parts:
            ref_label += f" [{', '.join(meta_parts)}]"

        # Include all available translation texts (no truncation)
        translation_lines = []
        for abbrev, text in translations.items():
            if text:
                translation_lines.append(f"  [{abbrev}] {text}")
        translations_block = "\n".join(translation_lines) if translation_lines else "  (no text)"

        # Original language data (Greek/Hebrew words with Strong's numbers)
        orig_line = ""
        if original and original.get("words"):
            lang_name = original.get("language", "").capitalize()
            word_parts = []
            for w in original["words"][:6]:
                word = w.get("word", "")
                translit = w.get("transliteration", "")
                strongs = w.get("strongs", "")
                defn = w.get("definition", "")
                parts = [p for p in [word, translit, strongs, defn] if p]
                if parts:
                    word_parts.append(" / ".join(parts))
            if word_parts:
                orig_line = f"  Original ({lang_name}): {' | '.join(word_parts)}"

        # Include cross-references with relationship type
        xref_parts = []
        for xr in cross_refs[:3]:
            xr_book = xr.get("book", xr.get("book_en", ""))
            xr_ch = xr.get("chapter", "")
            xr_v = xr.get("verse", "")
            rel = xr.get("relationship", "")
            if xr_book and xr_ch and xr_v:
                xref_parts.append(f"{xr_book} {xr_ch}:{xr_v} ({rel})" if rel else f"{xr_book} {xr_ch}:{xr_v}")
        xref_line = f"  Cross-refs: {', '.join(xref_parts)}" if xref_parts else ""

        entry = f"{i}. {ref_label}\n{translations_block}"
        if orig_line:
            entry += f"\n{orig_line}"
        if xref_line:
            entry += f"\n{xref_line}"
        verse_context.append(entry)

    verses_text = "\n\n".join(verse_context)
    verse_count = len(verses)
    history_section = _format_conversation_history(conversation_history, language)

    if language == "ko":
        prompt = f"""다음 성경 구절들을 바탕으로 질문에 적합한 깊이로 답변해 주세요.
{history_section}
질문: {query}

관련 성경 구절 ({verse_count}개):
{verses_text}

답변 지침:
- 아래 제공된 구절 목록에 있는 구절만 인용하세요. 목록에 없는 구절을 만들어내거나 추측하지 마세요.
- 각 구절 아래 나열된 교차 참조는 참고용일 뿐입니다 — 목록에 없는 구절의 내용을 추론하거나 인용하는 데 사용하지 마세요.
- 구절이 질문과 실질적으로 관련될 때만 사용하세요. 표면적인 단어만 공유하는 구절은 제외하세요 (예: 영적 개념을 묻는 질문에 물리적 의미만 있는 구절 제외).
- 질문의 깊이에 맞게 답변해 주세요 — 짧은 질문은 간결하게, 심층 질문은 자세히.
- 특정 구절을 인용할 때는 책 이름과 장:절을 명시해 주세요 (예: "로마서 12:9에 따르면...")
- 본문의 구조, 문학적 장치, 신학적 의미를 분석해 주세요. 장르(시가, 서신서, 예언서)도 고려하세요.
- 역사적·문화적 맥락이 있다면 포함해 주세요.
- 원어 데이터(히브리어/헬라어)가 제공된 경우, 본문 이해에 도움이 되는 단어 의미를 설명에 활용하세요.
- 결론은 간결하게 — 이미 말한 내용을 반복하지 마세요.
- 각 문장은 새로운 정보를 추가해야 합니다.
- 마크다운 형식(굵게, 제목, 목록)은 복잡한 다중 주제 분석에만 사용하세요 — 간단한 질문은 자연스러운 문장으로 답하세요.
- 답변이 완전한 문장으로 끝나도록 해 주세요.
- 이전 대화가 있다면 맥락을 고려하여 답변해 주세요."""
    else:
        prompt = f"""Based on the following Bible verses, answer the question at the appropriate depth.
{history_section}
Question: {query}

Provided verses ({verse_count} total):
{verses_text}

Instructions:
- IMPORTANT: Only cite verses that appear in the provided list above. Do not invent, assume, or reference any verses not listed here.
- Cross-references listed under each verse are for context only — do not use them to infer the content of verses not in the provided list, and do not cite cross-referenced verses as sources.
- Only use a verse if it is genuinely relevant to the question — skip verses that share only a surface-level word but not the actual concept being asked about.
- Match response depth to the question — brief questions get concise answers; deep study questions get full analysis.
- When citing, use exact references (e.g., 'According to Psalm 1:3...')
- Analyze the text's structure, literary devices, and theological significance; note the genre (poetry, epistle, prophecy, narrative) where it affects interpretation.
- Include relevant historical or cultural context where applicable.
- If original language data is provided for a verse, incorporate key word meanings (e.g., Greek ἀγάπη / agape) where they illuminate the text.
- Cover all key elements — do not skip later verses if they add distinct points.
- Conclude with a brief, non-repetitive takeaway.
- Do not repeat points already made; each sentence should add new information.
- Use markdown formatting (bold, headers, lists) only for complex multi-part analyses — not for conversational or single-topic questions, which should be flowing prose.
- Ensure your response ends with proper punctuation.
- If there is previous conversation context, take it into account."""

    return prompt


async def generate_response_stream_gemini(
    query: str,
    verses: list[dict],
    language: str = "en",
    api_key: str | None = None,
    conversation_history: list[dict] | None = None,
) -> any:  # Returns an async generator
    """Generate a streaming response using Google Gemini."""
    gemini_key = api_key or settings.gemini_api_key
    if not gemini_key or not _check_rate_limit("gemini", settings.gemini_rpm):
        yield None
        return

    try:
        import google.generativeai as genai

        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=(
                "You are a knowledgeable Bible study assistant. Provide accurate, well-grounded answers "
                "calibrated to the depth of the question — concise for simple questions, detailed for deep study. "
                "CRITICAL: Only cite verses explicitly provided in the user's context. "
                "Never invent, fabricate, or assume references to verses not listed. "
                "Cross-references listed under verses are context only — never use them to infer or cite unlisted verses. "
                "Respond in the same language as the user's question. "
                "Analyze structure, literary devices, theological significance, and historical context where relevant. "
                "Use markdown formatting only for complex multi-part analyses — simple or conversational questions should be flowing prose. "
                "Responses must be complete and end with proper punctuation."
            )
        )

        prompt = _build_prompt(query, verses, language, conversation_history)
        
        # Async streaming is supported in newer genai versions or we can use ThreadPool
        # For true async in Python with genai, check library support. 
        # current google-generativeai supports generate_content(stream=True) which returns a sync iterator.
        # To stream asynchronously, we might need to wrap it or use their async client if available.
        # As of recent versions, genai.generate_content_async is available.
        
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=2048,
                temperature=0.3,
            ),
            stream=True
        )
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        logger.error(f"Gemini Streaming error: {e}")
        yield None


async def generate_response_stream_groq(
    query: str,
    verses: list[dict],
    language: str = "en",
    api_key: str | None = None,
    conversation_history: list[dict] | None = None,
) -> any:  # Returns an async generator
    """Generate a streaming response using Groq."""
    groq_key = api_key or settings.groq_api_key
    if not groq_key or not _check_rate_limit("groq", settings.groq_rpm):
        yield None
        return

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=groq_key)
        # Pass conversation_history=None here — Groq receives history via the messages[] array below
        prompt = _build_prompt(query, verses, language, conversation_history=None)

        # Build messages array with conversation history for Groq's chat format
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a knowledgeable Bible study assistant. Provide accurate, well-grounded answers "
                    "calibrated to the depth of the question — concise for simple questions, detailed for deep study. "
                    "CRITICAL: Only cite verses explicitly provided in the user's context. "
                    "Never invent, fabricate, or assume references to verses not listed. "
                    "Respond in the same language as the user's question. "
                    "Analyze structure, literary devices, theological significance, and historical context where relevant. "
                    "Use markdown formatting only for complex multi-part analyses — simple or conversational questions should be flowing prose. "
                    "Responses must be complete and end with proper punctuation."
                ),
            },
        ]
        # Inject conversation history as prior messages
        if conversation_history:
            for turn in conversation_history[-10:]:
                messages.append({
                    "role": turn.get("role", "user"),
                    "content": turn.get("content", "")[:500],
                })
        messages.append({"role": "user", "content": prompt})

        stream = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=2048,
            temperature=0.3,
            stream=True,
        )

        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    except Exception as e:
        logger.error(f"Groq Streaming error: {e}")
        yield None


async def generate_contextual_response_stream(
    query: str,
    verses: list[dict],
    language: str = "en",
    gemini_api_key: str | None = None,
    groq_api_key: str | None = None,
    conversation_history: list[dict] | None = None,
):
    """Generate a streaming contextual response."""
    if not verses:
        yield None
        return

    # Try Groq first
    try:
        groq_gen = generate_response_stream_groq(query, verses, language, api_key=groq_api_key, conversation_history=conversation_history)
        
        # Check if we get any content effectively
        # Since it is a generator, we iterate. Use a flag.
        first_chunk = True
        async for chunk in groq_gen:
            if chunk is None:
                break # Failed
            yield chunk
            first_chunk = False
        
        if not first_chunk:
            return  # Success

    except Exception as e:
        logger.error(f"Groq stream failed: {e}")

    # Fallback to Gemini
    try:
        gemini_gen = generate_response_stream_gemini(query, verses, language, api_key=gemini_api_key, conversation_history=conversation_history)
        async for chunk in gemini_gen:
            if chunk is None:
                break
            yield chunk
    except Exception as e:
        logger.error(f"Gemini stream failed: {e}")


def generate_contextual_response(
    query: str,
    verses: list[dict],
    language: str = "en",
    gemini_api_key: str | None = None,
    groq_api_key: str | None = None,
) -> Optional[str]:
    """Generate a contextual response (synchronous wrapper/shim for compatibility).
    
    This function exists primarily for backward compatibility and tests.
    It does NOT support streaming and may not work fully in async context without event loop.
    For production, use generate_contextual_response_stream.
    """
    # For now, return None to satisfy imports, or implement a blocking call if needed.
    # Since we moved to async, a sync call is tricky. 
    # Return None is safest for "fallback" behavior if tests expect Optional[str].
    return None

def detect_language(text: str) -> str:
    """Detect the language of input text.

    Simple heuristic based on character ranges.

    Args:
        text: Input text to analyze

    Returns:
        'ko' for Korean, 'en' for English/other
    """
    korean_chars = 0
    total_chars = 0

    for char in text:
        if char.isalpha():
            total_chars += 1
            # Korean Unicode range
            if "\uac00" <= char <= "\ud7a3" or "\u3131" <= char <= "\u3163":
                korean_chars += 1

    if total_chars == 0:
        return "en"

    # If more than 30% Korean characters, consider it Korean
    if korean_chars / total_chars > 0.3:
        return "ko"

    return "en"
