"""Security module for authentication, authorization, and rate limiting."""

from .auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
    get_current_active_user,
    require_role,
    authenticate_user,
    create_user,
    get_user_from_db,
    Token,
    TokenData,
    UserCreate,
    UserResponse,
    LoginRequest,
)
from .rate_limiter import (
    RateLimiter,
    rate_limit,
    get_rate_limiter,
)
from .key_vault import (
    KeyVault,
    get_key_vault,
)
from .websocket_auth import (
    authenticate_websocket,
    WebSocketAuthenticator,
)

__all__ = [
    # Auth
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "authenticate_user",
    "create_user",
    "get_user_from_db",
    "Token",
    "TokenData",
    "UserCreate",
    "UserResponse",
    "LoginRequest",
    # Rate limiting
    "RateLimiter",
    "rate_limit",
    "get_rate_limiter",
    # Key vault
    "KeyVault",
    "get_key_vault",
    # WebSocket auth
    "authenticate_websocket",
    "WebSocketAuthenticator",
]
