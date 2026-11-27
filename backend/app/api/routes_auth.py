"""
Authentication API Routes.
Provides credential-checked login and token minting with server-assigned roles.
"""

from datetime import timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.security.users import authenticate_user
from backend.app.security.auth import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, description="Username for credential verification")
    password: str = Field(min_length=1, description="Password")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    expires_in_minutes: int

class UserInfoResponse(BaseModel):
    username: str
    role: str

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue verified role JWT",
    description="Validates credentials against server-side identities and assigns cryptographic role token."
)
def login(credentials: LoginRequest):
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Server assigns role strictly from authenticated identity
    token_data = {
        "sub": user["username"],
        "role": user["role"],
        "name": user["full_name"]
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user["role"],
        username=user["username"],
        expires_in_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth2-compatible token endpoint"
)
def token_endpoint(credentials: LoginRequest):
    return login(credentials)

@router.get(
    "/me",
    response_model=UserInfoResponse,
    summary="Retrieve current verified identity"
)
def get_me(current_user: dict = Depends(get_current_user)):
    return UserInfoResponse(
        username=current_user["username"],
        role=current_user["role"]
    )
