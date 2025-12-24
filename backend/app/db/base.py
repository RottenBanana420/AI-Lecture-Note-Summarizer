"""
Database base module.

This module exports the SQLAlchemy declarative base for ORM model definitions.
All database models should inherit from this Base class.

IMPORTANT: Models should be imported in alembic/env.py for migrations,
not here, to avoid circular import issues.
"""

# Import Base from database module for model definitions
from app.core.database import Base

# Export Base for use in models
__all__ = ["Base"]


