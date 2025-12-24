"""
Database testing utilities.

This module provides helper functions for managing test databases,
including creation, cleanup, and URL generation.
"""

from typing import Optional
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError
from sqlalchemy.engine import Engine

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_test_db_url(database_name: Optional[str] = None) -> str:
    """
    Generate test database URL.
    
    Creates a database URL for testing by appending '_test' to the
    configured database name, or using a custom test database name.
    
    Args:
        database_name: Optional custom test database name.
                      If not provided, uses POSTGRES_DB + '_test'
    
    Returns:
        str: Complete PostgreSQL connection URL for test database
        
    Example:
        >>> get_test_db_url()
        'postgresql://user:pass@localhost:5432/mydb_test'
        >>> get_test_db_url('custom_test_db')
        'postgresql://user:pass@localhost:5432/custom_test_db'
    """
    if database_name is None:
        database_name = f"{settings.POSTGRES_DB}_test"
    
    return (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{database_name}"
    )


def create_test_database(database_name: Optional[str] = None) -> bool:
    """
    Create test database if it doesn't exist.
    
    Connects to the default 'postgres' database to create the test database.
    This is safe to call multiple times - it will not error if database exists.
    
    Args:
        database_name: Optional custom test database name.
                      If not provided, uses POSTGRES_DB + '_test'
    
    Returns:
        bool: True if database was created or already exists, False on error
        
    Note:
        Requires the PostgreSQL user to have CREATE DATABASE privileges.
    """
    if database_name is None:
        database_name = f"{settings.POSTGRES_DB}_test"
    
    # Connect to 'postgres' database to create our test database
    postgres_url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    )
    
    try:
        # Create engine with isolation_level for DDL operations
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": database_name}
            )
            exists = result.scalar() is not None
            
            if exists:
                logger.info(f"Test database '{database_name}' already exists")
                return True
            
            # Create database
            # Note: Database names cannot be parameterized in SQL
            # We validate the name to prevent SQL injection
            if not database_name.replace('_', '').isalnum():
                raise ValueError(f"Invalid database name: {database_name}")
            
            conn.execute(text(f'CREATE DATABASE "{database_name}"'))
            logger.info(f"Created test database: {database_name}")
            return True
            
    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Failed to create test database '{database_name}': {e}")
        return False
    finally:
        engine.dispose()


def drop_test_database(database_name: Optional[str] = None, force: bool = False) -> bool:
    """
    Drop test database.
    
    WARNING: This permanently deletes the database and all its data.
    Use with caution, typically only in cleanup scripts.
    
    Args:
        database_name: Optional custom test database name.
                      If not provided, uses POSTGRES_DB + '_test'
        force: If True, terminates active connections before dropping.
               Use this if you get "database is being accessed" errors.
    
    Returns:
        bool: True if database was dropped or doesn't exist, False on error
        
    Note:
        Requires the PostgreSQL user to have DROP DATABASE privileges.
    """
    if database_name is None:
        database_name = f"{settings.POSTGRES_DB}_test"
    
    # Safety check: Don't allow dropping production database
    if database_name == settings.POSTGRES_DB:
        logger.error("Refusing to drop production database!")
        return False
    
    if not database_name.endswith('_test'):
        logger.warning(f"Database name '{database_name}' doesn't end with '_test'")
    
    postgres_url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    )
    
    try:
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": database_name}
            )
            exists = result.scalar() is not None
            
            if not exists:
                logger.info(f"Test database '{database_name}' doesn't exist")
                return True
            
            # Terminate active connections if force=True
            if force:
                conn.execute(
                    text(
                        "SELECT pg_terminate_backend(pg_stat_activity.pid) "
                        "FROM pg_stat_activity "
                        "WHERE pg_stat_activity.datname = :dbname "
                        "AND pid <> pg_backend_pid()"
                    ),
                    {"dbname": database_name}
                )
                logger.info(f"Terminated active connections to '{database_name}'")
            
            # Validate database name to prevent SQL injection
            if not database_name.replace('_', '').isalnum():
                raise ValueError(f"Invalid database name: {database_name}")
            
            # Drop database
            conn.execute(text(f'DROP DATABASE "{database_name}"'))
            logger.info(f"Dropped test database: {database_name}")
            return True
            
    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Failed to drop test database '{database_name}': {e}")
        return False
    finally:
        engine.dispose()


def reset_database(engine: Engine) -> bool:
    """
    Truncate all tables in the database.
    
    This is faster than dropping and recreating tables for each test.
    Useful for cleaning up between test runs while keeping the schema.
    
    Args:
        engine: SQLAlchemy engine connected to the database to reset
    
    Returns:
        bool: True if successful, False on error
        
    Note:
        This uses TRUNCATE CASCADE which will reset all tables
        regardless of foreign key constraints.
    """
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        if not table_names:
            logger.info("No tables to truncate")
            return True
        
        with engine.connect() as conn:
            # Disable foreign key checks temporarily
            conn.execute(text("SET session_replication_role = 'replica'"))
            
            # Truncate all tables
            for table_name in table_names:
                # Skip alembic version table
                if table_name == 'alembic_version':
                    continue
                conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
            
            # Re-enable foreign key checks
            conn.execute(text("SET session_replication_role = 'origin'"))
            conn.commit()
            
        logger.info(f"Truncated {len(table_names)} tables")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to reset database: {e}")
        return False


def verify_test_database_connection(database_url: str) -> bool:
    """
    Verify that we can connect to the test database.
    
    Args:
        database_url: Database URL to test
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Test database connection successful")
        engine.dispose()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Test database connection failed: {e}")
        return False
