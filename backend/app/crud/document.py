"""
Document CRUD repository implementation.

This module provides CRUD operations specific to the Document model.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.crud.base import CRUDBase
from app.models.document import Document, ProcessingStatus
from app.crud.exceptions import RecordNotFoundError
import logging

logger = logging.getLogger(__name__)


class CRUDDocument(CRUDBase[Document]):
    """CRUD operations for Document model."""
    
    def create_document(
        self,
        db: Session,
        *,
        title: str,
        original_filename: str,
        file_size: int,
        mime_type: str,
        file_path: str,
        user_id: Optional[int] = None,
        processing_status: ProcessingStatus = ProcessingStatus.PENDING
    ) -> Document:
        """
        Create a new document record.
        
        Args:
            db: Database session
            title: Document title
            original_filename: Original filename
            file_size: File size in bytes
            mime_type: MIME type
            file_path: Storage path
            user_id: User ID who uploaded the document
            processing_status: Initial processing status
            
        Returns:
            Created Document instance
        """
        document_data = {
            "title": title,
            "original_filename": original_filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "file_path": file_path,
            "user_id": user_id,
            "processing_status": processing_status,
        }
        return self.create(db, obj_in=document_data)
    
    def get_multi_by_user(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        status: Optional[ProcessingStatus] = None
    ) -> List[Document]:
        """
        Get all documents for a user with optional status filter.
        
        Args:
            db: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records
            status: Optional processing status filter
            
        Returns:
            List of Document instances
        """
        logger.debug(
            f"Getting documents for user_id={user_id}, skip={skip}, "
            f"limit={limit}, status={status}"
        )
        
        query = select(Document).where(Document.user_id == user_id)
        
        if status:
            query = query.where(Document.processing_status == status)
        
        query = query.offset(skip).limit(limit)
        result = db.execute(query)
        documents = result.scalars().all()
        
        logger.debug(f"Found {len(documents)} documents for user_id={user_id}")
        return list(documents)
    
    def get_by_status(
        self,
        db: Session,
        *,
        status: ProcessingStatus,
        skip: int = 0,
        limit: int = 50
    ) -> List[Document]:
        """
        Get documents by processing status.
        
        Args:
            db: Database session
            status: Processing status to filter by
            skip: Number of records to skip
            limit: Maximum number of records
            
        Returns:
            List of Document instances
        """
        logger.debug(
            f"Getting documents with status={status}, skip={skip}, limit={limit}"
        )
        
        query = select(Document).where(
            Document.processing_status == status
        ).offset(skip).limit(limit)
        
        result = db.execute(query)
        documents = result.scalars().all()
        
        logger.debug(f"Found {len(documents)} documents with status={status}")
        return list(documents)
    
    def update_document(
        self,
        db: Session,
        *,
        document_id: int,
        update_data: dict
    ) -> Document:
        """
        Update document metadata.
        
        Args:
            db: Database session
            document_id: Document ID to update
            update_data: Dictionary of fields to update
            
        Returns:
            Updated Document instance
            
        Raises:
            RecordNotFoundError: If document not found
        """
        document = self.get_or_404(db, document_id)
        return self.update(db, db_obj=document, obj_in=update_data)
    
    def update_status(
        self,
        db: Session,
        *,
        document_id: int,
        status: ProcessingStatus
    ) -> Document:
        """
        Update document processing status.
        
        Args:
            db: Database session
            document_id: Document ID
            status: New processing status
            
        Returns:
            Updated Document instance
            
        Raises:
            RecordNotFoundError: If document not found
        """
        logger.info(f"Updating document {document_id} status to {status}")
        return self.update_document(
            db,
            document_id=document_id,
            update_data={"processing_status": status}
        )
    
    def count_by_user(self, db: Session, *, user_id: int) -> int:
        """
        Count documents for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Count of documents
        """
        logger.debug(f"Counting documents for user_id={user_id}")
        result = db.execute(
            select(func.count()).select_from(Document).where(
                Document.user_id == user_id
            )
        )
        count = result.scalar()
        logger.debug(f"User {user_id} has {count} documents")
        return count
    
    def get_total_size_by_user(self, db: Session, *, user_id: int) -> int:
        """
        Get total file size for user's documents.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Total file size in bytes
        """
        logger.debug(f"Calculating total file size for user_id={user_id}")
        result = db.execute(
            select(func.sum(Document.file_size)).where(
                Document.user_id == user_id
            )
        )
        total_size = result.scalar() or 0
        logger.debug(f"User {user_id} total file size: {total_size} bytes")
        return total_size


# Create a singleton instance
document = CRUDDocument(Document)
