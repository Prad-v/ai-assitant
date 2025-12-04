"""API token management service."""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import get_db_session
from .models import ApiToken
from .auth_utils import generate_token, hash_token

logger = logging.getLogger(__name__)


class TokenService:
    """Service for managing API tokens."""
    
    @staticmethod
    def create_api_token(user_id: int, name: str, expires_at: Optional[datetime] = None) -> Dict:
        """
        Create a new API token for a user.
        
        Args:
            user_id: User ID
            name: User-friendly name for the token
            expires_at: Optional expiration datetime (None = no expiration)
            
        Returns:
            Dict with token info including plain text token (only shown once)
        """
        db: Session = get_db_session()
        try:
            # Generate token
            plain_token = generate_token(32)
            token_hash = hash_token(plain_token)
            
            # Create token record
            api_token = ApiToken(
                user_id=user_id,
                token_hash=token_hash,
                name=name,
                created_at=datetime.now(timezone.utc),
                last_used_at=None,
                expires_at=expires_at,
            )
            
            db.add(api_token)
            db.commit()
            db.refresh(api_token)
            
            logger.info(f"Created API token '{name}' for user {user_id}")
            
            return {
                "token": plain_token,  # Only shown once!
                "token_id": api_token.id,
                "name": api_token.name,
                "created_at": api_token.created_at.isoformat() if api_token.created_at else None,
                "expires_at": api_token.expires_at.isoformat() if api_token.expires_at else None,
            }
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating API token: {e}")
            raise ValueError(f"Failed to create API token: {e}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating API token: {e}")
            raise ValueError(f"Failed to create API token: {e}")
        finally:
            db.close()
    
    @staticmethod
    def list_api_tokens(user_id: int) -> List[Dict]:
        """
        List all API tokens for a user (without token values).
        
        Args:
            user_id: User ID
            
        Returns:
            List of token dicts (without actual token values)
        """
        db: Session = get_db_session()
        try:
            tokens = db.query(ApiToken).filter(
                ApiToken.user_id == user_id
            ).order_by(ApiToken.created_at.desc()).all()
            
            return [
                {
                    "id": token.id,
                    "name": token.name,
                    "created_at": token.created_at.isoformat() if token.created_at else None,
                    "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
                    "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                    "is_expired": token.expires_at is not None and token.expires_at < datetime.now(timezone.utc),
                }
                for token in tokens
            ]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error listing API tokens: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing API tokens: {e}")
            return []
        finally:
            db.close()
    
    @staticmethod
    def revoke_api_token(token_id: int, user_id: int) -> bool:
        """
        Revoke (delete) an API token.
        
        Args:
            token_id: Token ID
            user_id: User ID (must own the token)
            
        Returns:
            True if revoked, False if not found or not owned by user
        """
        db: Session = get_db_session()
        try:
            token = db.query(ApiToken).filter(
                ApiToken.id == token_id,
                ApiToken.user_id == user_id,
            ).first()
            
            if not token:
                return False
            
            db.delete(token)
            db.commit()
            
            logger.info(f"Revoked API token {token_id} for user {user_id}")
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error revoking API token: {e}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error revoking API token: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def verify_api_token(token: str) -> Optional[Dict]:
        """
        Verify an API token and return user information.
        
        Args:
            token: Plain text API token
            
        Returns:
            Dict with user info (user_id, username, role), or None if invalid
        """
        db: Session = get_db_session()
        try:
            token_hash = hash_token(token)
            now = datetime.now(timezone.utc)
            
            # Find token
            api_token = db.query(ApiToken).filter(
                ApiToken.token_hash == token_hash
            ).first()
            
            if not api_token:
                return None
            
            # Check expiration
            if api_token.expires_at and api_token.expires_at < now:
                logger.info(f"API token expired: {api_token.id}")
                return None
            
            # Get user
            from .models import User
            user = db.query(User).filter(User.id == api_token.user_id).first()
            if not user or not user.is_active:
                return None
            
            # Update last used
            api_token.last_used_at = now
            db.commit()
            
            return {
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error verifying API token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying API token: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def update_token_last_used(token_id: int) -> bool:
        """
        Update last used timestamp for a token.
        
        Args:
            token_id: Token ID
            
        Returns:
            True if updated, False if not found
        """
        db: Session = get_db_session()
        try:
            token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
            if not token:
                return False
            
            token.last_used_at = datetime.now(timezone.utc)
            db.commit()
            
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating token last used: {e}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating token last used: {e}")
            return False
        finally:
            db.close()

