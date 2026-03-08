"""Security helpers: JWT, hashing, RBAC, CSRF, and secret encryption."""
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import secrets
from typing import Optional

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

# Return 401 when Authorization header is missing/invalid.
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Generate bcrypt hash for a password."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        logger.warning("invalid_password_hash_format")
        return False


def _jwt_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = _jwt_now() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRATION_MINUTES))

    to_encode.update(
        {
            "exp": expire,
            "iat": _jwt_now(),
            "nbf": _jwt_now(),
        }
    )

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        logger.warning("jwt_decode_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Dependency to get authenticated JWT payload."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def require_role(*allowed_roles: str):
    """RBAC dependency factory."""

    async def role_checker(payload: dict = Depends(get_current_user_payload)):
        user_role = payload.get("role")
        if user_role not in allowed_roles:
            logger.warning(
                "unauthorized_role_access",
                user=payload.get("sub"),
                role=user_role,
                required_roles=allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Requiere rol: {', '.join(allowed_roles)}",
            )
        return payload

    return role_checker


def _fernet_key() -> bytes:
    """Build a stable Fernet key from env or SECRET_KEY."""
    key_material = settings.ROUTER_CREDENTIALS_KEY.strip() or settings.SECRET_KEY
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(value: str) -> str:
    """Encrypt sensitive values before storing in DB."""
    if not value:
        return value
    return Fernet(_fernet_key()).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    """Decrypt sensitive value, fallback to legacy plain text for migration."""
    if not value:
        return value
    try:
        return Fernet(_fernet_key()).decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return value


def generate_csrf_token() -> str:
    """Generate CSRF token for browser clients."""
    return secrets.token_urlsafe(32)


def compare_tokens(left: str, right: str) -> bool:
    """Constant-time token comparison."""
    if not left or not right:
        return False
    return hmac.compare_digest(left, right)


require_admin = require_role("admin")
require_admin_or_operator = require_role("admin", "operator")
