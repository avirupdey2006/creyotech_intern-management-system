from pathlib import Path
import time
import aiofiles
import httpx

from app.core.config import settings
from app.core.logging import pino_logger, trigger_sentry_alert


class StorageBackendService:
    """
    Unified Encrypted Document Storage Engine supporting both:
    - DROPBOX (Cloud persistent storage for Render / Kubernetes via OAuth2 Refresh Token)
    - LOCAL   (Local filesystem for development and offline pytest suites)
    """

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def is_dropbox_enabled(self) -> bool:
        return (
            settings.STORAGE_BACKEND.upper() == "DROPBOX"
            and bool(settings.DROPBOX_APP_KEY)
            and bool(settings.DROPBOX_APP_SECRET)
            and bool(settings.DROPBOX_REFRESH_TOKEN)
        )

    async def _get_dropbox_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.dropboxapi.com/oauth2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": settings.DROPBOX_REFRESH_TOKEN,
                    "client_id": settings.DROPBOX_APP_KEY,
                    "client_secret": settings.DROPBOX_APP_SECRET,
                },
            )
            resp.raise_for_status()
            token_data = resp.json()
            self._access_token = token_data["access_token"]
            self._token_expires_at = time.time() + int(token_data.get("expires_in", 14400))
            return self._access_token

    async def save_encrypted_document(self, filename: str, encrypted_bytes: bytes) -> str:
        """
        Saves the Fernet-encrypted PDF bytes to Dropbox (if enabled) or local disk.
        Returns the canonical storage_path string to persist in the documents table.
        """
        if self.is_dropbox_enabled:
            folder = settings.DROPBOX_FOLDER_PATH.rstrip("/")
            dropbox_path = f"{folder}/{filename}"
            try:
                token = await self._get_dropbox_access_token()
                import json

                arg_header = json.dumps(
                    {"path": dropbox_path, "mode": "overwrite", "autorename": False, "mute": True}
                )
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        "https://content.dropboxapi.com/2/files/upload",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Dropbox-API-Arg": arg_header,
                            "Content-Type": "application/octet-stream",
                        },
                        content=encrypted_bytes,
                    )
                    resp.raise_for_status()
                pino_logger.info(
                    "Uploaded Fernet-encrypted PDF to Dropbox vault",
                    dropbox_path=dropbox_path,
                    bytes_size=len(encrypted_bytes),
                )
                return f"dropbox://{dropbox_path}"
            except Exception as exc:
                trigger_sentry_alert(
                    "Dropbox upload failed; falling back to local container storage",
                    level="error",
                    context={"dropbox_path": dropbox_path, "error": str(exc)},
                )

        # Local disk storage (default or fallback)
        file_path: Path = settings.storage_path / filename
        async with aiofiles.open(file_path, mode="wb") as f:
            await f.write(encrypted_bytes)
        return str(file_path)

    async def read_encrypted_document(self, storage_path: str) -> bytes:
        """Reads the Fernet-encrypted PDF bytes from Dropbox (`dropbox://...`) or local disk."""
        if storage_path.startswith("dropbox://"):
            dropbox_path = storage_path.removeprefix("dropbox://")
            token = await self._get_dropbox_access_token()
            import json

            arg_header = json.dumps({"path": dropbox_path})
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://content.dropboxapi.com/2/files/download",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Dropbox-API-Arg": arg_header,
                    },
                )
                if resp.status_code != 200:
                    raise FileNotFoundError(
                        f"Dropbox file not found at {dropbox_path} (HTTP {resp.status_code})"
                    )
                return resp.content

        file_path = Path(storage_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Encrypted document file missing at {file_path}")
        async with aiofiles.open(file_path, mode="rb") as f:
            return await f.read()


storage_backend_service = StorageBackendService()