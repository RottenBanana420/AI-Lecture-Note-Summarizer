"""
Document model for storing uploaded document metadata.

This module defines the Document model which stores document metadata,
file information, processing status, and manages relationships with
users, summaries, and note chunks.
"""

from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, Index, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base
from app.models.base_model import BaseModelMixin


class ProcessingStatus(str, enum.Enum):
    """Enumeration for document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base, BaseModelMixin):
    """
    Document model for storing document metadata and processing information.
    
    Attributes:
        id: Primary key (inherited from BaseModelMixin)
        title: Document title
        original_filename: Original name of the uploaded file
        file_size: Size of the file in bytes
        mime_type: MIME type of the file
        file_path: Storage location of the file
        processing_status: Current processing status (pending/processing/completed/failed)
        user_id: Foreign key to User who uploaded the document
        uploaded_at: Timestamp when document was uploaded
        updated_at: Last update timestamp (inherited)
        
    Relationships:
        owner: Many-to-one relationship with User model
        summaries: One-to-many relationship with Summary model
        note_chunks: One-to-many relationship with NoteChunk model
    """
    
    __tablename__ = "documents"
    
    # Document metadata
    title = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Document title"
    )
    original_filename = Column(
        String(255),
        nullable=False,
        comment="Original filename of the uploaded document"
    )
    file_size = Column(
        BigInteger,
        nullable=False,
        comment="File size in bytes"
    )
    mime_type = Column(
        String(100),
        nullable=False,
        comment="MIME type of the document"
    )
    file_path = Column(
        String(500),
        nullable=False,
        unique=True,
        comment="Storage path or key for the document file"
    )
    
    # Processing status
    processing_status = Column(
        SQLEnum(ProcessingStatus, name="processing_status_enum"),
        nullable=False,
        server_default=ProcessingStatus.PENDING.value,
        index=True,
        comment="Current processing status of the document"
    )
    
    # Foreign key to User
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID of the user who uploaded the document"
    )
    
    # Override created_at with uploaded_at for semantic clarity
    uploaded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Timestamp when the document was uploaded"
    )
    
    # Relationships
    owner = relationship(
        "User",
        back_populates="documents",
        doc="User who uploaded this document"
    )
    summaries = relationship(
        "Summary",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="dynamic",
        doc="Summaries generated for this document"
    )
    note_chunks = relationship(
        "NoteChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="NoteChunk.chunk_index",
        doc="Text chunks extracted from this document"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("ix_documents_user_status", "user_id", "processing_status"),
        Index("ix_documents_uploaded_at", "uploaded_at"),
        {"comment": "Documents table for storing uploaded document metadata"}
    )
    
    def __repr__(self):
        """String representation of the Document instance."""
        return (
            f"<Document(id={self.id}, title='{self.title}', "
            f"status={self.processing_status.value})>"
        )
    
    @property
    def size_mb(self):
        """Return file size in megabytes."""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_processed(self):
        """Check if document processing is completed."""
        return self.processing_status == ProcessingStatus.COMPLETED
