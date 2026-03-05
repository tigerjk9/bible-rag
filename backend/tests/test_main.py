"""Tests for FastAPI app configuration, routing, and lifespan."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# --- App structure ---

@pytest.mark.unit
def test_app_is_fastapi_instance():
    """main.app is a FastAPI instance."""
    from fastapi import FastAPI
    from main import app

    assert isinstance(app, FastAPI)


@pytest.mark.unit
def test_app_has_correct_title():
    """App title matches expected value."""
    from main import app

    assert app.title == "Bible RAG API"


@pytest.mark.unit
def test_app_has_correct_version():
    """App version matches expected value."""
    from main import app

    assert app.version == "1.0.0"


@pytest.mark.unit
def test_app_cors_origins_include_localhost():
    """CORS middleware allows localhost:3000."""
    from main import allowed_origins

    assert "http://localhost:3000" in allowed_origins


@pytest.mark.unit
def test_app_cors_origins_include_vercel():
    """CORS middleware includes production Vercel origin by default."""
    from main import allowed_origins

    assert any("vercel" in o for o in allowed_origins)


# --- Route registration (via route list) ---

@pytest.mark.unit
def test_app_has_root_route():
    """App has a GET / route registered."""
    from main import app

    routes = [r.path for r in app.routes]
    assert "/" in routes


@pytest.mark.unit
def test_app_has_health_route():
    """App has /health route."""
    from main import app

    routes = [r.path for r in app.routes]
    assert "/health" in routes


@pytest.mark.unit
def test_app_has_search_route():
    """App has /api/search route."""
    from main import app

    routes = [r.path for r in app.routes]
    assert "/api/search" in routes


@pytest.mark.unit
def test_app_has_translations_route():
    """App has /api/translations route."""
    from main import app

    routes = [r.path for r in app.routes]
    assert "/api/translations" in routes


@pytest.mark.unit
def test_app_has_verse_route():
    """App has /api/verse route."""
    from main import app

    routes = [r.path for r in app.routes]
    assert any("verse" in r for r in routes)


# --- Root endpoint ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_root_endpoint_returns_api_info(test_client):
    """GET / returns API name and version."""
    response = await test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bible RAG API"
    assert data["version"] == "1.0.0"


# --- Lifespan ---

@pytest.mark.asyncio
@pytest.mark.unit
async def test_lifespan_gemini_mode_skips_local_model():
    """Lifespan with embedding_mode=gemini does not preload local model."""
    from main import lifespan
    from fastapi import FastAPI

    with patch("main.settings") as mock_settings:
        mock_settings.embedding_mode = "gemini"
        mock_settings.enable_reranking = False

        mock_db_result = MagicMock()
        mock_db_result.scalar.return_value = 0

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_db_result)

        # AsyncSessionLocal is imported inside lifespan body, so patch at source
        with patch("database.AsyncSessionLocal", return_value=mock_session):
            with patch("embeddings._get_local_model") as mock_load_local:
                app = FastAPI()
                async with lifespan(app):
                    pass

        mock_load_local.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_lifespan_sets_has_embeddings_flag():
    """Lifespan sets search._has_embeddings based on embeddings table count."""
    import search as search_module
    from main import lifespan
    from fastapi import FastAPI

    mock_db_result = MagicMock()
    mock_db_result.scalar.return_value = 100  # 100 embeddings exist

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_db_result)

    with patch("main.settings") as mock_settings:
        mock_settings.embedding_mode = "gemini"
        mock_settings.enable_reranking = False
        # AsyncSessionLocal is imported inside lifespan, patch at source
        with patch("database.AsyncSessionLocal", return_value=mock_session):
            app = FastAPI()
            async with lifespan(app):
                pass

    assert search_module._has_embeddings is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_lifespan_local_mode_preloads_embedding_model():
    """Lifespan with embedding_mode=local calls _get_local_model."""
    from main import lifespan
    from fastapi import FastAPI

    mock_db_result = MagicMock()
    mock_db_result.scalar.return_value = 0

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_db_result)

    with patch("main.settings") as mock_settings:
        mock_settings.embedding_mode = "local"
        mock_settings.enable_reranking = False
        with patch("database.AsyncSessionLocal", return_value=mock_session):
            with patch("embeddings._get_local_model") as mock_load:
                mock_load.return_value = MagicMock()
                app = FastAPI()
                async with lifespan(app):
                    pass

    mock_load.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_lifespan_enable_reranking_preloads_reranker():
    """Lifespan with enable_reranking=True calls _get_reranker."""
    from main import lifespan
    from fastapi import FastAPI

    mock_db_result = MagicMock()
    mock_db_result.scalar.return_value = 0

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_db_result)

    with patch("main.settings") as mock_settings:
        mock_settings.embedding_mode = "gemini"
        mock_settings.enable_reranking = True
        with patch("database.AsyncSessionLocal", return_value=mock_session):
            with patch("reranker._get_reranker") as mock_reranker:
                mock_reranker.return_value = MagicMock()
                app = FastAPI()
                async with lifespan(app):
                    pass

    mock_reranker.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_lifespan_db_error_does_not_crash():
    """Lifespan continues gracefully when embeddings count check fails."""
    from main import lifespan
    from fastapi import FastAPI

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(side_effect=Exception("DB unavailable"))

    with patch("main.settings") as mock_settings:
        mock_settings.embedding_mode = "gemini"
        mock_settings.enable_reranking = False
        with patch("database.AsyncSessionLocal", return_value=mock_session):
            app = FastAPI()
            # Should not raise
            async with lifespan(app):
                pass


@pytest.mark.unit
def test_cors_origins_from_env_var():
    """allowed_origins includes values from ALLOWED_ORIGINS env var."""
    import importlib
    import os
    import sys

    with patch.dict(os.environ, {"ALLOWED_ORIGINS": "https://example.com,https://app.example.com"}):
        # Re-import main to pick up environment variable
        if "main" in sys.modules:
            del sys.modules["main"]
        import main as fresh_main
        assert "https://example.com" in fresh_main.allowed_origins
        assert "https://app.example.com" in fresh_main.allowed_origins
