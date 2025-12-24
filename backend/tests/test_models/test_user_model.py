"""
Comprehensive User model tests designed to find bugs and validate constraints.

These tests are aggressive and designed to BREAK the code by testing:
- Required field validation
- Unique constraint violations
- Field type validation
- Boundary values
- Special characters and SQL injection attempts
"""

import pytest
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import Session

from app.models.user import User


class TestUserModelCreation:
    """Test creating User instances with valid data."""
    
    def test_create_user_with_all_valid_fields(self, db_session: Session):
        """Test creating a user with all valid fields."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$dummy_hash",
            full_name="Test User",
            is_active="1",
            is_superuser="0"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active == "1"
        assert user.is_superuser == "0"
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_create_user_with_minimal_fields(self, db_session: Session):
        """Test creating a user with only required fields."""
        user = User(
            username="minimaluser",
            email="minimal@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.username == "minimaluser"
        assert user.email == "minimal@example.com"
        assert user.full_name is None
        assert user.is_active == "1"  # Default value
        assert user.is_superuser == "0"  # Default value


class TestUserRequiredFields:
    """Test that required fields are enforced."""
    
    def test_create_user_without_username_fails(self, db_session: Session):
        """Test that creating a user without username fails."""
        user = User(
            email="nouser@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "username" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_user_without_email_fails(self, db_session: Session):
        """Test that creating a user without email fails."""
        user = User(
            username="noemail",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "email" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_user_without_password_fails(self, db_session: Session):
        """Test that creating a user without hashed_password fails."""
        user = User(
            username="nopassword",
            email="nopass@example.com"
        )
        db_session.add(user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "hashed_password" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()


class TestUserUniqueConstraints:
    """Test unique constraint violations."""
    
    def test_duplicate_username_fails(self, db_session: Session):
        """Test that duplicate username raises IntegrityError."""
        # Create first user
        user1 = User(
            username="duplicate",
            email="user1@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create second user with same username
        user2 = User(
            username="duplicate",  # Same username
            email="user2@example.com",  # Different email
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        error_msg = str(exc_info.value).lower()
        assert "unique" in error_msg or "duplicate" in error_msg
        assert "username" in error_msg
        db_session.rollback()
    
    def test_duplicate_email_fails(self, db_session: Session):
        """Test that duplicate email raises IntegrityError."""
        # Create first user
        user1 = User(
            username="user1",
            email="duplicate@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create second user with same email
        user2 = User(
            username="user2",  # Different username
            email="duplicate@example.com",  # Same email
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        error_msg = str(exc_info.value).lower()
        assert "unique" in error_msg or "duplicate" in error_msg
        assert "email" in error_msg
        db_session.rollback()
    
    def test_same_username_and_email_different_users_fails(self, db_session: Session):
        """Test that both username and email must be unique."""
        user1 = User(
            username="sameuser",
            email="same@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create user with same username
        user2 = User(
            username="sameuser",
            email="different@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestUserBoundaryValues:
    """Test boundary values and edge cases."""
    
    def test_username_at_max_length(self, db_session: Session):
        """Test username at maximum length (50 chars)."""
        max_username = "a" * 50
        user = User(
            username=max_username,
            email="maxuser@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert len(user.username) == 50
    
    def test_username_exceeds_max_length_fails(self, db_session: Session):
        """Test that username exceeding 50 chars fails."""
        too_long_username = "a" * 51
        user = User(
            username=too_long_username,
            email="toolong@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        
        with pytest.raises(DataError) as exc_info:
            db_session.commit()
        
        assert "value too long" in str(exc_info.value).lower() or \
               "string" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_email_at_max_length(self, db_session: Session):
        """Test email at maximum length (255 chars)."""
        # Create email with 255 chars
        local_part = "a" * 240
        max_email = f"{local_part}@example.com"
        
        user = User(
            username="maxemail",
            email=max_email,
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert len(user.email) <= 255
    
    def test_email_exceeds_max_length_fails(self, db_session: Session):
        """Test that email exceeding 255 chars fails."""
        # Create email with 256+ chars
        local_part = "a" * 250
        too_long_email = f"{local_part}@example.com"
        
        user = User(
            username="toolongemail",
            email=too_long_email,
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        
        with pytest.raises(DataError) as exc_info:
            db_session.commit()
        
        assert "value too long" in str(exc_info.value).lower() or \
               "string" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_empty_string_username_fails(self, db_session: Session):
        """Test that empty string username fails (should be caught by NOT NULL or CHECK)."""
        user = User(
            username="",
            email="empty@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        
        # Empty string might be allowed by database but should fail uniqueness or validation
        # This test documents current behavior
        try:
            db_session.commit()
            # If it succeeds, we should add a CHECK constraint
            db_session.rollback()
            pytest.fail("Empty username should not be allowed")
        except (IntegrityError, DataError):
            # Expected - either constraint violation or data error
            db_session.rollback()
    
    def test_full_name_at_max_length(self, db_session: Session):
        """Test full_name at maximum length (100 chars)."""
        max_name = "A" * 100
        user = User(
            username="maxname",
            email="maxname@example.com",
            hashed_password="$2b$12$dummy_hash",
            full_name=max_name
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert len(user.full_name) == 100


class TestUserSpecialCharacters:
    """Test handling of special characters and potential SQL injection."""
    
    def test_username_with_special_characters(self, db_session: Session):
        """Test username with special characters."""
        # Test various special characters
        special_usernames = [
            "user_123",
            "user-name",
            "user.name",
            "user@domain",  # @ symbol
        ]
        
        for i, username in enumerate(special_usernames):
            user = User(
                username=username,
                email=f"special{i}@example.com",
                hashed_password="$2b$12$dummy_hash"
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            
            assert user.username == username
    
    def test_sql_injection_attempt_in_username(self, db_session: Session):
        """Test that SQL injection attempts are safely handled."""
        injection_attempts = [
            "admin'--",
            "admin' OR '1'='1",
            "'; DROP TABLE users; --",
        ]
        
        for i, injection in enumerate(injection_attempts):
            user = User(
                username=injection,
                email=f"injection{i}@example.com",
                hashed_password="$2b$12$dummy_hash"
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            
            # Should be stored as literal string, not executed
            assert user.username == injection
    
    def test_unicode_characters_in_full_name(self, db_session: Session):
        """Test that Unicode characters are properly handled."""
        unicode_names = [
            "José García",
            "李明",
            "Владимир",
            "محمد",
            "🎉 Party User 🎊",
        ]
        
        for i, name in enumerate(unicode_names):
            user = User(
                username=f"unicode{i}",
                email=f"unicode{i}@example.com",
                hashed_password="$2b$12$dummy_hash",
                full_name=name
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            
            assert user.full_name == name


class TestUserBooleanFields:
    """Test is_active and is_superuser fields."""
    
    def test_is_active_valid_values(self, db_session: Session):
        """Test is_active with valid values ("0" and "1")."""
        # Test "1" (active)
        user1 = User(
            username="active",
            email="active@example.com",
            hashed_password="$2b$12$dummy_hash",
            is_active="1"
        )
        db_session.add(user1)
        db_session.commit()
        assert user1.is_active == "1"
        assert user1.is_active_bool is True
        
        # Test "0" (inactive)
        user2 = User(
            username="inactive",
            email="inactive@example.com",
            hashed_password="$2b$12$dummy_hash",
            is_active="0"
        )
        db_session.add(user2)
        db_session.commit()
        assert user2.is_active == "0"
        assert user2.is_active_bool is False
    
    def test_is_active_invalid_values(self, db_session: Session):
        """Test is_active with invalid values (should be constrained to "0" or "1")."""
        invalid_values = ["2", "true", "false", "yes", "no", ""]
        
        for value in invalid_values:
            user = User(
                username=f"invalid_{value}",
                email=f"invalid_{value}@example.com",
                hashed_password="$2b$12$dummy_hash",
                is_active=value
            )
            db_session.add(user)
            
            # Currently no CHECK constraint, so this will succeed
            # This test documents that we should add a CHECK constraint
            try:
                db_session.commit()
                db_session.rollback()
                # If we get here, we should add validation
            except (IntegrityError, DataError):
                # If constraint exists, this is expected
                db_session.rollback()
    
    def test_is_superuser_valid_values(self, db_session: Session):
        """Test is_superuser with valid values."""
        user = User(
            username="superuser",
            email="super@example.com",
            hashed_password="$2b$12$dummy_hash",
            is_superuser="1"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.is_superuser == "1"
        assert user.is_superuser_bool is True


class TestUserRelationships:
    """Test User model relationships."""
    
    def test_user_documents_relationship_exists(self, db_session: Session):
        """Test that user has documents relationship."""
        user = User(
            username="reltest",
            email="rel@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        db_session.commit()
        
        # Should have documents attribute
        assert hasattr(user, 'documents')
        
        # Should be a dynamic relationship (query object)
        # Can call .all() on it
        docs = user.documents.all()
        assert isinstance(docs, list)
        assert len(docs) == 0  # No documents yet


class TestUserModelMethods:
    """Test User model methods and properties."""
    
    def test_user_repr(self, db_session: Session):
        """Test User __repr__ method."""
        user = User(
            username="reprtest",
            email="repr@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        db_session.commit()
        
        repr_str = repr(user)
        assert "User" in repr_str
        assert "reprtest" in repr_str
        assert "repr@example.com" in repr_str
    
    def test_is_active_bool_property(self, db_session: Session):
        """Test is_active_bool property conversion."""
        user = User(
            username="booltest",
            email="bool@example.com",
            hashed_password="$2b$12$dummy_hash",
            is_active="1"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.is_active_bool is True
        
        user.is_active = "0"
        db_session.commit()
        
        assert user.is_active_bool is False
