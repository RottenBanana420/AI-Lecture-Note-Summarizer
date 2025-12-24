"""
Tests for User CRUD operations.

Following TDD approach - these tests are written first and should fail initially.
"""

import pytest
from sqlalchemy.orm import Session

from app.crud.user import user as user_crud
from app.crud.exceptions import RecordNotFoundError, DuplicateRecordError
from app.models.user import User


class TestUserCRUD:
    """Test User CRUD operations."""
    
    def test_create_user(self, db: Session):
        """Test creating a new user with valid data."""
        username = "testuser"
        email = "test@example.com"
        hashed_password = "hashedpassword123"
        full_name = "Test User"
        
        user = user_crud.create_user(
            db,
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
        )
        
        assert user.id is not None
        assert user.username == username
        assert user.email == email
        assert user.hashed_password == hashed_password
        assert user.full_name == full_name
        assert user.is_active == "1"
        assert user.is_superuser == "0"
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_create_user_duplicate_username(self, db: Session):
        """Test creating user with duplicate username raises DuplicateRecordError."""
        username = "duplicateuser"
        email1 = "user1@example.com"
        email2 = "user2@example.com"
        
        # Create first user
        user_crud.create_user(
            db,
            username=username,
            email=email1,
            hashed_password="password1",
        )
        db.commit()
        
        # Attempt to create second user with same username
        with pytest.raises(DuplicateRecordError) as exc_info:
            user_crud.create_user(
                db,
                username=username,
                email=email2,
                hashed_password="password2",
            )
        
        assert "username" in str(exc_info.value).lower()
    
    def test_create_user_duplicate_email(self, db: Session):
        """Test creating user with duplicate email raises DuplicateRecordError."""
        username1 = "user1"
        username2 = "user2"
        email = "duplicate@example.com"
        
        # Create first user
        user_crud.create_user(
            db,
            username=username1,
            email=email,
            hashed_password="password1",
        )
        db.commit()
        
        # Attempt to create second user with same email
        with pytest.raises(DuplicateRecordError) as exc_info:
            user_crud.create_user(
                db,
                username=username2,
                email=email,
                hashed_password="password2",
            )
        
        assert "email" in str(exc_info.value).lower()
    
    def test_get_user_by_id(self, db: Session):
        """Test getting user by ID."""
        # Create user
        created_user = user_crud.create_user(
            db,
            username="getbyid",
            email="getbyid@example.com",
            hashed_password="password",
        )
        db.commit()
        
        # Get user by ID
        retrieved_user = user_crud.get(db, created_user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == created_user.username
    
    def test_get_user_by_id_not_found(self, db: Session):
        """Test getting non-existent user returns None."""
        user = user_crud.get(db, 99999)
        assert user is None
    
    def test_get_or_404_raises_error(self, db: Session):
        """Test get_or_404 raises RecordNotFoundError for non-existent user."""
        with pytest.raises(RecordNotFoundError) as exc_info:
            user_crud.get_or_404(db, 99999)
        
        assert "User" in str(exc_info.value)
        assert "99999" in str(exc_info.value)
    
    def test_get_user_by_username(self, db: Session):
        """Test getting user by username."""
        username = "findbyusername"
        created_user = user_crud.create_user(
            db,
            username=username,
            email="findbyusername@example.com",
            hashed_password="password",
        )
        db.commit()
        
        # Get user by username
        retrieved_user = user_crud.get_by_username(db, username=username)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == username
    
    def test_get_user_by_username_not_found(self, db: Session):
        """Test getting user by non-existent username returns None."""
        user = user_crud.get_by_username(db, username="nonexistent")
        assert user is None
    
    def test_get_user_by_email(self, db: Session):
        """Test getting user by email."""
        email = "findbyemail@example.com"
        created_user = user_crud.create_user(
            db,
            username="findbyemail",
            email=email,
            hashed_password="password",
        )
        db.commit()
        
        # Get user by email
        retrieved_user = user_crud.get_by_email(db, email=email)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == email
    
    def test_get_user_by_email_not_found(self, db: Session):
        """Test getting user by non-existent email returns None."""
        user = user_crud.get_by_email(db, email="nonexistent@example.com")
        assert user is None
    
    def test_update_user(self, db: Session):
        """Test updating user information."""
        # Create user
        user = user_crud.create_user(
            db,
            username="updateuser",
            email="update@example.com",
            hashed_password="password",
            full_name="Original Name",
        )
        db.commit()
        
        # Update user
        new_full_name = "Updated Name"
        updated_user = user_crud.update_user(
            db,
            user_id=user.id,
            update_data={"full_name": new_full_name},
        )
        db.commit()
        
        assert updated_user.id == user.id
        assert updated_user.full_name == new_full_name
        assert updated_user.username == user.username  # Unchanged
    
    def test_update_user_not_found(self, db: Session):
        """Test updating non-existent user raises RecordNotFoundError."""
        with pytest.raises(RecordNotFoundError):
            user_crud.update_user(
                db,
                user_id=99999,
                update_data={"full_name": "New Name"},
            )
    
    def test_soft_delete_user(self, db: Session):
        """Test soft deleting user sets is_active to '0'."""
        # Create user
        user = user_crud.create_user(
            db,
            username="softdelete",
            email="softdelete@example.com",
            hashed_password="password",
        )
        db.commit()
        
        assert user.is_active == "1"
        
        # Soft delete
        deleted_user = user_crud.soft_delete(db, user_id=user.id)
        db.commit()
        
        assert deleted_user.id == user.id
        assert deleted_user.is_active == "0"
        
        # User still exists in database
        retrieved_user = user_crud.get(db, user.id)
        assert retrieved_user is not None
        assert retrieved_user.is_active == "0"
    
    def test_hard_delete_user(self, db: Session):
        """Test hard deleting user removes from database."""
        # Create user
        user = user_crud.create_user(
            db,
            username="harddelete",
            email="harddelete@example.com",
            hashed_password="password",
        )
        db.commit()
        user_id = user.id
        
        # Hard delete
        deleted_user = user_crud.hard_delete(db, user_id=user_id)
        db.commit()
        
        assert deleted_user.id == user_id
        
        # User no longer exists in database
        retrieved_user = user_crud.get(db, user_id)
        assert retrieved_user is None
    
    def test_is_active(self, db: Session):
        """Test checking if user is active."""
        # Create active user
        user = user_crud.create_user(
            db,
            username="activecheck",
            email="activecheck@example.com",
            hashed_password="password",
            is_active="1",
        )
        db.commit()
        
        assert user_crud.is_active(db, user_id=user.id) is True
        
        # Soft delete user
        user_crud.soft_delete(db, user_id=user.id)
        db.commit()
        
        assert user_crud.is_active(db, user_id=user.id) is False
    
    def test_is_superuser(self, db: Session):
        """Test checking if user is superuser."""
        # Create regular user
        regular_user = user_crud.create_user(
            db,
            username="regularuser",
            email="regular@example.com",
            hashed_password="password",
            is_superuser="0",
        )
        db.commit()
        
        assert user_crud.is_superuser(db, user_id=regular_user.id) is False
        
        # Create superuser
        super_user = user_crud.create_user(
            db,
            username="superuser",
            email="super@example.com",
            hashed_password="password",
            is_superuser="1",
        )
        db.commit()
        
        assert user_crud.is_superuser(db, user_id=super_user.id) is True
    
    def test_get_multi_users(self, db: Session):
        """Test getting multiple users with pagination."""
        # Create multiple users
        for i in range(5):
            user_crud.create_user(
                db,
                username=f"user{i}",
                email=f"user{i}@example.com",
                hashed_password="password",
            )
        db.commit()
        
        # Get first 3 users
        users = user_crud.get_multi(db, skip=0, limit=3)
        assert len(users) >= 3
        
        # Get next 2 users
        users = user_crud.get_multi(db, skip=3, limit=2)
        assert len(users) >= 2
    
    def test_count_users(self, db: Session):
        """Test counting total users."""
        initial_count = user_crud.count(db)
        
        # Create 3 users
        for i in range(3):
            user_crud.create_user(
                db,
                username=f"countuser{i}",
                email=f"countuser{i}@example.com",
                hashed_password="password",
            )
        db.commit()
        
        new_count = user_crud.count(db)
        assert new_count == initial_count + 3
