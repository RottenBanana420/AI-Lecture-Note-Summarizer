"""
SQLAlchemy database configuration with connection pooling.

This module provides:
- Database engine with production-ready connection pooling
- Session factory for creating database sessions
- Dependency injection function for FastAPI routes
- Declarative base for ORM models
- Connection pool monitoring utilities
"""

from typing import Generator
import logging
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# SQLAlchemy Engine Configuration
# ============================================================================

# Create database engine with production-ready connection pooling
# Based on SQLAlchemy 2.0 best practices for production applications
engine = create_engine(
    settings.DATABASE_URL,
    
    # Connection Pool Configuration
    # ============================
    
    # pool_size: Number of connections to maintain in the pool
    # Default: 5 - Good for most applications
    # Adjust based on concurrent request load
    pool_size=5,
    
    # max_overflow: Additional connections beyond pool_size during peak load
    # Default: 10 - Allows up to 15 total connections (5 + 10)
    # Total connections = pool_size + max_overflow
    max_overflow=10,
    
    # pool_timeout: Seconds to wait for available connection before raising error
    # Default: 30 - Prevents indefinite waiting
    pool_timeout=30,
    
    # pool_recycle: Recycle connections after N seconds
    # Prevents stale connections when database closes idle connections
    # PostgreSQL default idle timeout is often 8 hours (28800s)
    # Set to 1 hour (3600s) to be safe
    pool_recycle=3600,
    
    # pool_pre_ping: Test connection health before using
    # Adds minimal overhead but prevents "connection lost" errors
    # Highly recommended for production
    pool_pre_ping=True,
    
    # Performance & Debugging
    # =======================
    
    # echo: Log all SQL statements (useful for debugging)
    # Set to False in production for performance
    echo=settings.DEBUG,
    
    # echo_pool: Log connection pool events
    # Useful for debugging connection issues
    echo_pool=False,
    
    # Pool class: Use QueuePool (default) for thread-safe connection pooling
    # QueuePool is the default and works well for most applications
    poolclass=pool.QueuePool,
)


# ============================================================================
# Session Factory Configuration
# ============================================================================

# Create session factory with explicit transaction control
# Following SQLAlchemy 2.0 best practices for session management
SessionLocal = sessionmaker(
    # Bind to our configured engine
    bind=engine,
    
    # autocommit=False: Explicit transaction control
    # We manually call commit() or rollback()
    autocommit=False,
    
    # autoflush=False: Manual flush for better control
    # Prevents unexpected database queries
    autoflush=False,
    
    # expire_on_commit=True: Expire all instances after commit
    # This is the default and recommended for most use cases
    # For async applications, set to False to avoid lazy-loading errors
    expire_on_commit=True,
)


# ============================================================================
# Declarative Base
# ============================================================================

# Create declarative base for ORM model definitions
# All models should inherit from this Base class
Base = declarative_base()


# ============================================================================
# Database Session Dependency
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    
    Implements the session-per-request pattern:
    - Creates a new session for each request
    - Automatically closes session after request completes
    - Returns connection to pool for reuse
    
    Usage in FastAPI routes:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Transaction Management:
    - The session is created at the start of the request
    - You should call db.commit() explicitly after successful operations
    - If an exception occurs, call db.rollback() before re-raising
    - The session is always closed in the finally block
    
    Yields:
        Session: SQLAlchemy database session
        
    Example with transaction control:
        @app.post("/items")
        def create_item(item: ItemCreate, db: Session = Depends(get_db)):
            try:
                db_item = Item(**item.dict())
                db.add(db_item)
                db.commit()
                db.refresh(db_item)
                return db_item
            except Exception as e:
                db.rollback()
                raise
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # Always close the session to return connection to pool
        # This is critical to prevent connection leaks
        db.close()


# ============================================================================
# Connection Pool Monitoring
# ============================================================================

def get_pool_status() -> dict:
    """
    Get current connection pool statistics.
    
    Useful for monitoring and debugging connection pool behavior.
    
    Returns:
        dict: Connection pool statistics including:
            - size: Current number of connections in pool
            - checked_out: Number of connections currently in use
            - overflow: Number of overflow connections created
            - total: Total connections (size + overflow)
    """
    pool_obj = engine.pool
    return {
        "size": pool_obj.size(),
        "checked_out": pool_obj.checkedout(),
        "overflow": pool_obj.overflow(),
        "total": pool_obj.size() + pool_obj.overflow(),
    }


def log_pool_status():
    """
    Log current connection pool statistics.
    
    Call this periodically or on-demand to monitor pool health.
    """
    status = get_pool_status()
    logger.info(
        f"Connection Pool Status - "
        f"Size: {status['size']}, "
        f"Checked Out: {status['checked_out']}, "
        f"Overflow: {status['overflow']}, "
        f"Total: {status['total']}"
    )


# ============================================================================
# Database Connection Validation
# ============================================================================

def check_database_connection() -> bool:
    """
    Verify database connection is working.
    
    Useful for health checks and startup validation.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        # Try to connect and execute a simple query
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {e}")
        return False


# ============================================================================
# Event Listeners (Optional)
# ============================================================================

# Uncomment to enable connection pool event logging
# Useful for debugging connection issues

# @event.listens_for(engine, "connect")
# def receive_connect(dbapi_conn, connection_record):
#     """Log when a new connection is created."""
#     logger.debug("New database connection created")

# @event.listens_for(engine, "checkout")
# def receive_checkout(dbapi_conn, connection_record, connection_proxy):
#     """Log when a connection is checked out from the pool."""
#     logger.debug("Connection checked out from pool")

# @event.listens_for(engine, "checkin")
# def receive_checkin(dbapi_conn, connection_record):
#     """Log when a connection is returned to the pool."""
#     logger.debug("Connection returned to pool")
