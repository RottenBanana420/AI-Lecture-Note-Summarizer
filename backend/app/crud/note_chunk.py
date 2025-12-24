"""
NoteChunk CRUD repository implementation.

This module provides CRUD operations specific to the NoteChunk model.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.crud.base import CRUDBase
from app.models.note_chunk import NoteChunk
from app.crud.exceptions import DatabaseOperationError
import logging

logger = logging.getLogger(__name__)


class CRUDNoteChunk(CRUDBase[NoteChunk]):
    """CRUD operations for NoteChunk model."""
    
    def create_chunk(
        self,
        db: Session,
        *,
        document_id: int,
        chunk_text: str,
        chunk_index: int,
        character_count: int,
        token_count: Optional[int] = None,
        chunk_metadata: Optional[dict] = None,
        embedding: Optional[list] = None
    ) -> NoteChunk:
        """
        Create a single note chunk.
        
        Args:
            db: Database session
            document_id: Document ID this chunk belongs to
            chunk_text: The text content
            chunk_index: Position within document
            character_count: Number of characters
            token_count: Number of tokens
            chunk_metadata: Additional metadata
            embedding: Vector embedding
            
        Returns:
            Created NoteChunk instance
        """
        chunk_data = {
            "document_id": document_id,
            "chunk_text": chunk_text,
            "chunk_index": chunk_index,
            "character_count": character_count,
            "token_count": token_count,
            "chunk_metadata": chunk_metadata,
            "embedding": embedding,
        }
        return self.create(db, obj_in=chunk_data)
    
    def create_batch(
        self,
        db: Session,
        *,
        chunks_data: List[Dict[str, Any]]
    ) -> List[NoteChunk]:
        """
        Batch insert multiple chunks for efficiency.
        
        Args:
            db: Database session
            chunks_data: List of dictionaries containing chunk data
            
        Returns:
            List of created NoteChunk instances
            
        Raises:
            DatabaseOperationError: If batch insert fails
        """
        try:
            logger.debug(f"Batch creating {len(chunks_data)} note chunks")
            
            chunks = []
            for chunk_data in chunks_data:
                chunk = NoteChunk(**chunk_data)
                db.add(chunk)
                chunks.append(chunk)
            
            db.flush()
            
            # Refresh all chunks to get their IDs
            for chunk in chunks:
                db.refresh(chunk)
            
            logger.info(f"Successfully created {len(chunks)} note chunks")
            return chunks
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error batch creating note chunks: {e}")
            raise DatabaseOperationError("batch_create", "NoteChunk", e)
    
    def get_multi_by_document(
        self,
        db: Session,
        *,
        document_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[NoteChunk]:
        """
        Get chunks by document ID with pagination.
        
        Args:
            db: Database session
            document_id: Document ID
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List of NoteChunk instances ordered by chunk_index
        """
        logger.debug(
            f"Getting chunks for document_id={document_id}, "
            f"skip={skip}, limit={limit}"
        )
        
        result = db.execute(
            select(NoteChunk)
            .where(NoteChunk.document_id == document_id)
            .order_by(NoteChunk.chunk_index)
            .offset(skip)
            .limit(limit)
        )
        chunks = result.scalars().all()
        
        logger.debug(f"Found {len(chunks)} chunks for document_id={document_id}")
        return list(chunks)
    
    def get_by_index(
        self,
        db: Session,
        *,
        document_id: int,
        chunk_index: int
    ) -> Optional[NoteChunk]:
        """
        Get chunk by document and index.
        
        Args:
            db: Database session
            document_id: Document ID
            chunk_index: Chunk index
            
        Returns:
            NoteChunk instance if found, None otherwise
        """
        logger.debug(
            f"Getting chunk for document_id={document_id}, index={chunk_index}"
        )
        
        result = db.execute(
            select(NoteChunk).where(
                NoteChunk.document_id == document_id,
                NoteChunk.chunk_index == chunk_index
            )
        )
        return result.scalar_one_or_none()
    
    def update_embedding(
        self,
        db: Session,
        *,
        chunk_id: int,
        embedding_vector: list
    ) -> NoteChunk:
        """
        Update chunk embedding.
        
        Args:
            db: Database session
            chunk_id: Chunk ID
            embedding_vector: Vector embedding
            
        Returns:
            Updated NoteChunk instance
            
        Raises:
            RecordNotFoundError: If chunk not found
        """
        logger.debug(f"Updating embedding for chunk_id={chunk_id}")
        chunk = self.get_or_404(db, chunk_id)
        return self.update(db, db_obj=chunk, obj_in={"embedding": embedding_vector})
    
    def delete_by_document(self, db: Session, *, document_id: int) -> int:
        """
        Delete all chunks for a document.
        
        Args:
            db: Database session
            document_id: Document ID
            
        Returns:
            Number of chunks deleted
        """
        logger.info(f"Deleting all chunks for document_id={document_id}")
        
        chunks = self.get_multi_by_document(
            db, document_id=document_id, limit=10000
        )
        count = len(chunks)
        
        for chunk in chunks:
            db.delete(chunk)
        
        db.flush()
        logger.info(f"Deleted {count} chunks for document_id={document_id}")
        return count
    
    def count_by_document(self, db: Session, *, document_id: int) -> int:
        """
        Count chunks for a document.
        
        Args:
            db: Database session
            document_id: Document ID
            
        Returns:
            Count of chunks
        """
        logger.debug(f"Counting chunks for document_id={document_id}")
        
        result = db.execute(
            select(func.count()).select_from(NoteChunk).where(
                NoteChunk.document_id == document_id
            )
        )
        count = result.scalar()
        
        logger.debug(f"Document {document_id} has {count} chunks")
        return count


# Create a singleton instance
note_chunk = CRUDNoteChunk(NoteChunk)
