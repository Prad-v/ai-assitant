"""Authentication dependencies for FastAPI endpoints."""

import logging
from fastapi import Header, HTTPException, status, Depends, Request
from typing import Optional, Dict

from .jwt_auth import verify_jwt_token
from .token_service import TokenService
from .session_service import SessionService

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Dict:
    """
    FastAPI dependency to extract user from any authentication method.
    
    Supports:
    - JWT token in Authorization: Bearer <token> header
    - API token in X-API-Token header
    - Session token in X-Session-Token header or cookie
    
    Returns:
        Dict with user info: {user_id, username, role}
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    # Try JWT token first (Authorization: Bearer <token>)
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = verify_jwt_token(token)
        if payload and payload.get("type") == "access":
            return {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "role": payload.get("role"),
            }
    
    # Try API token (X-API-Token header)
    api_token = request.headers.get("X-API-Token")
    if api_token:
        user_info = TokenService.verify_api_token(api_token)
        if user_info:
            return user_info
    
    # Try session token (X-Session-Token header or cookie)
    session_token = request.headers.get("X-Session-Token")
    if not session_token:
        # Try cookie
        session_token = request.cookies.get("session_token")
    
    if session_token:
        user_info = SessionService.get_session(session_token)
        if user_info:
            # Update session activity
            SessionService.update_session_activity(session_token)
            return user_info
    
    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide JWT token (Authorization: Bearer <token>), API token (X-API-Token), or session token (X-Session-Token).",
    )


async def require_auth(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    FastAPI dependency requiring any valid authentication.
    
    Returns:
        User dict from get_current_user
    """
    return current_user


async def require_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    FastAPI dependency requiring admin role.
    
    Returns:
        User dict from get_current_user
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_role(required_role: str):
    """
    FastAPI dependency factory for specific role requirement.
    
    Args:
        required_role: Required role ("admin" or "user")
        
    Returns:
        FastAPI dependency function
    """
    async def role_check(current_user: Dict = Depends(get_current_user)) -> Dict:
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{required_role} role required"
            )
        return current_user
    
    return role_check
