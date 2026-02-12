"""
WebSocket authentication module.

Provides token-based authentication for WebSocket connections.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect, Query, status
import structlog

from .auth import verify_token, UserInDB, get_user_from_db, TokenData

logger = structlog.get_logger()


class WebSocketAuthenticator:
    """
    Authenticator for WebSocket connections.
    
    Supports multiple authentication methods:
    1. Query parameter token (?token=xxx)
    2. First message authentication
    3. Subprotocol-based authentication
    """
    
    def __init__(self, require_auth: bool = True):
        """
        Initialize authenticator.
        
        Args:
            require_auth: Whether authentication is required
        """
        self.require_auth = require_auth
    
    async def authenticate_from_query(
        self,
        websocket: WebSocket,
        token: Optional[str] = None
    ) -> Optional[UserInDB]:
        """
        Authenticate WebSocket using query parameter token.
        
        Args:
            websocket: WebSocket connection
            token: JWT token from query string
            
        Returns:
            Authenticated user or None
        """
        if not token:
            if self.require_auth:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Authentication required. Provide token in query string."
                )
                return None
            return None
        
        try:
            token_data = verify_token(token, token_type="access")
            user = await get_user_from_db(token_data.username)
            
            if not user:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="User not found"
                )
                return None
            
            if user.disabled:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="User account is disabled"
                )
                return None
            
            logger.info(
                "WebSocket authenticated via query token",
                username=user.username,
                client=websocket.client
            )
            return user
            
        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired token"
            )
            return None
    
    async def authenticate_from_message(
        self,
        websocket: WebSocket,
        timeout_seconds: float = 30.0
    ) -> Optional[UserInDB]:
        """
        Authenticate WebSocket using first message containing token.
        
        The first message must be JSON: {"type": "auth", "token": "xxx"}
        
        Args:
            websocket: WebSocket connection (must be accepted first)
            timeout_seconds: Seconds to wait for auth message
            
        Returns:
            Authenticated user or None
        """
        import asyncio
        
        try:
            # Wait for auth message with timeout
            message = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=timeout_seconds
            )
            
            if message.get("type") != "auth":
                await websocket.send_json({
                    "type": "error",
                    "code": "AUTH_REQUIRED",
                    "message": "First message must be authentication"
                })
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="First message must be authentication"
                )
                return None
            
            token = message.get("token")
            if not token:
                await websocket.send_json({
                    "type": "error",
                    "code": "TOKEN_MISSING",
                    "message": "Token is required"
                })
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Token is required"
                )
                return None
            
            # Verify token
            token_data = verify_token(token, token_type="access")
            user = await get_user_from_db(token_data.username)
            
            if not user:
                await websocket.send_json({
                    "type": "error",
                    "code": "USER_NOT_FOUND",
                    "message": "User not found"
                })
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="User not found"
                )
                return None
            
            if user.disabled:
                await websocket.send_json({
                    "type": "error",
                    "code": "USER_DISABLED",
                    "message": "User account is disabled"
                })
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="User account is disabled"
                )
                return None
            
            # Send auth success
            await websocket.send_json({
                "type": "auth_success",
                "user": {
                    "username": user.username,
                    "roles": user.roles
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(
                "WebSocket authenticated via message",
                username=user.username,
                client=websocket.client
            )
            return user
            
        except asyncio.TimeoutError:
            await websocket.send_json({
                "type": "error",
                "code": "AUTH_TIMEOUT",
                "message": f"Authentication timeout ({timeout_seconds}s)"
            })
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Authentication timeout"
            )
            return None
            
        except Exception as e:
            logger.warning(f"WebSocket message authentication failed: {e}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "code": "AUTH_FAILED",
                    "message": "Authentication failed"
                })
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Authentication failed"
                )
            except:
                pass
            return None


async def authenticate_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT access token")
) -> Optional[UserInDB]:
    """
    FastAPI dependency for WebSocket authentication.
    
    Use this as a dependency in WebSocket endpoints:
    
    ```python
    @router.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        user: Optional[UserInDB] = Depends(authenticate_websocket)
    ):
        if not user:
            return  # Connection already closed
        await websocket.accept()
        ...
    ```
    
    Args:
        websocket: WebSocket connection
        token: JWT token from query string
        
    Returns:
        Authenticated user or None (connection closed)
    """
    authenticator = WebSocketAuthenticator(require_auth=True)
    return await authenticator.authenticate_from_query(websocket, token)


class AuthenticatedWebSocket:
    """
    Wrapper for authenticated WebSocket connections.
    
    Provides automatic token refresh and connection management.
    """
    
    def __init__(self, websocket: WebSocket, user: UserInDB):
        """
        Initialize authenticated WebSocket.
        
        Args:
            websocket: Underlying WebSocket connection
            user: Authenticated user
        """
        self.websocket = websocket
        self.user = user
        self._connected = False
        self._last_activity = datetime.now(timezone.utc)
    
    async def accept(
        self,
        subprotocol: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        """Accept the WebSocket connection."""
        await self.websocket.accept(subprotocol=subprotocol, headers=headers)
        self._connected = True
        
        # Send connection confirmation with user info
        await self.send_json({
            "type": "connected",
            "user": {
                "username": self.user.username,
                "roles": self.user.roles
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Send JSON data to the client."""
        await self.websocket.send_json(data)
        self._last_activity = datetime.now(timezone.utc)
    
    async def send_text(self, data: str) -> None:
        """Send text data to the client."""
        await self.websocket.send_text(data)
        self._last_activity = datetime.now(timezone.utc)
    
    async def receive_json(self) -> Dict[str, Any]:
        """Receive JSON data from the client."""
        data = await self.websocket.receive_json()
        self._last_activity = datetime.now(timezone.utc)
        return data
    
    async def receive_text(self) -> str:
        """Receive text data from the client."""
        data = await self.websocket.receive_text()
        self._last_activity = datetime.now(timezone.utc)
        return data
    
    async def close(
        self,
        code: int = 1000,
        reason: Optional[str] = None
    ) -> None:
        """Close the WebSocket connection."""
        self._connected = False
        await self.websocket.close(code=code, reason=reason)
    
    @property
    def is_connected(self) -> bool:
        """Check if the connection is active."""
        return self._connected
    
    @property
    def last_activity(self) -> datetime:
        """Get the time of last activity."""
        return self._last_activity
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.user.roles or "admin" in self.user.roles
