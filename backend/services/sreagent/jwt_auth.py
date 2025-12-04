"""JWT token management for authentication."""

import os
import jwt
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# JWT configuration from environment
# Helm secrets use stringData so they're plain text (not base64 encoded)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")

JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRY = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRY", "900"))  # 15 minutes
JWT_REFRESH_TOKEN_EXPIRY = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRY", "604800"))  # 7 days

if JWT_SECRET == "dev-secret-change-in-production":
    import warnings
    warnings.warn("Using default JWT_SECRET. Set JWT_SECRET environment variable in production!")


def create_jwt_token(user_id: int, username: str, role: str, token_type: str = "access") -> str:
    """
    Create a JWT token for a user.
    
    Args:
        user_id: User ID
        username: Username
        role: User role ("admin" or "user")
        token_type: Token type ("access" or "refresh")
        
    Returns:
        Encoded JWT token string
    """
    # Determine expiration based on token type
    if token_type == "refresh":
        expires_delta = timedelta(seconds=JWT_REFRESH_TOKEN_EXPIRY)
    else:
        expires_delta = timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRY)
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token: str) -> Optional[Dict]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload as dict, or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying JWT token: {e}")
        return None


def refresh_jwt_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    Generate new access token from refresh token.
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        Dict with new access_token and refresh_token, or None if invalid
    """
    payload = verify_jwt_token(refresh_token)
    if not payload:
        return None
    
    # Verify it's a refresh token
    if payload.get("type") != "refresh":
        logger.warning("Token is not a refresh token")
        return None
    
    # Create new tokens
    user_id = payload.get("user_id")
    username = payload.get("username")
    role = payload.get("role")
    
    if not all([user_id, username, role]):
        logger.warning("Invalid refresh token payload")
        return None
    
    new_access_token = create_jwt_token(user_id, username, role, "access")
    new_refresh_token = create_jwt_token(user_id, username, role, "refresh")
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    }

