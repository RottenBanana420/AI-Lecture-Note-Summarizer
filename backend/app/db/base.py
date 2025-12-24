"""
Database base module.

This module exports the SQLAlchemy declarative base for ORM model definitions.
All database models should inherit from this Base class.
"""

# Import Base from database module for model definitions
from app.core.database import Base

# Export Base for use in models
__all__ = ["Base"]
