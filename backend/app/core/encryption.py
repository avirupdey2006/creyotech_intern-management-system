import hashlib
import hmac
import secrets
import time
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, Text

from app.core.config import settings

# Unambiguous 32-character uppercase alphanumeric alphabet (excludes 0/O, 1/I)
VERIFICATION_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


class CryptoEngine:
    """Centralized cryptographic engine for PII encryption, file encryption, HMAC hashing, and verification codes."""

    def __init__(self, fernet_key: str, hmac_secret: str) -> None:
        self._fernet = Fernet(fernet_key.encode("utf-8"))
        self._hmac_secret = hmac_secret.encode("utf-8")

    # 1. Field-Level PII Encryption (String -> Ciphertext String)
    def encrypt_pii(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt_pii(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Failed to decrypt PII field: invalid token or corrupted key.") from exc

    # 2. Binary File Encryption at Rest (PDF bytes -> Encrypted bytes)
    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        return self._fernet.decrypt(encrypted_data)

    # 3. SHA-256 Checksum for Documents
    @staticmethod
    def sha256_checksum(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    # 4. Cryptographically Secure 12-Character Alphanumeric Verification Code
    @staticmethod
    def generate_verification_code(length: int = 12) -> str:
        """
        Generates a cryptographically random 12-character uppercase alphanumeric
        verification code for certificates and offer letters.
        """
        return "".join(secrets.choice(VERIFICATION_ALPHABET) for _ in range(length))

    # 5. Data-Minimized KYC Reference Hash (One-way HMAC-SHA256)
    def hash_kyc_reference(self, profile_id: str, provider: str, raw_id_number: str, gateway_txn_id: str) -> str:
        """
        Computes a cryptographic reference hash from the verification transaction
        in volatile memory. Raw ID numbers are never stored or logged.
        """
        payload = f"{profile_id}:{provider}:{raw_id_number.strip()}:{gateway_txn_id}".encode("utf-8")
        digest = hmac.new(self._hmac_secret, payload, hashlib.sha256).hexdigest()
        del payload
        return digest

    # 6. Short-Lived Signed URL Token Generation & Verification
    def generate_signed_url_token(self, document_id: str, expires_in: Optional[int] = None) -> tuple[str, int]:
        ttl = expires_in if expires_in is not None else settings.SIGNED_URL_EXPIRY_SECONDS
        expires_at = int(time.time()) + ttl
        message = f"{document_id}:{expires_at}".encode("utf-8")
        signature = hmac.new(self._hmac_secret, message, hashlib.sha256).hexdigest()
        return signature, expires_at

    def verify_signed_url_token(self, document_id: str, expires_at: int, signature: str) -> bool:
        if int(time.time()) > expires_at:
            return False
        message = f"{document_id}:{expires_at}".encode("utf-8")
        expected_sig = hmac.new(self._hmac_secret, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, signature)


crypto_engine = CryptoEngine(
    fernet_key=settings.PII_ENCRYPTION_KEY,
    hmac_secret=settings.HMAC_SIGNING_SECRET,
)


class EncryptedString(TypeDecorator):
    """SQLAlchemy TypeDecorator that transparently encrypts PII before DB write and decrypts on read."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return crypto_engine.encrypt_pii(str(value))

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return crypto_engine.decrypt_pii(value)