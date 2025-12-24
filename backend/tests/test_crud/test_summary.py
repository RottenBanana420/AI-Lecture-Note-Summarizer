"""
Tests for Summary CRUD operations.

Following TDD approach - these tests are written first and should fail initially.
"""

import pytest
from sqlalchemy.orm import Session

from app.crud.summary import summary as summary_crud
from app.crud.document import document as document_crud
from app.crud.user import user as user_crud
from app.crud.exceptions import RecordNotFoundError
from app.models.summary import Summary, SummaryType


class TestSummaryCRUD:
    """Test Summary CRUD operations."""
    
    @pytest.fixture
    def test_document(self, db: Session):
        """Create a test document for summary tests."""
        user = user_crud.create_user(
            db,
            username="summaryuser",
            email="summaryuser@example.com",
            hashed_password="password",
        )
        doc = document_crud.create_document(
            db,
            title="Summary Test Doc",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/summary_test.pdf",
            user_id=user.id,
        )
        db.commit()
        return doc
    
    def test_create_summary(self, db: Session, test_document):
        """Test creating a new summary."""
        summary_text = "This is a test summary of the document."
        summary_type = SummaryType.EXTRACTIVE
        processing_duration = 1.5
        metadata = {"model": "test-model", "version": "1.0"}
        
        summary = summary_crud.create_summary(
            db,
            document_id=test_document.id,
            summary_text=summary_text,
            summary_type=summary_type,
            processing_duration=processing_duration,
            summary_metadata=metadata,
        )
        db.commit()
        
        assert summary.id is not None
        assert summary.document_id == test_document.id
        assert summary.summary_text == summary_text
        assert summary.summary_type == summary_type
        assert summary.processing_duration == processing_duration
        assert summary.summary_metadata == metadata
        assert summary.generated_at is not None
    
    def test_get_summary_by_id(self, db: Session, test_document):
        """Test getting summary by ID."""
        summary = summary_crud.create_summary(
            db,
            document_id=test_document.id,
            summary_text="Test summary",
            summary_type=SummaryType.ABSTRACTIVE,
        )
        db.commit()
        
        retrieved_summary = summary_crud.get(db, summary.id)
        
        assert retrieved_summary is not None
        assert retrieved_summary.id == summary.id
        assert retrieved_summary.summary_text == summary.summary_text
    
    def test_get_summary_not_found(self, db: Session):
        """Test getting non-existent summary returns None."""
        summary = summary_crud.get(db, 99999)
        assert summary is None
    
    def test_get_multi_by_document(self, db: Session, test_document):
        """Test getting all summaries for a document."""
        # Create multiple summaries
        summary_crud.create_summary(
            db,
            document_id=test_document.id,
            summary_text="Extractive summary",
            summary_type=SummaryType.EXTRACTIVE,
        )
        summary_crud.create_summary(
            db,
            document_id=test_document.id,
            summary_text="Abstractive summary",
            summary_type=SummaryType.ABSTRACTIVE,
        )
        db.commit()
        
        summaries = summary_crud.get_multi_by_document(
            db, document_id=test_document.id
        )
        
        assert len(summaries) == 2
        assert all(s.document_id == test_document.id for s in summaries)
    
    def test_get_by_type(self, db: Session, test_document):
        """Test getting summary by type."""
        # Create both types
        extractive = summary_crud.create_summary(
            db,
            document_id=test_document.id,
            summary_text="Extractive summary",
            summary_type=SummaryType.EXTRACTIVE,
        )
        abstractive = summary_crud.create_summary(
            db,
            document_id=test_document.id,
            summary_text="Abstractive summary",
            summary_type=SummaryType.ABSTRACTIVE,
        )
        db.commit()
        
        # Get extractive
        retrieved_extractive = summary_crud.get_by_type(
            db,
            document_id=test_document.id,
            summary_type=SummaryType.EXTRACTIVE,
        )
        
        assert retrieved_extractive is not None
        assert retrieved_extractive.id == extractive.id
        assert retrieved_extractive.summary_type == SummaryType.EXTRACTIVE
        
        # Get abstractive
        retrieved_abstractive = summary_crud.get_by_type(
            db,
            document_id=test_document.id,
            summary_type=SummaryType.ABSTRACTIVE,
        )
        
        assert retrieved_abstractive is not None
        assert retrieved_abstractive.id == abstractive.id
        assert retrieved_abstractive.summary_type == SummaryType.ABSTRACTIVE
    
    def test_get_by_type_not_found(self, db: Session, test_document):
        """Test getting non-existent summary type returns None."""
        summary = summary_crud.get_by_type(
            db,
            document_id=test_document.id,
            summary_type=SummaryType.EXTRACTIVE,
        )
        assert summary is None
    
    def test_delete_summary(self, db: Session, test_document):
        """Test deleting a summary."""
        summary = summary_crud.create_summary(
            db,
            document_id=test_document.id,
            summary_text="Delete test",
            summary_type=SummaryType.EXTRACTIVE,
        )
        db.commit()
        summary_id = summary.id
        
        # Delete summary
        deleted_summary = summary_crud.delete(db, id=summary_id)
        db.commit()
        
        assert deleted_summary.id == summary_id
        
        # Verify summary no longer exists
        retrieved_summary = summary_crud.get(db, summary_id)
        assert retrieved_summary is None
    
    def test_delete_by_document(self, db: Session, test_document):
        """Test deleting all summaries for a document."""
        # Create multiple summaries
        for i in range(3):
            summary_crud.create_summary(
                db,
                document_id=test_document.id,
                summary_text=f"Summary {i}",
                summary_type=SummaryType.EXTRACTIVE if i % 2 == 0 else SummaryType.ABSTRACTIVE,
            )
        db.commit()
        
        # Delete all summaries
        count = summary_crud.delete_by_document(db, document_id=test_document.id)
        db.commit()
        
        assert count == 3
        
        # Verify no summaries remain
        summaries = summary_crud.get_multi_by_document(
            db, document_id=test_document.id
        )
        assert len(summaries) == 0
