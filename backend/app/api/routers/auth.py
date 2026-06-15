"""Auth router: login + current user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth_store import authenticate
from app.api.deps import get_current_user
from app.api.schemas import LoginRequest, TokenResponse, UserOut
from app.core.security import create_access_token

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    """Verify credentials and mint a JWT."""
    user = authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_access_token(user.username, user.role)
    return TokenResponse(access_token=token, role=user.role)  # type: ignore[arg-type]


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)) -> UserOut:
    """Return the authenticated caller."""
    return UserOut(id=user.id, username=user.username, role=user.role)  # type: ignore[arg-type]
