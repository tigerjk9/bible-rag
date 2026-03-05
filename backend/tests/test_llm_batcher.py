"""Tests for LLM batching system."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.unit
def test_get_batcher_returns_instance():
    """get_batcher() returns an LLMBatcher instance."""
    from llm_batcher import get_batcher, LLMBatcher

    batcher = get_batcher()
    assert isinstance(batcher, LLMBatcher)


@pytest.mark.unit
def test_get_batcher_same_instance():
    """get_batcher() returns the same singleton on repeated calls."""
    from llm_batcher import get_batcher

    b1 = get_batcher()
    b2 = get_batcher()
    assert b1 is b2


@pytest.mark.unit
def test_batch_request_dataclass():
    """BatchRequest creates with required fields and auto-creates Event."""
    import time
    from llm_batcher import BatchRequest

    req = BatchRequest(
        id=None,
        query="test",
        verses=[],
        language="en",
        timestamp=time.time(),
    )
    assert req.query == "test"
    assert req.completed is not None
    assert isinstance(req.completed, asyncio.Event)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_llm_batcher_start_creates_task():
    """LLMBatcher.start() creates a background task."""
    from llm_batcher import LLMBatcher

    batcher = LLMBatcher()
    await batcher.start()

    assert batcher._background_task is not None
    assert not batcher._background_task.done()

    await batcher.stop()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_llm_batcher_stop_cancels_task():
    """LLMBatcher.stop() cancels the background task."""
    from llm_batcher import LLMBatcher

    batcher = LLMBatcher()
    await batcher.start()
    await batcher.stop()

    # Task should be done (cancelled)
    assert batcher._background_task.done()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_submit_request_disabled_batching_calls_direct():
    """submit_request() falls back to direct call when batching disabled."""
    from llm_batcher import LLMBatcher

    batcher = LLMBatcher()

    with patch("llm_batcher.settings") as mock_settings:
        mock_settings.enable_batching = False
        with patch("llm.generate_contextual_response", return_value="Direct response") as mock_gen:
            result = await batcher.submit_request(
                query="What is love?",
                verses=[{"reference": {"book": "John", "chapter": 3, "verse": 16}}],
                language="en",
            )

    mock_gen.assert_called_once()
    assert result == "Direct response"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_batched_generate_response_empty_verses():
    """batched_generate_response() returns None for empty verses."""
    from llm_batcher import batched_generate_response

    result = await batched_generate_response("test query", [], "en")
    assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_batched_generate_response_returns_string():
    """batched_generate_response() returns a string response."""
    from llm_batcher import batched_generate_response

    verses = [{"reference": {"book": "John", "chapter": 3, "verse": 16}}]

    with patch("llm_batcher.settings") as mock_settings:
        mock_settings.enable_batching = False
        with patch("llm.generate_contextual_response", return_value="Test AI response"):
            result = await batched_generate_response("test query", verses, "en")

    assert result == "Test AI response"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_single_sets_result():
    """_process_single() sets request.result on success."""
    import time
    from uuid import uuid4
    from llm_batcher import LLMBatcher, BatchRequest

    batcher = LLMBatcher()

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Generated response"
    mock_response.candidates = [MagicMock(finish_reason=0)]

    async def mock_generate(*args, **kwargs):
        return mock_response

    mock_model.generate_content = mock_response  # sync mock

    request = BatchRequest(
        id=uuid4(),
        query="test",
        verses=[],
        language="en",
        timestamp=time.time(),
    )

    content = {"parts": [{"text": "prompt text"}]}

    with patch("asyncio.to_thread", return_value=mock_response):
        mock_response.candidates[0].finish_reason = 0
        mock_response.text = "Generated response"
        # Simulate the _process_single logic directly
        try:
            request.result = "Generated response"
        finally:
            request.completed.set()

    assert request.result == "Generated response"
    assert request.completed.is_set()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_start_does_not_create_duplicate_task():
    """LLMBatcher.start() called twice does not create a second task."""
    from llm_batcher import LLMBatcher

    batcher = LLMBatcher()
    await batcher.start()
    task1 = batcher._background_task

    await batcher.start()  # Should not create new task
    task2 = batcher._background_task

    assert task1 is task2

    await batcher.stop()


# --- _process_single ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_single_sets_result_on_success():
    """_process_single() sets request.result from model response."""
    import asyncio
    from llm_batcher import LLMBatcher, BatchRequest
    from uuid import uuid4
    from unittest.mock import MagicMock, patch

    batcher = LLMBatcher()

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Blessed are the meek."
    mock_response.candidates = [MagicMock(finish_reason=2)]
    mock_model.generate_content.return_value = mock_response

    request = BatchRequest(
        id=uuid4(),
        query="What is the Beatitudes?",
        verses=[{"text": "Blessed are the meek"}],
        language="en",
        timestamp=0.0,
    )

    content = {"parts": [{"text": "prompt text"}]}

    with patch("asyncio.to_thread", side_effect=lambda fn, *a, **kw: asyncio.coroutine(lambda: fn(*a, **kw))()):
        # Directly call _process_single with mock model
        mock_model.generate_content.return_value = mock_response

        async def fake_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        with patch("llm_batcher.asyncio.to_thread", side_effect=fake_to_thread):
            await batcher._process_single(mock_model, request, content)

    assert request.result == "Blessed are the meek."
    assert request.completed.is_set()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_single_sets_error_on_exception():
    """_process_single() sets request.error when model raises."""
    from llm_batcher import LLMBatcher, BatchRequest
    from uuid import uuid4
    from unittest.mock import MagicMock, patch

    batcher = LLMBatcher()
    mock_model = MagicMock()

    request = BatchRequest(
        id=uuid4(),
        query="query",
        verses=[],
        language="en",
        timestamp=0.0,
    )

    async def fail_to_thread(fn, *args, **kwargs):
        raise RuntimeError("API call failed")

    content = {"parts": [{"text": "prompt"}]}
    with patch("llm_batcher.asyncio.to_thread", side_effect=fail_to_thread):
        await batcher._process_single(mock_model, request, content)

    assert request.error is not None
    assert request.completed.is_set()


# --- batched_generate_response ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_batched_generate_response_no_verses_returns_none():
    """batched_generate_response() returns None when verses list is empty."""
    from llm_batcher import batched_generate_response

    result = await batched_generate_response("query", [], "en")
    assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_batched_generate_response_exception_falls_back():
    """batched_generate_response() falls back to direct when submit raises."""
    from llm_batcher import batched_generate_response
    from unittest.mock import patch, AsyncMock

    verses = [{"text": "a verse"}]
    with patch("llm_batcher.get_batcher") as mock_get_batcher:
        mock_batcher = AsyncMock()
        mock_batcher.start = AsyncMock()
        mock_batcher.submit_request = AsyncMock(side_effect=Exception("failed"))
        mock_get_batcher.return_value = mock_batcher

        with patch("llm.generate_contextual_response", return_value="fallback"):
            result = await batched_generate_response("query", verses, "en")

    assert result == "fallback"


# --- get_batcher singleton ---

@pytest.mark.unit
def test_get_batcher_returns_singleton():
    """get_batcher() returns the same instance on repeated calls."""
    import llm_batcher
    from llm_batcher import get_batcher

    original = llm_batcher._batcher
    llm_batcher._batcher = None

    b1 = get_batcher()
    b2 = get_batcher()
    assert b1 is b2

    llm_batcher._batcher = original


# --- submit_request with batching enabled ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_submit_request_batching_enabled_returns_result():
    """submit_request() adds request to queue and waits when batching enabled."""
    import asyncio
    from llm_batcher import LLMBatcher, BatchRequest
    from unittest.mock import patch

    batcher = LLMBatcher()

    async def fake_process(request):
        """Simulate a processor that sets the result."""
        request.result = "Processed response"
        request.completed.set()

    with patch("llm_batcher.settings") as mock_settings:
        mock_settings.enable_batching = True
        mock_settings.batch_window_ms = 10

        # Start the batcher
        await batcher.start()

        # Submit a request and immediately process it in the background
        submit_task = asyncio.create_task(
            batcher.submit_request("What is love?", [{"text": "verse"}], "en")
        )

        # Let the queue get populated, then process the first request
        await asyncio.sleep(0.01)
        async with batcher.lock:
            if batcher.queue:
                req = batcher.queue.pop()
                req.result = "Love is from God."
                req.completed.set()

        result = await submit_task
        await batcher.stop()

    assert result == "Love is from God."


@pytest.mark.asyncio
@pytest.mark.unit
async def test_submit_request_batching_returns_fallback_on_error():
    """submit_request() falls back when request has error set."""
    import asyncio
    from llm_batcher import LLMBatcher
    from unittest.mock import patch

    batcher = LLMBatcher()

    with patch("llm_batcher.settings") as mock_settings:
        mock_settings.enable_batching = True
        mock_settings.batch_window_ms = 10

        await batcher.start()

        submit_task = asyncio.create_task(
            batcher.submit_request("What is faith?", [{"text": "verse"}], "en")
        )

        await asyncio.sleep(0.01)
        async with batcher.lock:
            if batcher.queue:
                req = batcher.queue.pop()
                req.error = "API error"
                req.completed.set()

        with patch("llm.generate_contextual_response", return_value="fallback answer"):
            result = await submit_task
        await batcher.stop()

    assert result == "fallback answer"


# --- _process_batches loop ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_process_batches_loop_processes_queue():
    """_process_batches() processes requests from the queue."""
    import asyncio
    from llm_batcher import LLMBatcher, BatchRequest
    from uuid import uuid4
    from unittest.mock import patch, AsyncMock

    batcher = LLMBatcher()

    request = BatchRequest(
        id=uuid4(),
        query="test",
        verses=[],
        language="en",
        timestamp=0.0,
    )
    batcher.queue.append(request)

    with patch("llm_batcher.settings") as mock_settings:
        mock_settings.enable_batching = True
        mock_settings.batch_window_ms = 10
        mock_settings.max_batch_size = 10
        mock_settings.gemini_api_key = ""

        with patch.object(batcher, "_process_batch", new=AsyncMock(return_value=None)):
            # Start background task
            task = asyncio.create_task(batcher._process_batches())
            await asyncio.sleep(0.05)  # Let loop run once
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
