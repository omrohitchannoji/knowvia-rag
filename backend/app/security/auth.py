import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from backend.app.core.config import settings

security = HTTPBearer(auto_error=False)

def get_signing_secret() -> str:
    """
    Retrieves the JWT signing secret from environment or settings.
    Fails closed (raises RuntimeError) if not configured and auth is required.
    """
    secret = os.getenv("JWT_SECRET_KEY") or settings.JWT_SECRET_KEY
    if not secret:
        if settings.REQUIRE_AUTH:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: JWT_SECRET_KEY is not set in the environment. "
                "Failing closed to prevent insecure unauthenticated execution."
            )
        # In non-auth development/testing mode only
        secret = "dev-insecure-test-key-only"
    return secret

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a cryptographically signed JWT token with server-assigned claims."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    secret = get_signing_secret()
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """Decodes and validates a JWT token signature and expiration."""
    secret = get_signing_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """
    Validates JWT identity and returns verified user payload.
    If anonymous access is explicitly enabled and no token is provided, returns
    restricted PUBLIC_USER identity.
    Otherwise, rejects unauthorized requests with HTTP 401.
    """
    if not credentials:
        if settings.ALLOW_ANONYMOUS_ACCESS:
            return {"role": "PUBLIC_USER", "sub": "anonymous_guest"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)
    role: Optional[str] = payload.get("role")
    if role not in {"PUBLIC_USER", "INTERNAL_USER", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient role in verified token",
        )
    return {
        "role": role,
        "sub": payload.get("sub", "unknown"),
        "username": payload.get("sub", "unknown")
    }
