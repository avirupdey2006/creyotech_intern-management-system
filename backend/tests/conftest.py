import pytest
from app.core.database import engine


@pytest.fixture(autouse=True)
async def manage_db_engine_lifecycle():
    """Ensures asyncpg pooled connections bind cleanly to each test's event loop."""
    await engine.dispose()
    yield
    await engine.dispose()