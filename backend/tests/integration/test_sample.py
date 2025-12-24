"""
Integration tests demonstrating database testing patterns.

These tests show how to:
- Test database connections
- Perform CRUD operations with fixtures
- Verify transaction rollback
- Test error cases
- Use markers for test categorization
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User, Document
from app.models.document import ProcessingStatus


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseConnection:
    """Test database connectivity and basic operations."""
    
    def test_database_connection(self, db_session: Session):
        """Test that we can connect to the test database."""
        result = db_session.execute(text("SELECT 1 as value"))
        row = result.fetchone()
        assert row[0] == 1
    
    def test_database_tables_exist(self, db_session: Session):
        """Test that all required tables exist."""
        # Query information_schema to check tables
        result = db_session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        tables = [row[0] for row in result.fetchall()]
        
        # Check that our main tables exist
        assert "users" in tables
        assert "documents" in tables
        assert "summaries" in tables
        assert "note_chunks" in tables
    
    def test_pgvector_extension(self, db_session: Session):
        """Test that pgvector extension is available."""
        result = db_session.execute(
            text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )
        )
        assert result.scalar() == 1, "pgvector extension not installed"


@pytest.mark.integration
@pytest.mark.database
class TestUserCRUD:
    """Test User model CRUD operations."""
    
    def test_create_user(self, db_session: Session):
        """Test creating a new user."""
        user = User(
            email="newuser@example.com",
            username="newuser",
            hashed_password="hashed_password_here",
            is_active="1"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.created_at is not None
    
    def test_read_user(self, sample_user: User, db_session: Session):
        """Test reading a user from database."""
        # Query the user
        user = db_session.query(User).filter(
            User.email == "testuser@example.com"
        ).first()
        
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email
    
    def test_update_user(self, sample_user: User, db_session: Session):
        """Test updating a user."""
        # Update user
        sample_user.username = "updated_username"
        db_session.commit()
        db_session.refresh(sample_user)
        
        # Verify update
        assert sample_user.username == "updated_username"
        
        # Query again to ensure it persisted
        user = db_session.get(User, sample_user.id)
        assert user.username == "updated_username"
    
    def test_delete_user(self, sample_user: User, db_session: Session):
        """Test deleting a user."""
        user_id = sample_user.id
        
        # Delete user
        db_session.delete(sample_user)
        db_session.commit()
        
        # Verify deletion
        user = db_session.get(User, user_id)
        assert user is None
    
    def test_unique_email_constraint(self, sample_user: User, db_session: Session):
        """Test that duplicate emails are rejected."""
        # Try to create user with same email
        duplicate_user = User(
            email="testuser@example.com",  # Same as sample_user
            username="different_username",
            hashed_password="hashed_password"
        )
        
        db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_unique_username_constraint(self, sample_user: User, db_session: Session):
        """Test that duplicate usernames are rejected."""
        # Try to create user with same username
        duplicate_user = User(
            email="different@example.com",
            username="testuser",  # Same as sample_user
            hashed_password="hashed_password"
        )
        
        db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.integration
@pytest.mark.database
class TestDocumentCRUD:
    """Test Document model CRUD operations."""
    
    def test_create_document(self, sample_user: User, db_session: Session):
        """Test creating a document."""
        document = Document(
            user_id=sample_user.id,
            title="My Document",
            original_filename="doc.pdf",
            file_path="/uploads/doc.pdf",
            file_size=2048,
            mime_type="application/pdf",
            processing_status=ProcessingStatus.PENDING.value
        )
        
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert document.id is not None
        assert document.user_id == sample_user.id
        assert document.title == "My Document"
        assert document.created_at is not None
    
    def test_user_document_relationship(
        self, sample_user: User, sample_document: Document, db_session: Session
    ):
        """Test relationship between User and Document."""
        # Access documents through user relationship
        user = db_session.get(User, sample_user.id)
        assert user.documents.count() == 1
        assert user.documents.first().id == sample_document.id
        
        # Access user through document relationship
        document = db_session.get(Document, sample_document.id)
        assert document.owner.id == sample_user.id
        assert document.owner.email == sample_user.email
    
    def test_cascade_delete_documents(
        self, sample_user: User, sample_document: Document, db_session: Session
    ):
        """Test that deleting a user cascades to documents."""
        document_id = sample_document.id
        
        # Delete user
        db_session.delete(sample_user)
        db_session.commit()
        
        # Verify document was also deleted (cascade)
        document = db_session.get(Document, document_id)
        assert document is None


@pytest.mark.integration
@pytest.mark.database
class TestTransactionIsolation:
    """Test that transaction rollback provides proper test isolation."""
    
    def test_changes_are_isolated_first(self, db_session: Session):
        """First test: create a user."""
        user = User(
            email="isolated1@example.com",
            username="isolated1",
            hashed_password="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        # User should exist in this test
        assert db_session.query(User).filter(
            User.email == "isolated1@example.com"
        ).first() is not None
    
    def test_changes_are_isolated_second(self, db_session: Session):
        """Second test: verify user from first test doesn't exist."""
        # User from previous test should NOT exist due to rollback
        user = db_session.query(User).filter(
            User.email == "isolated1@example.com"
        ).first()
        assert user is None
    
    def test_fixture_data_is_isolated(self, sample_user: User, db_session: Session):
        """Test that fixture data is available but isolated."""
        # sample_user should exist
        assert sample_user.id is not None
        
        # Modify the user
        sample_user.username = "modified"
        db_session.commit()
        
        assert sample_user.username == "modified"
        # This change will be rolled back after test


@pytest.mark.integration
@pytest.mark.database
class TestMultipleRecords:
    """Test operations with multiple records."""
    
    def test_query_multiple_users(self, multiple_users: list[User], db_session: Session):
        """Test querying multiple users."""
        users = db_session.query(User).all()
        
        # Should have at least the 3 users from fixture
        assert len(users) >= 3
        
        # Check that our fixture users are present
        emails = [u.email for u in users]
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails
        assert "user3@example.com" in emails
    
    def test_filter_users(self, multiple_users: list[User], db_session: Session):
        """Test filtering users."""
        # Filter active users
        active_users = db_session.query(User).filter(
            User.is_active == "1"
        ).all()
        
        assert len(active_users) >= 3
        
        # All should be active (is_active is stored as '1')
        for user in active_users:
            assert user.is_active == "1"
    
    def test_count_users(self, multiple_users: list[User], db_session: Session):
        """Test counting users."""
        count = db_session.query(User).count()
        assert count >= 3


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.slow
class TestComplexQueries:
    """Test more complex database queries."""
    
    def test_join_query(
        self, sample_user: User, sample_document: Document, db_session: Session
    ):
        """Test join between users and documents."""
        result = db_session.query(User, Document).join(
            Document, User.id == Document.user_id
        ).filter(User.id == sample_user.id).first()
        
        assert result is not None
        user, document = result
        assert user.id == sample_user.id
        assert document.id == sample_document.id
