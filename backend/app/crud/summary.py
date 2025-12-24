"""
Summary CRUD repository implementation.

This module provides CRUD operations specific to the Summary model.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.crud.base import CRUDBase
from app.models.summary import Summary, SummaryType
from app.crud.exceptions import RecordNotFoundError
import logging

logger = logging.getLogger(__name__)


class CRUDSummary(CRUDBase[Summary]):
    """CRUD operations for Summary model."""
    
    def create_summary(
        self,
        db: Session,
        *,
        document_id: int,
        summary_text: str,
        summary_type: SummaryType,
        processing_duration: Optional[float] = None,
        summary_metadata: Optional[dict] = None
    ) -> Summary:
        """
        Create a new summary record.
        
        Args:
            db: Database session
            document_id: Document ID this summary belongs to
            summary_text: The generated summary text
            summary_type: Type of summary (extractive/abstractive)
            processing_duration: Time taken to generate summary
            summary_metadata: Additional metadata
            
        Returns:
            Created Summary instance
        """
        summary_data = {
            "document_id": document_id,
            "summary_text": summary_text,
            "summary_type": summary_type,
            "processing_duration": processing_duration,
            "summary_metadata": summary_metadata,
        }
        return self.create(db, obj_in=summary_data)
    
    def get_multi_by_document(
        self,
        db: Session,
        *,
        document_id: int
    ) -> List[Summary]:
        """
        Get all summaries for a document.
        
        Args:
            db: Database session
            document_id: Document ID
            
        Returns:
            List of Summary instances
        """
        logger.debug(f"Getting summaries for document_id={document_id}")
        
        result = db.execute(
            select(Summary).where(Summary.document_id == document_id)
        )
        summaries = result.scalars().all()
        
        logger.debug(f"Found {len(summaries)} summaries for document_id={document_id}")
        return list(summaries)
    
    def get_by_type(
        self,
        db: Session,
        *,
        document_id: int,
        summary_type: SummaryType
    ) -> Optional[Summary]:
        """
        Get summary by type for a document.
        
        Args:
            db: Database session
            document_id: Document ID
            summary_type: Type of summary to retrieve
            
        Returns:
            Summary instance if found, None otherwise
        """
        logger.debug(
            f"Getting {summary_type} summary for document_id={document_id}"
        )
        
        result = db.execute(
            select(Summary).where(
                Summary.document_id == document_id,
                Summary.summary_type == summary_type
            )
        )
        summary = result.scalar_one_or_none()
        
        if summary:
            logger.debug(f"Found {summary_type} summary for document_id={document_id}")
        else:
            logger.debug(f"No {summary_type} summary found for document_id={document_id}")
        
        return summary
    
    def delete_by_document(self, db: Session, *, document_id: int) -> int:
        """
        Delete all summaries for a document.
        
        Args:
            db: Database session
            document_id: Document ID
            
        Returns:
            Number of summaries deleted
        """
        logger.info(f"Deleting all summaries for document_id={document_id}")
        
        summaries = self.get_multi_by_document(db, document_id=document_id)
        count = len(summaries)
        
        for summary in summaries:
            db.delete(summary)
        
        db.flush()
        logger.info(f"Deleted {count} summaries for document_id={document_id}")
        return count


# Create a singleton instance
summary = CRUDSummary(Summary)
