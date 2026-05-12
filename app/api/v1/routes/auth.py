import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.crud.user import CRUDUser
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserResponse,
)
from app.services.auth import create_access_token, create_refresh_token, decode_token
from app.services.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    response_description="Access and refresh tokens",
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account and receive JWT tokens immediately.

    - **email**: valid email address
    - **password**: minimum 8 characters
    """
    existing = await CRUDUser.get_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    user = await CRUDUser.create(db, payload.email, payload.password)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    response_description="Access and refresh tokens",
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate and receive JWT tokens.

    Use the `access_token` in the **Authorize** button above (format: `Bearer <token>`).
    """
    user = await CRUDUser.authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    response_description="New access and refresh token pair",
)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    user_id = decode_token(payload.refresh_token, expected_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = await CRUDUser.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request a password reset email",
)
async def forgot_password(
    payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """
    Send a password reset link to the given email.

    Always returns success to prevent user enumeration.
    """
    user = await CRUDUser.get_by_email(db, payload.email)
    if not user:
        logger.warning("auth.forgot_password.unknown_email email=%s", payload.email)
        return {"message": "If that email exists, a reset link has been sent"}

    token = await CRUDUser.set_reset_token(db, user)
    await send_password_reset_email(user.email, token)
    return {"message": "If that email exists, a reset link has been sent"}


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password using token from email",
)
async def reset_password(
    payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Complete a password reset using the token received by email. Token expires in 1 hour."""
    user = await CRUDUser.get_by_reset_token(db, payload.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    await CRUDUser.reset_password(db, user, payload.new_password)
    return {"message": "Password reset successfully"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    responses={401: {"description": "Not authenticated"}},
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's profile including role."""
    return current_user
