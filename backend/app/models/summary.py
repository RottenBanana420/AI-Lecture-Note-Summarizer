"""
Summary model for storing generated document summaries.

This module defines the Summary model which stores AI-generated summaries
of documents with metadata about the summarization process.
"""

from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, Index, Enum as SQLEnum, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class SummaryType(str, enum.Enum):
    """Enumeration for summary generation types."""
    EXTRACTIVE = "extractive"
    ABSTRACTIVE = "abstractive"


class Summary(Base):
    """
    Summary model for storing generated document summaries.
    
    Attributes:
        id: Primary key
        document_id: Foreign key to the parent Document
        summary_text: The generated summary content
        summary_type: Type of summary (extractive or abstractive)
        processing_duration: Time taken to generate the summary in seconds
        summary_metadata: Additional metadata about the summarization process (JSON)
        generated_at: Timestamp when the summary was generated
        
    Relationships:
        document: Many-to-one relationship with Document model
    """
    
    __tablename__ = "summaries"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign key to Document
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the document this summary belongs to"
    )
    
    # Summary content
    summary_text = Column(
        Text,
        nullable=False,
        comment="The generated summary text"
    )
    
    # Summary metadata
    summary_type = Column(
        SQLEnum(SummaryType, name="summary_type_enum"),
        nullable=False,
        index=True,
        comment="Type of summary generation method used"
    )
    processing_duration = Column(
        Float,
        nullable=True,
        comment="Time taken to generate the summary in seconds"
    )
    summary_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata about the summarization process"
    )
    
    # Timestamp
    generated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Timestamp when the summary was generated"
    )
    
    # Relationships
    document = relationship(
        "Document",
        back_populates="summaries",
        doc="Document that this summary belongs to"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("ix_summaries_document_type", "document_id", "summary_type"),
        {"comment": "Summaries table for storing AI-generated document summaries"}
    )
    
    def __repr__(self):
        """String representation of the Summary instance."""
        return (
            f"<Summary(id={self.id}, document_id={self.document_id}, "
            f"type={self.summary_type.value})>"
        )
    
    @property
    def summary_preview(self):
        """Return first 100 characters of the summary."""
        if self.summary_text:
            return self.summary_text[:100] + "..." if len(self.summary_text) > 100 else self.summary_text
        return ""
    
    @property
    def word_count(self):
        """Return approximate word count of the summary."""
        if self.summary_text:
            return len(self.summary_text.split())
        return 0
