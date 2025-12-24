"""
NoteChunk model for storing document chunks with vector embeddings.

This module defines the NoteChunk model which stores text chunks extracted
from documents along with their vector embeddings for similarity search.
"""

from sqlalchemy import Column, Text, Integer, ForeignKey, Index, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.base import Base


class NoteChunk(Base):
    """
    NoteChunk model for storing document chunks with vector embeddings.
    
    Attributes:
        id: Primary key
        document_id: Foreign key to the parent Document
        chunk_text: The text content of this chunk
        chunk_index: Position of this chunk within the document (0-indexed)
        embedding: Vector embedding of the chunk text (pgvector)
        character_count: Number of characters in the chunk
        token_count: Approximate number of tokens in the chunk
        chunk_metadata: Additional metadata about the chunk (JSON)
        created_at: Timestamp when the chunk was created
        
    Relationships:
        document: Many-to-one relationship with Document model
    """
    
    __tablename__ = "note_chunks"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign key to Document
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the document this chunk belongs to"
    )
    
    # Chunk content
    chunk_text = Column(
        Text,
        nullable=False,
        comment="The text content of this chunk"
    )
    
    # Chunk position
    chunk_index = Column(
        Integer,
        nullable=False,
        comment="Position of this chunk within the document (0-indexed)"
    )
    
    # Vector embedding (using pgvector)
    # Default dimension is 1536 (OpenAI ada-002), can be adjusted based on embedding model
    embedding = Column(
        Vector(1536),
        nullable=True,
        comment="Vector embedding of the chunk text for similarity search"
    )
    
    # Chunk statistics
    character_count = Column(
        Integer,
        nullable=False,
        comment="Number of characters in the chunk"
    )
    token_count = Column(
        Integer,
        nullable=True,
        comment="Approximate number of tokens in the chunk"
    )
    
    # Additional metadata
    chunk_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata about the chunk (e.g., page number, section)"
    )
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the chunk was created"
    )
    
    # Relationships
    document = relationship(
        "Document",
        back_populates="note_chunks",
        doc="Document that this chunk belongs to"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("ix_note_chunks_document_index", "document_id", "chunk_index"),
        # Vector similarity search index (HNSW for better performance)
        # Note: This index should be created via migration with specific parameters
        # Index("ix_note_chunks_embedding_hnsw", "embedding", postgresql_using="hnsw"),
        {"comment": "Note chunks table for storing document chunks with vector embeddings"}
    )
    
    def __repr__(self):
        """String representation of the NoteChunk instance."""
        return (
            f"<NoteChunk(id={self.id}, document_id={self.document_id}, "
            f"index={self.chunk_index})>"
        )
    
    @property
    def chunk_preview(self):
        """Return first 100 characters of the chunk."""
        if self.chunk_text:
            return self.chunk_text[:100] + "..." if len(self.chunk_text) > 100 else self.chunk_text
        return ""
    
    @property
    def has_embedding(self):
        """Check if this chunk has an embedding."""
        return self.embedding is not None
    
    def set_embedding(self, embedding_vector):
        """
        Set the embedding vector for this chunk.
        
        Args:
            embedding_vector: List or array of floats representing the embedding
        """
        self.embedding = embedding_vector
