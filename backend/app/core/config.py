import json
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE_PATH = PROJECT_ROOT / ".env" if (PROJECT_ROOT / ".env").exists() else BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = "development"
    APP_NAME: str = "Intern Management System"
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://localhost"]

    # Database (Neon PostgreSQL)
    DATABASE_URL: str
    DIRECT_DATABASE_URL: str

    # Security & JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "strict"

    # Cryptographic Keys (Fernet PII & HMAC)
    PII_ENCRYPTION_KEY: str
    HMAC_SIGNING_SECRET: str
    SIGNED_URL_EXPIRY_SECONDS: int = 300

    # KYC Gateway
    KYC_PROVIDER: str = "MOCK"
    KYC_API_BASE_URL: str = "https://sandbox.cashfree.com/verification"
    KYC_CLIENT_ID: str = "mock_id"
    KYC_CLIENT_SECRET: str = "mock_secret"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_DOCUMENT_GENERATION: str = "intern.document.generate"
    KAFKA_TOPIC_EMAIL_NOTIFICATION: str = "intern.notification.email"
    KAFKA_CONSUMER_GROUP: str = "ims-backend-workers"

    # Email Dispatcher
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@ims.local"
    EMAIL_DAILY_LIMIT: int = 100

    # Storage (LOCAL or DROPBOX)
    STORAGE_BACKEND: str = "LOCAL"  # Set to "DROPBOX" on Render production
    ENCRYPTED_STORAGE_DIR: str = str(BACKEND_DIR / "storage" / "encrypted_docs")
    DROPBOX_APP_KEY: str = ""
    DROPBOX_APP_SECRET: str = ""
    DROPBOX_REFRESH_TOKEN: str = ""
    DROPBOX_FOLDER_PATH: str = "/IMS_Encrypted_Vault"
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    # Observability: Pino Structured Logs & Sentry Alerts
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    @property
    def storage_path(self) -> Path:
        path = Path(self.ENCRYPTED_STORAGE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()