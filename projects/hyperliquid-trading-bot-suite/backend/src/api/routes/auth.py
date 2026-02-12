"""
Authentication endpoints.

Provides login, registration, token refresh, and user management.
"""

from typing import Annotated, Optional
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
import structlog

from ..security import (
    Token,
    UserCreate,
    UserResponse,
    LoginRequest,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_active_user,
    require_role,
    create_user,
    get_user_from_db,
)
from ..security.auth import (
    UserInDB,
    UserRole,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from ..security.rate_limiter import rate_limit, RateLimitTier
from ..security.key_vault import get_key_vault

router = APIRouter()
logger = structlog.get_logger()


@router.post(
    "/token",
    response_model=Token,
    summary="Get access token",
    description="OAuth2 compatible token login, get an access token for future requests"
)
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    _: None = Depends(rate_limit(RateLimitTier.AUTH))
):
    """
    OAuth2 compatible login endpoint.
    
    Use this for standard OAuth2 flows. Returns access and refresh tokens.
    """
    user = await authenticate_user(form_data.username, form_data.password)
    
    if not user:
        logger.warning(
            "Failed login attempt",
            username=form_data.username,
            ip=request.client.host if request.client else "unknown"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "roles": user.roles
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": user.username,
            "user_id": user.id
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    logger.info("User logged in", username=user.username)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Login with username and password"
)
async def login(
    request: Request,
    credentials: LoginRequest,
    _: None = Depends(rate_limit(RateLimitTier.AUTH))
):
    """
    JSON-based login endpoint.
    
    Alternative to OAuth2 form-based login for easier API usage.
    """
    user = await authenticate_user(credentials.username, credentials.password)
    
    if not user:
        logger.warning(
            "Failed login attempt",
            username=credentials.username,
            ip=request.client.host if request.client else "unknown"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create tokens
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "roles": user.roles
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": user.username,
            "user_id": user.id
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    logger.info("User logged in", username=user.username)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token"
)
async def refresh_token(
    request: Request,
    refresh_token: str,
    _: None = Depends(rate_limit(RateLimitTier.AUTH))
):
    """
    Get a new access token using a refresh token.
    
    Refresh tokens have a longer lifetime than access tokens.
    """
    try:
        token_data = verify_token(refresh_token, token_type="refresh")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user
    user = await get_user_from_db(token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create new tokens
    new_access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "roles": user.roles
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    new_refresh_token = create_refresh_token(
        data={
            "sub": user.username,
            "user_id": user.id
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    logger.info("Token refreshed", username=user.username)
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
async def register(
    request: Request,
    user_create: UserCreate,
    _: None = Depends(rate_limit(RateLimitTier.AUTH))
):
    """
    Register a new user account.
    
    Password requirements:
    - At least 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    try:
        user = await create_user(user_create)
        
        logger.info(
            "User registered",
            username=user.username,
            ip=request.client.host if request.client else "unknown"
        )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            roles=user.roles,
            disabled=user.disabled,
            created_at=user.created_at
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user"
)
async def get_current_user_info(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Get information about the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        roles=current_user.roles,
        disabled=current_user.disabled,
        created_at=current_user.created_at
    )


@router.post(
    "/wallet/register",
    summary="Register wallet for trading",
    description="Register a Hyperliquid wallet address and private key for trading"
)
async def register_wallet(
    request: Request,
    wallet_address: str,
    private_key: str,
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))],
    _: None = Depends(rate_limit(RateLimitTier.AUTH))
):
    """
    Register a Hyperliquid wallet for trading.
    
    The private key is:
    - Encrypted immediately using AES-256-GCM
    - Never stored in plaintext
    - Never transmitted in API requests
    - Used only for generating signatures
    
    WARNING: This endpoint accepts a private key. Ensure:
    - TLS is enabled in production
    - The key is from a wallet used only for this bot
    - The wallet has limited funds for safety
    """
    key_vault = get_key_vault()
    
    # Check if user already has a wallet
    if key_vault.has_key(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a registered wallet. Deactivate it first."
        )
    
    try:
        key_vault.store_key(
            user_id=current_user.id,
            wallet_address=wallet_address,
            private_key=private_key
        )
        
        logger.info(
            "Wallet registered",
            username=current_user.username,
            wallet_address=wallet_address[:10] + "..."
        )
        
        return {
            "message": "Wallet registered successfully",
            "wallet_address": wallet_address
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/wallet",
    summary="Remove registered wallet"
)
async def remove_wallet(
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))]
):
    """
    Remove the registered wallet for the current user.
    
    This deactivates the wallet and clears the encrypted key.
    """
    key_vault = get_key_vault()
    
    if not key_vault.has_key(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No wallet registered for this user"
        )
    
    key_vault.delete_key(current_user.id)
    
    logger.info("Wallet removed", username=current_user.username)
    
    return {"message": "Wallet removed successfully"}


@router.get(
    "/wallet",
    summary="Get wallet status"
)
async def get_wallet_status(
    current_user: Annotated[UserInDB, Depends(require_role(UserRole.TRADER))]
):
    """Get the wallet registration status for the current user."""
    key_vault = get_key_vault()
    
    has_wallet = key_vault.has_key(current_user.id)
    wallet_address = key_vault.get_wallet_address(current_user.id) if has_wallet else None
    
    return {
        "has_wallet": has_wallet,
        "wallet_address": wallet_address
    }


@router.post(
    "/logout",
    summary="Logout (invalidate tokens)"
)
async def logout(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """
    Logout the current user.
    
    Note: JWTs are stateless, so this endpoint doesn't actually invalidate
    the token. The client should discard the token. For full token invalidation,
    implement a token blacklist using Redis.
    """
    logger.info("User logged out", username=current_user.username)
    
    return {
        "message": "Successfully logged out",
        "note": "Discard the access and refresh tokens on the client side"
    }
