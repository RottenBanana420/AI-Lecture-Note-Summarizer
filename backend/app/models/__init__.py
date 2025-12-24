"""
Database models package.

This module exports all SQLAlchemy models for use throughout the application
and for Alembic migration autogeneration.
"""

from app.db.base import Base
from app.models.user import User
from app.models.document import Document
from app.models.summary import Summary, SummaryType
from app.models.note_chunk import NoteChunk

# Export all models for easy importing
__all__ = [
    "Base",
    "User",
    "Document",
    "Summary",
    "SummaryType",
    "NoteChunk",
]
