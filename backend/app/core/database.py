import ssl
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def _prepare_asyncpg_url_and_connect_args(raw_url: str) -> tuple[str, dict]:
    """
    Normalizes a Neon PostgreSQL URL for SQLAlchemy + asyncpg and enforces TLS.
    Strips query params unsupported by asyncpg (like sslmode/channel_binding)
    and passes an explicit ssl.SSLContext via connect_args.
    """
    parsed = urlparse(raw_url)
    scheme = "postgresql+asyncpg" if parsed.scheme.startswith("postgres") else parsed.scheme
    query_params = parse_qs(parsed.query)

    # Remove libpq-only parameters that cause TypeError in asyncpg.connect()
    requires_ssl = False
    for key in ["sslmode", "ssl", "channel_binding"]:
        if key in query_params:
            val = query_params.pop(key)[0].lower()
            if val in ("require", "verify-full", "verify-ca", "true", "1"):
                requires_ssl = True

    clean_query = urlencode(query_params, doseq=True)
    clean_url = urlunparse((scheme, parsed.netloc, parsed.path, parsed.params, clean_query, parsed.fragment))

    connect_args: dict = {}
    if requires_ssl or "neon.tech" in (parsed.hostname or ""):
        ssl_ctx = ssl.create_default_context()
        connect_args["ssl"] = ssl_ctx

    return clean_url, connect_args


ASYNC_DB_URL, ASYNC_CONNECT_ARGS = _prepare_asyncpg_url_and_connect_args(settings.DATABASE_URL)

engine = create_async_engine(
    ASYNC_DB_URL,
    connect_args=ASYNC_CONNECT_ARGS,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base for all IMS SQLAlchemy 2.0 ORM models."""
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()