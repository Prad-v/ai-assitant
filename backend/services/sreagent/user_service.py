"""User management service."""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import get_db_session
from .models import User
from .auth_utils import hash_password, verify_password, validate_password

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users."""
    
    @staticmethod
    def create_user(username: str, password: str, role: str = "user") -> Dict:
        """
        Create a new user.
        
        Args:
            username: Username (must be unique)
            password: Plain text password
            role: User role ("admin" or "user")
            
        Returns:
            Dict with user info (without password_hash)
            
        Raises:
            ValueError: If validation fails or user already exists
        """
        # Validate password
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Validate role
        if role not in ["admin", "user"]:
            raise ValueError("Role must be 'admin' or 'user'")
        
        db: Session = get_db_session()
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                raise ValueError(f"User '{username}' already exists")
            
            # Hash password
            password_hash = hash_password(password)
            
            # Create user
            user = User(
                username=username,
                password_hash=password_hash,
                role=role,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"Created user: {username} with role: {role}")
            
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating user: {e}")
            raise ValueError(f"Failed to create user: {e}")
        except ValueError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user: {e}")
            raise ValueError(f"Failed to create user: {e}")
        finally:
            db.close()
    
    @staticmethod
    def get_user(user_id: int) -> Optional[Dict]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with user info, or None if not found
        """
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            Dict with user info including password_hash, or None if not found
        """
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return None
            
            return {
                "id": user.id,
                "username": user.username,
                "password_hash": user.password_hash,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user by username: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def update_user(user_id: int, **kwargs) -> Optional[Dict]:
        """
        Update user information.
        
        Args:
            user_id: User ID
            **kwargs: Fields to update (username, role, is_active)
            
        Returns:
            Updated user dict, or None if not found
        """
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Update allowed fields
            if "username" in kwargs:
                # Check if new username is already taken
                existing = db.query(User).filter(
                    User.username == kwargs["username"],
                    User.id != user_id
                ).first()
                if existing:
                    raise ValueError(f"Username '{kwargs['username']}' already exists")
                user.username = kwargs["username"]
            
            if "role" in kwargs:
                if kwargs["role"] not in ["admin", "user"]:
                    raise ValueError("Role must be 'admin' or 'user'")
                user.role = kwargs["role"]
            
            if "is_active" in kwargs:
                user.is_active = kwargs["is_active"]
            
            user.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(user)
            
            logger.info(f"Updated user: {user_id}")
            
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating user: {e}")
            raise ValueError(f"Failed to update user: {e}")
        except ValueError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user: {e}")
            raise ValueError(f"Failed to update user: {e}")
        finally:
            db.close()
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            db.delete(user)
            db.commit()
            
            logger.info(f"Deleted user: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error deleting user: {e}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting user: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def list_users(role: Optional[str] = None) -> List[Dict]:
        """
        List all users, optionally filtered by role.
        
        Args:
            role: Optional role filter
            
        Returns:
            List of user dicts
        """
        db: Session = get_db_session()
        try:
            query = db.query(User)
            if role:
                query = query.filter(User.role == role)
            
            users = query.order_by(User.created_at.desc()).all()
            
            return [
                {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                }
                for user in users
            ]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error listing users: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
        finally:
            db.close()
    
    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password (requires old password).
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
            
        Returns:
            True if changed, False if old password incorrect or user not found
        """
        # Validate new password
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Verify old password
            if not verify_password(old_password, user.password_hash):
                return False
            
            # Update password
            user.password_hash = hash_password(new_password)
            user.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            
            logger.info(f"Changed password for user: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error changing password: {e}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error changing password: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def reset_password(user_id: int, new_password: str) -> bool:
        """
        Reset user password (admin only, no old password required).
        
        Args:
            user_id: User ID
            new_password: New password
            
        Returns:
            True if reset, False if user not found
        """
        # Validate new password
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Update password
            user.password_hash = hash_password(new_password)
            user.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            
            logger.info(f"Reset password for user: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error resetting password: {e}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error resetting password: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def update_last_login(user_id: int) -> bool:
        """
        Update last login timestamp for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if updated, False if user not found
        """
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.last_login = datetime.now(timezone.utc)
            db.commit()
            
            return True
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error updating last login: {e}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating last login: {e}")
            return False
        finally:
            db.close()

