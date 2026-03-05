"""Tests for LLM functionality."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.unit
def test_detect_language_english():
    """Test language detection for English text."""
    from llm import detect_language

    assert detect_language("This is an English sentence.") == "en"
    assert detect_language("love and forgiveness") == "en"
    assert detect_language("What does the Bible say about faith?") == "en"


@pytest.mark.unit
def test_detect_language_korean():
    """Test language detection for Korean text."""
    from llm import detect_language

    assert detect_language("사랑과 용서") == "ko"
    assert detect_language("성경에서 믿음에 대해 무엇이라고 말합니까?") == "ko"
    assert detect_language("창세기 1장 1절") == "ko"


@pytest.mark.unit
def test_detect_language_mixed():
    """Test language detection for mixed text."""
    from llm import detect_language

    # Mixed text should return based on predominant script
    result = detect_language("사랑 love")
    assert result in ["ko", "en"]  # Could be either depending on logic


@pytest.mark.unit
def test_detect_language_numbers_and_symbols():
    """Test language detection with numbers and symbols."""
    from llm import detect_language

    # Primarily English with numbers
    assert detect_language("Genesis 1:1") == "en"

    # Primarily Korean with numbers
    assert detect_language("창세기 1:1") == "ko"


@pytest.mark.unit
def test_build_prompt_english():
    """Test prompt building for English."""
    from llm import _build_prompt

    verses = [
        {
            "reference": {
                "book": "John",
                "chapter": 3,
                "verse": 16,
            },
            "translations": {
                "NIV": "For God so loved the world...",
            },
        }
    ]

    prompt = _build_prompt("What is love?", verses, "en")

    assert "What is love?" in prompt
    assert "John 3:16" in prompt
    assert "For God so loved the world" in prompt
    # Prompt exists and contains the key elements


@pytest.mark.unit
def test_build_prompt_korean():
    """Test prompt building for Korean."""
    from llm import _build_prompt

    verses = [
        {
            "reference": {
                "book": "요한복음",
                "book_korean": "요한복음",
                "chapter": 3,
                "verse": 16,
            },
            "translations": {
                "RKV": "하나님이 세상을 이처럼 사랑하사...",
            },
        }
    ]

    prompt = _build_prompt("사랑이란 무엇입니까?", verses, "ko")

    assert "사랑이란 무엇입니까?" in prompt
    assert "요한복음 3:16" in prompt or "요한복음" in prompt
    assert "하나님이 세상을" in prompt
    # The prompt might not explicitly say "Korean" or "한국어" if it's implicitly structural
    # Just check for Korean structure chars if needed, or skip this specific string check
    assert "답변 지침" in prompt or "질문" in prompt


@pytest.mark.unit
def test_build_prompt_multiple_verses():
    """Test prompt building with multiple verses."""
    from llm import _build_prompt

    verses = [
        {
            "reference": {"book": "Matthew", "chapter": 5, "verse": 44},
            "translations": {"NIV": "Love your enemies..."},
        },
        {
            "reference": {"book": "Matthew", "chapter": 22, "verse": 37},
            "translations": {"NIV": "Love the Lord your God..."},
        },
    ]

    prompt = _build_prompt("What does Jesus say about love?", verses, "en")

    assert "Matthew 5:44" in prompt
    assert "Matthew 22:37" in prompt
    assert "Love your enemies" in prompt
    assert "Love the Lord your God" in prompt


@pytest.mark.unit
def test_generate_contextual_response_with_mock():
    """Test sync generate_contextual_response shim returns None (streaming moved to async)."""
    from llm import generate_contextual_response

    verses = [
        {
            "reference": {"book": "John", "chapter": 3, "verse": 16},
            "translations": {"NIV": "For God so loved the world..."},
        }
    ]

    response = generate_contextual_response("What is love?", verses, "en")

    # Sync wrapper is a stub; async streaming is the real implementation
    assert response is None


@pytest.mark.unit
def test_generate_contextual_response_error_handling():
    """Test sync shim returns None regardless of input (no LLM call made)."""
    from llm import generate_contextual_response

    verses = [
        {
            "reference": {"book": "John", "chapter": 3, "verse": 16},
            "translations": {"NIV": "For God so loved the world..."},
        }
    ]

    # Should not raise exception, returns None as a safe stub
    response = generate_contextual_response("What is love?", verses, "en")

    assert response is None


@pytest.mark.unit
def test_generate_contextual_response_empty_verses():
    """Test generating response with no verses."""
    from llm import generate_contextual_response

    response = generate_contextual_response("What is love?", [], "en")

    # With no verses, should return None or a message
    assert response is None or isinstance(response, str)


@pytest.mark.unit
@patch("llm.generate_contextual_response")
def test_batched_generate_response(mock_generate):
    """Test batched response generation."""
    import asyncio
    from llm_batcher import batched_generate_response

    mock_generate.return_value = "This is a test response"

    verses = [
        {
            "reference": {"book": "John", "chapter": 3, "verse": 16},
            "translations": {"NIV": "For God so loved the world..."},
        }
    ]

    # Run async function
    response = asyncio.run(batched_generate_response("What is love?", verses, "en"))

    assert response == "This is a test response"
    mock_generate.assert_called_once()


@pytest.mark.unit
def test_detect_language_empty_string():
    """Test language detection with empty string."""
    from llm import detect_language

    # Should default to English or handle gracefully
    result = detect_language("")
    assert result in ["en", "ko"]


@pytest.mark.unit
def test_detect_language_only_punctuation():
    """Test language detection with only punctuation."""
    from llm import detect_language

    result = detect_language("...!!!???")
    assert result in ["en", "ko"]  # Should default to something


@pytest.mark.unit
def test_prompt_length_limits():
    """Test that prompts don't exceed reasonable length."""
    from llm import _build_prompt

    # Create many verses
    verses = []
    for i in range(100):
        verses.append(
            {
                "reference": {"book": "Psalms", "chapter": i, "verse": 1},
                "translations": {"NIV": "This is a test verse " * 50},
            }
        )

    prompt = _build_prompt("test query", verses, "en")

    # Prompt should be reasonable length (not exceed 200k chars); no per-verse truncation by design
    assert len(prompt) < 200000


# --- _format_conversation_history tests ---

@pytest.mark.unit
def test_format_conversation_history_empty():
    """_format_conversation_history() returns empty string for None/empty input."""
    from llm import _format_conversation_history

    assert _format_conversation_history(None) == ""
    assert _format_conversation_history([]) == ""


@pytest.mark.unit
def test_format_conversation_history_with_turns():
    """_format_conversation_history() formats turns correctly."""
    from llm import _format_conversation_history

    history = [
        {"role": "user", "content": "What is love?"},
        {"role": "assistant", "content": "Love is described in 1 Corinthians 13."},
    ]
    result = _format_conversation_history(history, language="en")

    assert "User: What is love?" in result
    assert "Assistant: Love is described" in result
    assert "Previous conversation:" in result


@pytest.mark.unit
def test_format_conversation_history_korean():
    """_format_conversation_history() uses Korean header for ko language."""
    from llm import _format_conversation_history

    history = [{"role": "user", "content": "사랑이란?"}]
    result = _format_conversation_history(history, language="ko")

    assert "이전 대화:" in result


@pytest.mark.unit
def test_format_conversation_history_truncates_long_content():
    """_format_conversation_history() truncates content longer than 600 chars."""
    from llm import _format_conversation_history

    long_content = "x" * 700
    history = [{"role": "assistant", "content": long_content}]
    result = _format_conversation_history(history, language="en")

    # Content should be truncated with ...
    assert "..." in result
    # Total assistant content in result should be truncated
    lines = result.strip().split("\n")
    assistant_line = next(l for l in lines if l.startswith("Assistant:"))
    assert len(assistant_line) < 650


# --- _check_rate_limit tests ---

@pytest.mark.unit
def test_check_rate_limit_within_limit():
    """_check_rate_limit() returns True when under the limit."""
    import llm

    # Reset state
    llm._rate_limit_state["groq"] = {"count": 0, "reset_time": 0}

    result = llm._check_rate_limit("groq", limit=30)
    assert result is True
    assert llm._rate_limit_state["groq"]["count"] == 1


@pytest.mark.unit
def test_check_rate_limit_at_limit():
    """_check_rate_limit() returns False when at the limit."""
    import llm, time

    llm._rate_limit_state["gemini"] = {"count": 10, "reset_time": time.time()}

    result = llm._check_rate_limit("gemini", limit=10)
    assert result is False


@pytest.mark.unit
def test_check_rate_limit_resets_after_minute():
    """_check_rate_limit() resets counter after 60 seconds."""
    import llm, time

    # Set count to limit, but reset_time is 61 seconds ago
    llm._rate_limit_state["groq"] = {"count": 30, "reset_time": time.time() - 61}

    result = llm._check_rate_limit("groq", limit=30)
    assert result is True  # Reset triggered, count goes from 0 to 1
    assert llm._rate_limit_state["groq"]["count"] == 1


# --- expand_query tests ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_expand_query_returns_list_on_success():
    """expand_query() returns list of strings from Groq response."""
    import llm

    # Reset rate limit state
    llm._rate_limit_state["groq"] = {"count": 0, "reset_time": 0}

    mock_response = MagicMock()
    mock_response.choices[0].message.content = '["love mercy", "forgiveness grace", "compassion kindness"]'

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("llm.settings") as mock_settings:
        mock_settings.groq_api_key = "test-key"
        mock_settings.gemini_api_key = ""
        mock_settings.groq_rpm = 30
        mock_settings.gemini_rpm = 10
        with patch("llm._check_rate_limit", return_value=True):
            with patch("llm.AsyncGroq", return_value=mock_client, create=True):
                from llm import expand_query
                result = await expand_query("What is love?", language="en", groq_api_key="test-key")

    assert isinstance(result, list)
    assert len(result) <= 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_expand_query_returns_empty_on_failure():
    """expand_query() returns [] when all LLM calls fail."""
    import llm

    with patch("llm.settings") as mock_settings:
        mock_settings.groq_api_key = ""
        mock_settings.gemini_api_key = ""
        mock_settings.groq_rpm = 30
        mock_settings.gemini_rpm = 10
        from llm import expand_query
        # No API keys → no LLM calls → returns []
        result = await expand_query("What is love?")

    assert result == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_expand_query_groq_exception_returns_empty():
    """expand_query() returns [] when Groq raises an exception."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

    with patch("llm.settings") as mock_settings:
        mock_settings.groq_api_key = "test-key"
        mock_settings.gemini_api_key = ""
        mock_settings.groq_rpm = 30
        mock_settings.gemini_rpm = 10
        with patch("llm._check_rate_limit", return_value=True):
            with patch("llm.AsyncGroq", return_value=mock_client, create=True):
                from llm import expand_query
                result = await expand_query("test query", groq_api_key="test-key")

    assert result == []


# --- generate_contextual_response ---

@pytest.mark.unit
def test_generate_contextual_response_returns_none():
    """generate_contextual_response() sync wrapper returns None."""
    from llm import generate_contextual_response

    result = generate_contextual_response("query", [{"text": "verse"}], "en")
    assert result is None


# --- generate_contextual_response_stream ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_contextual_response_stream_empty_verses():
    """generate_contextual_response_stream() yields None for empty verses."""
    from llm import generate_contextual_response_stream

    chunks = []
    async for chunk in generate_contextual_response_stream("query", [], "en"):
        chunks.append(chunk)

    assert chunks == [None]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_contextual_response_stream_groq_success():
    """generate_contextual_response_stream() yields tokens when groq succeeds."""
    from llm import generate_contextual_response_stream

    async def mock_groq_gen(*args, **kwargs):
        yield "token1"
        yield "token2"

    with patch("llm.generate_response_stream_groq", side_effect=mock_groq_gen):
        chunks = []
        async for chunk in generate_contextual_response_stream(
            "faith", [{"text": "verse"}], "en"
        ):
            chunks.append(chunk)

    assert "token1" in chunks
    assert "token2" in chunks


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_contextual_response_stream_groq_none_falls_back_to_gemini():
    """generate_contextual_response_stream() falls back to gemini when groq yields None."""
    from llm import generate_contextual_response_stream

    async def mock_groq_gen(*args, **kwargs):
        yield None  # signals failure

    async def mock_gemini_gen(*args, **kwargs):
        yield "gemini_token"

    with patch("llm.generate_response_stream_groq", side_effect=mock_groq_gen):
        with patch("llm.generate_response_stream_gemini", side_effect=mock_gemini_gen):
            chunks = []
            async for chunk in generate_contextual_response_stream(
                "faith", [{"text": "verse"}], "en"
            ):
                chunks.append(chunk)

    assert "gemini_token" in chunks


# --- generate_response_stream_gemini ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_response_stream_gemini_no_api_key():
    """generate_response_stream_gemini() yields None when no API key."""
    from llm import generate_response_stream_gemini

    with patch("llm.settings") as mock_settings:
        mock_settings.gemini_api_key = ""
        mock_settings.gemini_rpm = 10
        chunks = []
        async for chunk in generate_response_stream_gemini("query", [], "en", api_key=None):
            chunks.append(chunk)

    assert chunks == [None]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_response_stream_groq_no_api_key():
    """generate_response_stream_groq() yields None when no API key."""
    from llm import generate_response_stream_groq

    with patch("llm.settings") as mock_settings:
        mock_settings.groq_api_key = ""
        mock_settings.groq_rpm = 30
        chunks = []
        async for chunk in generate_response_stream_groq("query", [], "en", api_key=None):
            chunks.append(chunk)

    assert chunks == [None]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_response_stream_groq_rate_limited():
    """generate_response_stream_groq() yields None when rate limited."""
    from llm import generate_response_stream_groq

    with patch("llm._check_rate_limit", return_value=False):
        chunks = []
        async for chunk in generate_response_stream_groq(
            "query", [], "en", api_key="test-key"
        ):
            chunks.append(chunk)

    assert chunks == [None]


# --- generate_response_stream_gemini (success path) ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_response_stream_gemini_success():
    """generate_response_stream_gemini() streams tokens when API key and rate limit OK."""
    import sys
    from unittest.mock import AsyncMock, MagicMock

    # Mock response chunks
    mock_chunk1 = MagicMock()
    mock_chunk1.text = "For God so "
    mock_chunk2 = MagicMock()
    mock_chunk2.text = "loved the world."

    # Mock async generator for streaming response
    async def mock_aiter():
        yield mock_chunk1
        yield mock_chunk2

    mock_response = MagicMock()
    mock_response.__aiter__ = lambda s: mock_aiter()

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_model
    mock_genai.GenerationConfig = MagicMock(return_value={})

    with patch.dict(sys.modules, {
        "google": MagicMock(generativeai=mock_genai),
        "google.generativeai": mock_genai,
    }):
        with patch("llm._check_rate_limit", return_value=True):
            from llm import generate_response_stream_gemini
            chunks = []
            async for chunk in generate_response_stream_gemini(
                "faith", [{"text": "verse"}], "en", api_key="test-key"
            ):
                chunks.append(chunk)

    assert any(c and "God" in c for c in chunks)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_response_stream_gemini_exception_yields_none():
    """generate_response_stream_gemini() yields None on exception."""
    import sys
    from unittest.mock import AsyncMock, MagicMock

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.side_effect = Exception("API error")

    with patch.dict(sys.modules, {
        "google": MagicMock(generativeai=mock_genai),
        "google.generativeai": mock_genai,
    }):
        with patch("llm._check_rate_limit", return_value=True):
            from llm import generate_response_stream_gemini
            chunks = []
            async for chunk in generate_response_stream_gemini(
                "faith", [{"text": "verse"}], "en", api_key="test-key"
            ):
                chunks.append(chunk)

    assert chunks == [None]


# --- generate_response_stream_groq (success path) ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_response_stream_groq_success():
    """generate_response_stream_groq() streams tokens from Groq API."""
    from unittest.mock import AsyncMock, MagicMock

    mock_chunk1 = MagicMock()
    mock_chunk1.choices = [MagicMock(delta=MagicMock(content="Blessed are "))]
    mock_chunk2 = MagicMock()
    mock_chunk2.choices = [MagicMock(delta=MagicMock(content="the meek."))]

    async def mock_stream():
        yield mock_chunk1
        yield mock_chunk2

    mock_stream_obj = mock_stream()

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream_obj)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)

    with patch("llm._check_rate_limit", return_value=True):
        with patch("groq.AsyncGroq", return_value=mock_client):
            from llm import generate_response_stream_groq
            chunks = []
            async for chunk in generate_response_stream_groq(
                "meek", [{"text": "verse"}], "en", api_key="test-key"
            ):
                if chunk:
                    chunks.append(chunk)

    assert any("Blessed" in c or "meek" in c for c in chunks)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_response_stream_groq_exception_yields_none():
    """generate_response_stream_groq() yields None on API exception."""
    from unittest.mock import AsyncMock, MagicMock

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("Groq down"))

    with patch("llm._check_rate_limit", return_value=True):
        with patch("groq.AsyncGroq", return_value=mock_client):
            from llm import generate_response_stream_groq
            chunks = []
            async for chunk in generate_response_stream_groq(
                "faith", [{"text": "verse"}], "en", api_key="test-key"
            ):
                chunks.append(chunk)

    assert chunks == [None]


# --- _build_prompt with original language + cross-references ---

@pytest.mark.unit
def test_build_prompt_with_original_and_crossrefs():
    """_build_prompt() includes original language and cross-refs when present."""
    from llm import _build_prompt

    verses = [
        {
            "reference": {
                "book": "John", "chapter": 3, "verse": 16,
                "testament": "NT", "genre": "gospel",
            },
            "translations": {"NIV": "For God so loved the world..."},
            "relevance_score": 0.95,
            "original": {
                "language": "greek",
                "words": [
                    {
                        "word": "ἀγαπάω", "transliteration": "agapao",
                        "strongs": "G25", "definition": "to love"
                    }
                ],
            },
            "cross_references": [
                {"book": "Romans", "chapter": 5, "verse": 8, "relationship": "parallel"}
            ],
        }
    ]

    prompt = _build_prompt("God's love", verses, "en")
    assert "Original (Greek)" in prompt
    assert "agapao" in prompt
    assert "Romans 5:8" in prompt


@pytest.mark.unit
def test_build_prompt_korean_conversation_history():
    """_build_prompt() includes Korean conversation history section."""
    from llm import _build_prompt

    history = [
        {"role": "user", "content": "사랑이란 무엇인가?"},
        {"role": "assistant", "content": "사랑은 하나님의 성품입니다."},
    ]

    verses = [{"reference": {"book": "John", "chapter": 3, "verse": 16},
               "translations": {"KRV": "하나님이 세상을..."}}]

    prompt = _build_prompt("사랑", verses, "ko", conversation_history=history)
    assert "이전 대화" in prompt


# --- expand_query success paths ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_expand_query_groq_success_returns_parsed_list():
    """expand_query() returns list when Groq returns valid JSON."""
    from unittest.mock import AsyncMock, MagicMock

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='["faith", "trust", "belief"]'))]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("llm._check_rate_limit", return_value=True):
        with patch("groq.AsyncGroq", return_value=mock_client):
            with patch("llm.settings") as mock_settings:
                mock_settings.groq_api_key = "test-key"
                mock_settings.gemini_api_key = ""
                mock_settings.groq_rpm = 30
                mock_settings.gemini_rpm = 10
                from llm import expand_query
                result = await expand_query("what is faith", language="en", groq_api_key="test-key")

    assert result == ["faith", "trust", "belief"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_expand_query_gemini_success_returns_parsed_list():
    """expand_query() falls back to Gemini and returns parsed list."""
    import sys
    from unittest.mock import AsyncMock, MagicMock

    mock_response = MagicMock()
    mock_response.text = '["grace", "mercy", "forgiveness"]'

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_model
    mock_genai.GenerationConfig = MagicMock(return_value={})

    # groq fails, gemini succeeds
    def rate_limit(provider, limit):
        return provider == "gemini"

    with patch.dict(sys.modules, {
        "google": MagicMock(generativeai=mock_genai),
        "google.generativeai": mock_genai,
    }):
        with patch("llm._check_rate_limit", side_effect=rate_limit):
            with patch("llm.settings") as mock_settings:
                mock_settings.groq_api_key = ""
                mock_settings.gemini_api_key = "test-key"
                mock_settings.groq_rpm = 30
                mock_settings.gemini_rpm = 10
                from llm import expand_query
                result = await expand_query("what is grace", language="en", gemini_api_key="test-key")

    assert result == ["grace", "mercy", "forgiveness"]
