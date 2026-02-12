"""
Authentication and authorization module.

Implements JWT-based authentication with role-based access control.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Annotated
from enum import Enum

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt, ExpiredSignatureError
import structlog

from ...config import settings

logger = structlog.get_logger()

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


class UserRole(str, Enum):
    """User roles for authorization."""
    VIEWER = "viewer"      # Read-only access
    TRADER = "trader"      # Can execute trades
    STRATEGIST = "strategist"  # Can manage strategies
    ADMIN = "admin"        # Full access


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until token expires")


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    username: Optional[str] = None
    user_id: Optional[str] = None
    roles: List[str] = []
    exp: Optional[datetime] = None


class UserBase(BaseModel):
    """Base user model."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must contain only alphanumeric characters, underscores, and hyphens")
        return v.lower()


class UserCreate(UserBase):
    """Model for user creation."""
    password: str = Field(..., min_length=12, max_length=128)
    roles: List[UserRole] = Field(default_factory=lambda: [UserRole.VIEWER])
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserInDB(UserBase):
    """User model as stored in database."""
    id: str
    hashed_password: str
    roles: List[str] = [UserRole.VIEWER.value]
    disabled: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None


class UserResponse(UserBase):
    """User response model (no sensitive data)."""
    id: str
    roles: List[str]
    disabled: bool
    created_at: datetime


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


# In-memory user storage (replace with database in production)
# This is for demonstration - production should use a proper database
_users_db: Dict[str, UserInDB] = {}


def _get_secret_key() -> str:
    """Get JWT secret key with validation."""
    return settings.validated_secret_key


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, _get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": secrets.token_hex(16)  # Unique token ID for revocation
    })
    
    encoded_jwt = jwt.encode(to_encode, _get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        Decoded token data
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            logger.warning("Invalid token type", expected=token_type, got=payload.get("type"))
            raise credentials_exception
        
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        roles: List[str] = payload.get("roles", [])
        exp = payload.get("exp")
        
        if username is None:
            raise credentials_exception
        
        return TokenData(
            username=username,
            user_id=user_id,
            roles=roles,
            exp=datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
        )
        
    except ExpiredSignatureError:
        logger.info("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning("JWT decode error", error=str(e))
        raise credentials_exception


async def get_user_from_db(username: str) -> Optional[UserInDB]:
    """Get user from database by username."""
    # Replace with actual database query in production
    return _users_db.get(username.lower())


async def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Get user from database by ID."""
    # Replace with actual database query in production
    for user in _users_db.values():
        if user.id == user_id:
            return user
    return None


async def create_user(user_create: UserCreate) -> UserInDB:
    """
    Create a new user in the database.
    
    Args:
        user_create: User creation data
        
    Returns:
        Created user
        
    Raises:
        HTTPException: If username or email already exists
    """
    # Check if username exists
    if user_create.username.lower() in _users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    for user in _users_db.values():
        if user.email.lower() == user_create.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create user
    user_id = secrets.token_hex(16)
    user = UserInDB(
        id=user_id,
        username=user_create.username.lower(),
        email=user_create.email.lower(),
        full_name=user_create.full_name,
        hashed_password=get_password_hash(user_create.password),
        roles=[r.value for r in user_create.roles],
        disabled=False,
        created_at=datetime.now(timezone.utc),
    )
    
    _users_db[user.username] = user
    
    logger.info("User created", username=user.username, user_id=user_id)
    return user


async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: User's username
        password: User's password
        
    Returns:
        User if authentication successful, None otherwise
    """
    user = await get_user_from_db(username)
    
    if not user:
        # Use constant-time comparison even for non-existent users
        # to prevent timing attacks
        get_password_hash(password)
        logger.warning("Login attempt for non-existent user", username=username)
        return None
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        logger.warning("Login attempt on locked account", username=username)
        return None
    
    if not verify_password(password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts for 15 minutes
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            logger.warning("Account locked due to failed attempts", username=username)
        
        logger.warning(
            "Failed login attempt",
            username=username,
            attempts=user.failed_login_attempts
        )
        return None
    
    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    
    logger.info("Successful login", username=username)
    return user


async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> UserInDB:
    """
    Get the current authenticated user from the request.
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If not authenticated or user not found
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = verify_token(token)
    user = await get_user_from_db(token_data.username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    """
    Get the current active (non-disabled) user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user


def require_role(*required_roles: UserRole):
    """
    Dependency factory for role-based access control.
    
    Args:
        required_roles: Roles required to access the endpoint
        
    Returns:
        Dependency function that checks user roles
    """
    async def role_checker(
        current_user: Annotated[UserInDB, Depends(get_current_active_user)]
    ) -> UserInDB:
        # Admin role has access to everything
        if UserRole.ADMIN.value in current_user.roles:
            return current_user
        
        # Check if user has any of the required roles
        user_roles = set(current_user.roles)
        required = {r.value for r in required_roles}
        
        if not user_roles.intersection(required):
            logger.warning(
                "Access denied - insufficient role",
                username=current_user.username,
                user_roles=list(user_roles),
                required_roles=list(required)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required)}"
            )
        
        return current_user
    
    return role_checker


# Optional authentication - returns None if not authenticated
async def get_optional_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> Optional[UserInDB]:
    """
    Get the current user if authenticated, None otherwise.
    
    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if not token:
        return None
    
    try:
        token_data = verify_token(token)
        return await get_user_from_db(token_data.username)
    except HTTPException:
        return None


# Initialize default admin user if none exists (for development)
async def init_default_admin():
    """
    Initialize a default admin user if no users exist.
    
    WARNING: This is for development only. Remove in production.
    """
    if not _users_db:
        try:
            await create_user(UserCreate(
                username="admin",
                email="admin@localhost",
                full_name="System Administrator",
                password=secrets.token_urlsafe(16) + "Aa1!",  # Random password
                roles=[UserRole.ADMIN]
            ))
            logger.warning(
                "Default admin user created. "
                "This is for development only - remove in production!"
            )
        except Exception as e:
            logger.error(f"Failed to create default admin: {e}")
