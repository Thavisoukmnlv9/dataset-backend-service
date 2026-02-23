"""Shared test fixtures.

The Prisma mock is session-scoped so that module-level singletons
(like ``settings`` and ``app``) are only created once and reused
across all test functions.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(scope="session")
def _mock_prisma():
    """Stub out Prisma for the entire test session so that
    module-level imports (config, app factory) don't break."""
    mock_prisma = MagicMock()
    mock_prisma.is_connected.return_value = False
    mock_prisma.connect = AsyncMock()
    mock_prisma.disconnect = AsyncMock()

    mock_module = MagicMock(
        prisma=mock_prisma,
        db=mock_prisma,
        connect_db=AsyncMock(return_value=True),
        cleanup_all_connections=AsyncMock(),
        disconnect_db=AsyncMock(),
        ensure_connection=AsyncMock(),
    )

    with patch.dict(sys.modules, {"app.prisma": mock_module, "app.prisma.generated": MagicMock()}):
        yield mock_prisma


@pytest.fixture(scope="session")
def test_app(_mock_prisma):
    """Create the FastAPI app once per test session."""
    from app.main import create_app
    return create_app()


@pytest.fixture
def client(test_app):
    """Per-test TestClient (lightweight — reuses the session app)."""
    from fastapi.testclient import TestClient
    return TestClient(test_app)
