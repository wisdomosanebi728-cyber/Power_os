import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import bcrypt
import jwt


class Roles:
    OPERATOR = "operator"
    ADMIN = "admin"
    CONSUMER = "consumer"
    AUDITOR = "auditor"
    DEVICE = "device"


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8")[:72], salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    subject: str,
    role: str,
    community_id: Optional[str] = None,
    secret_key: str = "power-os-insecure-development-secret-change-in-production-32bytes",
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a signed JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(hours=24)
    )
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "community_id": community_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "POWER OS",
    }
    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_access_token(
    token: str,
    secret_key: str = "power-os-insecure-development-secret-change-in-production-32bytes",
    algorithm: str = "HS256",
) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token, secret_key, algorithms=[algorithm], issuer="POWER OS"
        )
        return payload
    except jwt.PyJWTError as e:
        raise ValueError(f"Invalid or expired token: {str(e)}") from e


def generate_device_token() -> str:
    """Generate a cryptographically secure raw token for device authentication."""
    return f"pow_dev_{secrets.token_urlsafe(32)}"


def hash_device_token(raw_token: str) -> str:
    """Compute SHA-256 hash of a device token for secure storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def verify_device_token(raw_token: str, stored_hash: str) -> bool:
    """Verify a raw device token against stored SHA-256 hash using constant-time comparison."""
    computed_hash = hash_device_token(raw_token)
    return hmac.compare_digest(computed_hash, stored_hash)
