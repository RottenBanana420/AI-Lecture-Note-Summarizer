"""
Base model mixin for common database fields.

This module provides a base mixin class that includes common fields
used across all database models (id, created_at, updated_at).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func


class BaseModelMixin:
    """
    Base mixin class providing common fields for all models.
    
    Attributes:
        id: Primary key auto-incrementing integer
        created_at: Timestamp of record creation (auto-set)
        updated_at: Timestamp of last update (auto-updated)
    """
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the record was created"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the record was last updated"
    )
    
    def __repr__(self):
        """String representation of the model instance."""
        return f"<{self.__class__.__name__}(id={self.id})>"
