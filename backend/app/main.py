from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging import pino_logger, setup_logging_and_sentry
from app.core.middleware import SecurityAndPinoLoggingMiddleware
from app.services.kafka_producer import kafka_event_producer

setup_logging_and_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    pino_logger.info(
        "Starting Intern Management System API",
        environment=settings.ENVIRONMENT,
        kyc_provider=settings.KYC_PROVIDER,
        sentry_enabled=bool(settings.SENTRY_DSN),
    )
    await kafka_event_producer.start()
    yield
    await kafka_event_producer.stop()
    pino_logger.info("Shutting down Intern Management System API")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(SecurityAndPinoLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "database": "connected",
        "logger": "pino-json",
        "sentry_configured": bool(settings.SENTRY_DSN),
    }