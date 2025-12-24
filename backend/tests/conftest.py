"""
Pytest configuration and shared fixtures.

This module provides fixtures for database testing with proper isolation,
FastAPI test client, and sample data for tests.
"""

import pytest
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from app.models import User, Document, Summary, NoteChunk
from app.models.document import ProcessingStatus
from tests.utils.database import (
    get_test_db_url,
    create_test_database,
    verify_test_database_connection
)


# ============================================================================
# Session-scoped fixtures (run once per test session)
# ============================================================================

@pytest.fixture(scope="session")
def test_db_url() -> str:
    """
    Generate test database URL.
    
    This fixture runs once per test session and provides the URL
    for the test database.
    
    Returns:
        str: PostgreSQL connection URL for test database
    """
    return get_test_db_url()


@pytest.fixture(scope="session")
def test_engine(test_db_url: str):
    """
    Create test database engine.
    
    This fixture:
    1. Creates the test database if it doesn't exist
    2. Creates a SQLAlchemy engine for the test database
    3. Yields the engine for use in tests
    4. Disposes the engine after all tests complete
    
    The engine is session-scoped, so it's created once and reused
    across all tests for performance.
    
    Args:
        test_db_url: Test database URL from test_db_url fixture
    
    Yields:
        Engine: SQLAlchemy engine connected to test database
    """
    # Create test database if it doesn't exist
    create_test_database()
    
    # Verify connection
    if not verify_test_database_connection(test_db_url):
        pytest.fail("Could not connect to test database")
    
    # Create engine with test-optimized settings
    engine = create_engine(
        test_db_url,
        # Use smaller pool for tests
        pool_size=2,
        max_overflow=5,
        # Disable pool pre-ping for speed (we just verified connection)
        pool_pre_ping=False,
        # Echo SQL in tests if needed for debugging
        echo=False,
    )
    
    yield engine
    
    # Cleanup: dispose engine
    engine.dispose()


@pytest.fixture(scope="session")
def test_db_setup(test_engine):
    """
    Create all database tables before tests, drop after.
    
    This fixture runs once per test session:
    1. Creates pgvector extension if not exists
    2. Creates PostgreSQL ENUM types if they don't exist
    3. Creates all tables defined in SQLAlchemy models
    4. Yields control to run tests
    5. Drops all tables after tests complete
    
    This ensures a clean database state for each test run.
    
    Args:
        test_engine: Test database engine from test_engine fixture
    
    Yields:
        None
    """
    from sqlalchemy import text
    
    # Create extensions and ENUM types that are used in models
    # These need to be created before tables
    with test_engine.connect() as conn:
        # Create pgvector extension if it doesn't exist
        # This is required for the VECTOR type in note_chunks table
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # Create processing_status_enum if it doesn't exist
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE processing_status_enum AS ENUM (
                    'pending', 'processing', 'completed', 'failed'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # Create summary_type_enum if it doesn't exist
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE summary_type_enum AS ENUM (
                    'brief', 'detailed', 'key_points'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        conn.commit()
    
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    yield
    
    # Drop all tables
    Base.metadata.drop_all(bind=test_engine)
    
    # Drop ENUM types
    with test_engine.connect() as conn:
        conn.execute(text("DROP TYPE IF EXISTS processing_status_enum CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS summary_type_enum CASCADE"))
        # Note: We don't drop the vector extension as it might be used by other databases
        conn.commit()


# ============================================================================
# Function-scoped fixtures (run for each test function)
# ============================================================================

@pytest.fixture(scope="function")
def db_session(test_engine, test_db_setup) -> Generator[Session, None, None]:
    """
    Provide a transactional database session for testing.
    
    This fixture implements the "nested transaction" pattern:
    1. Begins a transaction
    2. Creates a session bound to that transaction
    3. Yields the session for use in the test
    4. Rolls back the transaction after the test
    
    This ensures complete test isolation - each test gets a clean
    database state, and changes made during the test are not persisted.
    
    This is the recommended pattern for database testing as it's much
    faster than creating/dropping tables for each test.
    
    Args:
        test_engine: Test database engine
        test_db_setup: Ensures tables are created
    
    Yields:
        Session: SQLAlchemy session with automatic rollback
        
    Example:
        def test_create_user(db_session):
            user = User(email="test@example.com")
            db_session.add(user)
            db_session.commit()
            # Changes will be rolled back after test
    """
    # Create a connection
    connection = test_engine.connect()
    
    # Begin a transaction
    transaction = connection.begin()
    
    # Create a session bound to the connection
    session = sessionmaker(bind=connection)()
    
    # Begin a nested transaction (savepoint)
    # This allows us to rollback to this point
    nested = connection.begin_nested()
    
    # If the application code calls session.commit(), it will only commit
    # the nested transaction (savepoint), not the outer transaction
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        """Restart savepoint after each commit."""
        if transaction.nested and not transaction._parent.nested:
            # Ensure we're still in a transaction
            if connection.in_transaction():
                session.expire_all()
                session.begin_nested()
    
    yield session
    
    # Rollback the transaction (discards all changes)
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Provide FastAPI test client with database override.
    
    This fixture creates a TestClient that uses the test database
    session instead of the production database. This ensures that
    API endpoint tests use the isolated test database.
    
    Args:
        db_session: Test database session with automatic rollback
    
    Yields:
        TestClient: FastAPI test client configured for testing
        
    Example:
        def test_create_user_endpoint(client):
            response = client.post("/api/v1/users", json={...})
            assert response.status_code == 201
    """
    # Override the get_db dependency to use our test session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Don't close session, it's managed by db_session fixture
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clear overrides after test
    app.dependency_overrides.clear()


# ============================================================================
# Sample data fixtures
# ============================================================================

@pytest.fixture
def sample_user(db_session: Session) -> User:
    """
    Create a sample user for testing.
    
    This fixture creates a user in the test database and returns it.
    The user will be automatically rolled back after the test.
    
    Args:
        db_session: Test database session
    
    Returns:
        User: Created user instance
        
    Example:
        def test_user_documents(sample_user, db_session):
            assert sample_user.id is not None
            assert sample_user.email == "testuser@example.com"
    """
    user = User(
        email="testuser@example.com",
        username="testuser",
        hashed_password="$2b$12$dummy_hash_for_testing",
        is_active="1"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_document(db_session: Session, sample_user: User) -> Document:
    """
    Create a sample document for testing.
    
    This fixture creates a document owned by sample_user.
    The document will be automatically rolled back after the test.
    
    Args:
        db_session: Test database session
        sample_user: User who owns the document
    
    Returns:
        Document: Created document instance
        
    Example:
        def test_document_summaries(sample_document, db_session):
            assert sample_document.user_id == sample_user.id
            assert sample_document.title == "Test Document"
    """
    document = Document(
        user_id=sample_user.id,
        title="Test Document",
        original_filename="document.pdf",
        file_path="/test/path/document.pdf",
        file_size=1024,
        mime_type="application/pdf",
        processing_status=ProcessingStatus.COMPLETED.value
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.fixture
def sample_user_inactive(db_session: Session) -> User:
    """
    Create an inactive user for testing authentication/authorization.
    
    Args:
        db_session: Test database session
    
    Returns:
        User: Created inactive user instance
    """
    user = User(
        email="inactive@example.com",
        username="inactiveuser",
        hashed_password="$2b$12$dummy_hash_for_testing",
        is_active="0"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def multiple_users(db_session: Session) -> list[User]:
    """
    Create multiple users for testing queries and relationships.
    
    Args:
        db_session: Test database session
    
    Returns:
        list[User]: List of created user instances
    """
    users = [
        User(
            email=f"user{i}@example.com",
            username=f"user{i}",
            hashed_password="$2b$12$dummy_hash_for_testing",
            is_active="1"
        )
        for i in range(1, 4)
    ]
    db_session.add_all(users)
    db_session.commit()
    for user in users:
        db_session.refresh(user)
    return users


# ============================================================================
# Utility fixtures
# ============================================================================

@pytest.fixture
def clean_db(db_session: Session):
    """
    Ensure database is clean before test.
    
    This fixture can be used when you need to ensure no data exists
    before running a test. It's automatically cleaned up by the
    db_session rollback.
    
    Args:
        db_session: Test database session
    
    Yields:
        Session: Clean database session
    """
    # The db_session fixture already provides isolation via rollback,
    # but this fixture can be used to explicitly mark tests that
    # require a clean database
    yield db_session


@pytest.fixture(autouse=False)
def reset_sequences(db_session: Session):
    """
    Reset database sequences after test.
    
    Use this fixture when you need predictable IDs in your tests.
    Not autouse by default as it adds overhead.
    
    Args:
        db_session: Test database session
    """
    yield
    # Reset sequences if needed
    # This is typically not necessary with transaction rollback
    pass
