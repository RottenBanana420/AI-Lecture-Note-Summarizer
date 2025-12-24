"""
CRUD operations module.

This module provides repository pattern implementations for all database models.
Each repository class encapsulates database operations for a specific model.
"""

from app.crud.base import CRUDBase
from app.crud.user import CRUDUser, user
from app.crud.document import CRUDDocument, document
from app.crud.summary import CRUDSummary, summary
from app.crud.note_chunk import CRUDNoteChunk, note_chunk

__all__ = [
    "CRUDBase",
    "CRUDUser",
    "user",
    "CRUDDocument",
    "document",
    "CRUDSummary",
    "summary",
    "CRUDNoteChunk",
    "note_chunk",
]

