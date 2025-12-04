"""Session management service for web authentication."""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import get_db_session
from .models import Session as SessionModel, User
from .auth_utils import generate_token, hash_token

logger = logging.getLogger(__name__)

# Session configuration from environment
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))  # Inactivity expiry
SESSION_ABSOLUTE_EXPIRY_DAYS = int(os.getenv("SESSION_ABSOLUTE_EXPIRY_DAYS", "7"))  # Absolute expiry


class SessionService:
    """Service for managing user sessions."""
    
    @staticmethod
    def create_session(user_id: int) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Session token (plain text, only shown once)
        """
        db: Session = get_db_session()
        try:
            # Generate session token
            session_token = generate_token(32)
            
            # Calculate expiration times
            now = datetime.now(timezone.utc)
            absolute_expires_at = now + timedelta(days=SESSION_ABSOLUTE_EXPIRY_DAYS)
            
            # Create session record
            session = SessionModel(
                user_id=user_id,
                session_token=session_token,
                created_at=now,
                expires_at=absolute_expires_at,
                last_activity_at=now,
                is_active=True,
            )
            
            db.add(session)
            db.commit()
            db.refresh(session)
            
            logger.info(f"Created session for user {user_id}")
            return session_token
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating session: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating session: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_session(session_token: str) -> Optional[Dict]:
        """
        Get session information.
        
        Args:
            session_token: Session token
            
        Returns:
            Dict with session info including user_id, username, role, or None if invalid
        """
        db: Session = get_db_session()
        try:
            now = datetime.now(timezone.utc)
            
            # Find active session
            session = db.query(SessionModel).filter(
                SessionModel.session_token == session_token,
                SessionModel.is_active == True,
                SessionModel.expires_at > now,
            ).first()
            
            if not session:
                return None
            
            # Check inactivity expiry
            inactivity_expires_at = session.last_activity_at + timedelta(hours=SESSION_EXPIRY_HOURS)
            if now > inactivity_expires_at:
                logger.info(f"Session expired due to inactivity: {session_token[:8]}...")
                session.is_active = False
                db.commit()
                return None
            
            # Get user info
            user = db.query(User).filter(User.id == session.user_id).first()
            if not user or not user.is_active:
                return None
            
            return {
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
                "session_id": session.id,
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting session: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def update_session_activity(session_token: str) -> bool:
        """
        Update last activity time for a session.
        
        Args:
            session_token: Session token
            
        Returns:
            True if updated, False if session not found
        """
        db: Session = get_db_session()
        try:
            session = db.query(SessionModel).filter(
                SessionModel.session_token == session_token,
                SessionModel.is_active == True,
            ).first()
            
            if not session:
                return False
            
            session.last_activity_at = datetime.now(timezone.utc)
            db.commit()
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating session activity: {e}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating session activity: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def invalidate_session(session_token: str) -> bool:
        """
        Invalidate a session (logout).
        
        Args:
            session_token: Session token
            
        Returns:
            True if invalidated, False if session not found
        """
        db: Session = get_db_session()
        try:
            session = db.query(SessionModel).filter(
                SessionModel.session_token == session_token,
                SessionModel.is_active == True,
            ).first()
            
            if not session:
                return False
            
            session.is_active = False
            db.commit()
            
            logger.info(f"Invalidated session: {session_token[:8]}...")
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error invalidating session: {e}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error invalidating session: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def cleanup_expired_sessions() -> int:
        """
        Remove expired sessions from database.
        
        Returns:
            Number of sessions cleaned up
        """
        db: Session = get_db_session()
        try:
            now = datetime.now(timezone.utc)
            
            # Find expired sessions
            expired_sessions = db.query(SessionModel).filter(
                SessionModel.is_active == True,
                SessionModel.expires_at <= now,
            ).all()
            
            count = len(expired_sessions)
            
            # Mark as inactive
            for session in expired_sessions:
                session.is_active = False
            
            db.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
            
            return count
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error cleaning up sessions: {e}")
            return 0
        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning up sessions: {e}")
            return 0
        finally:
            db.close()

