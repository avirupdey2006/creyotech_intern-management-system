import logging
import os
import re
import socket
import sys
import time
from typing import Any, Dict, MutableMapping
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
import structlog

from app.core.config import settings

HOSTNAME = socket.gethostname()
PID = os.getpid()

PINO_LEVEL_MAP: Dict[str, int] = {
    "debug": 20,
    "info": 30,
    "warning": 40,
    "warn": 40,
    "error": 50,
    "critical": 60,
    "fatal": 60,
}

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "raw_id_number",
    "government_id",
    "id_number",
    "aadhaar",
    "pan",
    "otp",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
}

# Regex matching 12-digit Aadhaar or 10-char PAN patterns in free text
GOV_ID_REGEX = re.compile(r"\b(\d{4}[-\s]?\d{4}[-\s]?\d{4}|[A-Z]{5}\d{4}[A-Z])\b")


def scrub_sensitive_data(value: Any) -> Any:
    """Recursively scrubs raw government IDs, passwords, and tokens from dicts, lists, and strings."""
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else scrub_sensitive_data(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [scrub_sensitive_data(item) for item in value]
    if isinstance(value, str):
        return GOV_ID_REGEX.sub("[REDACTED_ID]", value)
    return value


def pino_schema_processor(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    Formats structlog output into the standard Pino JSON specification:
    {"level": 30, "time": 1761241200000, "pid": 1234, "hostname": "...", "msg": "..."}
    """
    level_name = event_dict.pop("level", method_name).lower()
    msg = event_dict.pop("event", "")
    scrubbed_extras = scrub_sensitive_data(dict(event_dict))

    pino_record: Dict[str, Any] = {
        "level": PINO_LEVEL_MAP.get(level_name, 30),
        "level_label": level_name.upper(),
        "time": int(time.time() * 1000),
        "pid": PID,
        "hostname": HOSTNAME,
        "service": "ims-backend-api",
        "msg": scrub_sensitive_data(str(msg)),
    }
    pino_record.update(scrubbed_extras)
    return pino_record


def _sentry_before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Dict[str, Any]:
    """Guarantees zero raw government ID numbers or PII leak into Sentry alerts (Section 5.1)."""
    return scrub_sensitive_data(event)


def setup_logging_and_sentry() -> None:
    """Initializes Pino-formatted structured logging and Sentry error/security alerting."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            pino_schema_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,
            before_send=_sentry_before_send,  # type: ignore[arg-type]
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
        )


pino_logger = structlog.get_logger("ims.pino")


def trigger_sentry_alert(
    message: str,
    level: str = "error",
    context: Dict[str, Any] | None = None,
) -> None:
    """Emits both a high-priority Pino log entry and a scrubbed Sentry alert."""
    safe_context = scrub_sensitive_data(context or {})
    if level in ("error", "fatal", "critical"):
        pino_logger.error(message, alert=True, **safe_context)
    else:
        pino_logger.warning(message, alert=True, **safe_context)

    if settings.SENTRY_DSN:
        with sentry_sdk.push_scope() as scope:
            for k, v in safe_context.items():
                scope.set_extra(k, v)
            sentry_sdk.capture_message(scrub_sensitive_data(message), level=level)  # type: ignore[arg-type]