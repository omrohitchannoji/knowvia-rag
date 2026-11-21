import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from backend.app.core.config import settings

security = HTTPBearer()

def decode_token(token: str) -> dict:
    secret = os.getenv("JWT_SECRET_KEY") or settings.JWT_SECRET_KEY
    algorithm = os.getenv("JWT_ALGORITHM") or settings.JWT_ALGORITHM
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validate JWT and return token payload.
    Expected payload contains at least a ``role`` field matching one of
    ``PUBLIC_USER``, ``INTERNAL_USER`` or ``ADMIN``.
    """
    token = credentials.credentials
    payload = decode_token(token)
    role: Optional[str] = payload.get("role")
    if role not in {"PUBLIC_USER", "INTERNAL_USER", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role in token",
        )
    return {"role": role, "sub": payload.get("sub")}
