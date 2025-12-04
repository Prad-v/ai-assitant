"""Initialize default admin account on startup."""

import logging
from .user_service import UserService

logger = logging.getLogger(__name__)


def init_default_admin():
    """
    Initialize default admin account if it doesn't exist.
    
    Creates user:
    - Username: admin
    - Password: admin
    - Role: admin
    """
    try:
        # Check if admin user exists
        admin_user = UserService.get_user_by_username("admin")
        
        if admin_user:
            logger.info("Default admin user already exists")
            return
        
        # Create default admin user (password must be at least 6 characters)
        UserService.create_user(
            username="admin",
            password="admin123",  # Changed to meet 6 character minimum
            role="admin"
        )
        
        logger.info("Created default admin user (username: admin, password: admin123)")
        logger.warning("IMPORTANT: Change the default admin password in production!")
        
    except Exception as e:
        logger.error(f"Failed to initialize default admin user: {e}", exc_info=True)

