"""
User CRUD repository implementation.

This module provides CRUD operations specific to the User model.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.crud.base import CRUDBase
from app.models.user import User
from app.crud.exceptions import RecordNotFoundError, DuplicateRecordError
import logging

logger = logging.getLogger(__name__)


class CRUDUser(CRUDBase[User]):
    """CRUD operations for User model."""
    
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            db: Database session
            username: Username to search for
            
        Returns:
            User instance if found, None otherwise
        """
        logger.debug(f"Getting user by username: {username}")
        result = db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            db: Database session
            email: Email to search for
            
        Returns:
            User instance if found, None otherwise
        """
        logger.debug(f"Getting user by email: {email}")
        result = db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    def create_user(
        self,
        db: Session,
        *,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        is_active: str = "1",
        is_superuser: str = "0"
    ) -> User:
        """
        Create a new user with validation.
        
        Args:
            db: Database session
            username: Unique username
            email: Unique email address
            hashed_password: Hashed password
            full_name: User's full name (optional)
            is_active: Whether user is active ("1" or "0")
            is_superuser: Whether user is superuser ("1" or "0")
            
        Returns:
            Created User instance
            
        Raises:
            DuplicateRecordError: If username or email already exists
        """
        # Check for existing username
        existing_user = self.get_by_username(db, username=username)
        if existing_user:
            raise DuplicateRecordError("User", "username", username)
        
        # Check for existing email
        existing_email = self.get_by_email(db, email=email)
        if existing_email:
            raise DuplicateRecordError("User", "email", email)
        
        # Create user
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "is_active": is_active,
            "is_superuser": is_superuser,
        }
        return self.create(db, obj_in=user_data)
    
    def update_user(
        self,
        db: Session,
        *,
        user_id: int,
        update_data: dict
    ) -> User:
        """
        Update user information.
        
        Args:
            db: Database session
            user_id: User ID to update
            update_data: Dictionary of fields to update
            
        Returns:
            Updated User instance
            
        Raises:
            RecordNotFoundError: If user not found
        """
        user = self.get_or_404(db, user_id)
        return self.update(db, db_obj=user, obj_in=update_data)
    
    def soft_delete(self, db: Session, *, user_id: int) -> User:
        """
        Soft delete user by setting is_active to "0".
        
        Args:
            db: Database session
            user_id: User ID to soft delete
            
        Returns:
            Updated User instance
            
        Raises:
            RecordNotFoundError: If user not found
        """
        logger.info(f"Soft deleting user with id={user_id}")
        user = self.get_or_404(db, user_id)
        return self.update(db, db_obj=user, obj_in={"is_active": "0"})
    
    def hard_delete(self, db: Session, *, user_id: int) -> User:
        """
        Hard delete user (permanently remove from database).
        
        WARNING: This will cascade delete all user's documents, summaries, and chunks.
        
        Args:
            db: Database session
            user_id: User ID to delete
            
        Returns:
            Deleted User instance
            
        Raises:
            RecordNotFoundError: If user not found
        """
        logger.warning(f"Hard deleting user with id={user_id} (cascade delete)")
        return self.delete(db, id=user_id)
    
    def is_active(self, db: Session, *, user_id: int) -> bool:
        """
        Check if user is active.
        
        Args:
            db: Database session
            user_id: User ID to check
            
        Returns:
            True if user is active, False otherwise
            
        Raises:
            RecordNotFoundError: If user not found
        """
        user = self.get_or_404(db, user_id)
        return user.is_active == "1"
    
    def is_superuser(self, db: Session, *, user_id: int) -> bool:
        """
        Check if user is superuser.
        
        Args:
            db: Database session
            user_id: User ID to check
            
        Returns:
            True if user is superuser, False otherwise
            
        Raises:
            RecordNotFoundError: If user not found
        """
        user = self.get_or_404(db, user_id)
        return user.is_superuser == "1"


# Create a singleton instance
user = CRUDUser(User)
