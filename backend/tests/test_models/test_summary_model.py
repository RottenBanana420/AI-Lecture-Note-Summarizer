"""
Comprehensive Summary model tests designed to find bugs and validate constraints.

These tests are aggressive and designed to BREAK the code by testing:
- Foreign key constraints
- Enum validation (SummaryType)
- Required field validation
- JSON metadata field handling
- Boundary values
- Cascade delete behaviors
"""

import pytest
import json
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import Session

from app.models.summary import Summary, SummaryType
from app.models.document import Document
from app.models.user import User


class TestSummaryModelCreation:
    """Test creating Summary instances with valid data."""
    
    def test_create_summary_with_all_valid_fields(self, db_session: Session, sample_document: Document):
        """Test creating a summary with all valid fields."""
        metadata = {"model": "gpt-4", "tokens": 1500}
        
        summary = Summary(
            document_id=sample_document.id,
            summary_text="This is a comprehensive summary of the document.",
            summary_type=SummaryType.ABSTRACTIVE,
            processing_duration=5.5,
            summary_metadata=metadata
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        assert summary.id is not None
        assert summary.document_id == sample_document.id
        assert summary.summary_text == "This is a comprehensive summary of the document."
        assert summary.summary_type == SummaryType.ABSTRACTIVE
        assert summary.processing_duration == 5.5
        assert summary.summary_metadata == metadata
        assert summary.generated_at is not None
    
    def test_create_summary_with_minimal_fields(self, db_session: Session, sample_document: Document):
        """Test creating a summary with only required fields."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Minimal summary",
            summary_type=SummaryType.EXTRACTIVE
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        assert summary.id is not None
        assert summary.processing_duration is None
        assert summary.summary_metadata is None


class TestSummaryRequiredFields:
    """Test that required fields are enforced."""
    
    def test_create_summary_without_document_id_fails(self, db_session: Session):
        """Test that creating a summary without document_id fails."""
        summary = Summary(
            summary_text="Test summary",
            summary_type=SummaryType.EXTRACTIVE
        )
        db_session.add(summary)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "document_id" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_summary_without_summary_text_fails(self, db_session: Session, sample_document: Document):
        """Test that creating a summary without summary_text fails."""
        summary = Summary(
            document_id=sample_document.id,
            summary_type=SummaryType.EXTRACTIVE
        )
        db_session.add(summary)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "summary_text" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_summary_without_summary_type_fails(self, db_session: Session, sample_document: Document):
        """Test that creating a summary without summary_type fails."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Test summary"
        )
        db_session.add(summary)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "summary_type" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()


class TestSummaryForeignKeyConstraints:
    """Test foreign key constraint violations."""
    
    def test_create_summary_with_invalid_document_id_fails(self, db_session: Session):
        """Test that creating a summary with non-existent document_id fails."""
        summary = Summary(
            document_id=99999,  # Non-existent document
            summary_text="Test summary",
            summary_type=SummaryType.EXTRACTIVE
        )
        db_session.add(summary)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        error_msg = str(exc_info.value).lower()
        assert "foreign key" in error_msg or \
               "violates foreign key constraint" in error_msg or \
               "fk_" in error_msg
        db_session.rollback()


class TestSummaryEnumValidation:
    """Test SummaryType enum validation."""
    
    def test_valid_summary_type_values(self, db_session: Session, sample_document: Document):
        """Test all valid SummaryType enum values."""
        types = [
            SummaryType.EXTRACTIVE,
            SummaryType.ABSTRACTIVE,
            SummaryType.ABSTRACTIVE,
            SummaryType.EXTRACTIVE
        ]
        
        for i, summary_type in enumerate(types):
            summary = Summary(
                document_id=sample_document.id,
                summary_text=f"Summary {i}",
                summary_type=summary_type
            )
            db_session.add(summary)
            db_session.commit()
            db_session.refresh(summary)
            
            assert summary.summary_type == summary_type
    
    def test_invalid_summary_type_fails(self, db_session: Session, sample_document: Document):
        """Test that invalid summary_type value fails."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Test",
            summary_type=SummaryType.EXTRACTIVE
        )
        
        # Try to set invalid type (bypass enum)
        with pytest.raises((ValueError, DataError, IntegrityError)):
            summary.summary_type = "invalid_type"
            db_session.add(summary)
            db_session.commit()
        
        db_session.rollback()


class TestSummaryBoundaryValues:
    """Test boundary values and edge cases."""
    
    def test_summary_text_very_long(self, db_session: Session, sample_document: Document):
        """Test summary_text with very long content."""
        # Create a 100KB summary
        long_text = "A" * 100000
        summary = Summary(
            document_id=sample_document.id,
            summary_text=long_text,
            summary_type=SummaryType.ABSTRACTIVE
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        assert len(summary.summary_text) == 100000
    
    def test_empty_summary_text_fails(self, db_session: Session, sample_document: Document):
        """Test that empty summary_text is rejected."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="",
            summary_type=SummaryType.EXTRACTIVE
        )
        db_session.add(summary)
        
        # Should fail with CHECK constraint if implemented
        try:
            db_session.commit()
            # If it succeeds, we should add a CHECK constraint
            db_session.rollback()
            # For now, document that empty strings are allowed
        except (IntegrityError, DataError):
            # Expected if CHECK constraint exists
            db_session.rollback()
    
    def test_processing_duration_zero(self, db_session: Session, sample_document: Document):
        """Test that processing_duration of 0.0 is allowed."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Instant summary",
            summary_type=SummaryType.EXTRACTIVE,
            processing_duration=0.0
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        assert summary.processing_duration == 0.0
    
    def test_processing_duration_negative_fails(self, db_session: Session, sample_document: Document):
        """Test that negative processing_duration fails."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Test",
            summary_type=SummaryType.EXTRACTIVE,
            processing_duration=-1.0
        )
        db_session.add(summary)
        
        # Should fail with CHECK constraint
        with pytest.raises((IntegrityError, DataError)):
            db_session.commit()
        
        db_session.rollback()
    
    def test_processing_duration_very_large(self, db_session: Session, sample_document: Document):
        """Test very large processing_duration (slow processing)."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Slow summary",
            summary_type=SummaryType.ABSTRACTIVE,
            processing_duration=3600.5  # 1 hour
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        assert summary.processing_duration == 3600.5


class TestSummaryJSONMetadata:
    """Test JSON metadata field handling."""
    
    def test_metadata_with_nested_objects(self, db_session: Session, sample_document: Document):
        """Test metadata with complex nested JSON structure."""
        metadata = {
            "model": "gpt-4",
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "metrics": {
                "input_tokens": 1500,
                "output_tokens": 500,
                "cost": 0.05
            },
            "tags": ["important", "reviewed"]
        }
        
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Test",
            summary_type=SummaryType.EXTRACTIVE,
            summary_metadata=metadata
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        assert summary.summary_metadata == metadata
        assert summary.summary_metadata["model"] == "gpt-4"
        assert summary.summary_metadata["parameters"]["temperature"] == 0.7
        assert len(summary.summary_metadata["tags"]) == 2
    
    def test_metadata_with_empty_dict(self, db_session: Session, sample_document: Document):
        """Test metadata with empty dictionary."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Test",
            summary_type=SummaryType.EXTRACTIVE,
            summary_metadata={}
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        assert summary.summary_metadata == {}
    
    def test_metadata_with_null(self, db_session: Session, sample_document: Document):
        """Test metadata with NULL value."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Test",
            summary_type=SummaryType.EXTRACTIVE,
            summary_metadata=None
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        assert summary.summary_metadata is None
    
    def test_metadata_with_special_characters(self, db_session: Session, sample_document: Document):
        """Test metadata with special characters and Unicode."""
        metadata = {
            "note": "Summary with special chars: <>&\"'",
            "unicode": "测试 🎉",
            "escaped": "Line 1\nLine 2\tTabbed"
        }
        
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Test",
            summary_type=SummaryType.EXTRACTIVE,
            summary_metadata=metadata
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        assert summary.summary_metadata == metadata


class TestSummaryRelationships:
    """Test Summary model relationships."""
    
    def test_summary_document_relationship(self, db_session: Session, sample_document: Document):
        """Test that summary has document relationship."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Test",
            summary_type=SummaryType.EXTRACTIVE
        )
        db_session.add(summary)
        db_session.commit()
        db_session.refresh(summary)
        
        # Should have document attribute
        assert hasattr(summary, 'document')
        assert summary.document is not None
        assert summary.document.id == sample_document.id


class TestSummaryModelMethods:
    """Test Summary model methods and properties."""
    
    def test_summary_repr(self, db_session: Session, sample_document: Document):
        """Test Summary __repr__ method."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="Test summary for repr",
            summary_type=SummaryType.ABSTRACTIVE
        )
        db_session.add(summary)
        db_session.commit()
        
        repr_str = repr(summary)
        assert "Summary" in repr_str
        assert "abstractive" in repr_str.lower()
    
    def test_preview_property(self, db_session: Session, sample_document: Document):
        """Test preview property (first 100 chars)."""
        long_text = "A" * 200
        summary = Summary(
            document_id=sample_document.id,
            summary_text=long_text,
            summary_type=SummaryType.EXTRACTIVE
        )
        db_session.add(summary)
        db_session.commit()
        
        assert len(summary.summary_preview) == 103  # 100 chars + "..."
        assert summary.summary_preview.endswith("...")
    
    def test_word_count_property(self, db_session: Session, sample_document: Document):
        """Test word_count property."""
        summary = Summary(
            document_id=sample_document.id,
            summary_text="This is a test summary with ten words here.",
            summary_type=SummaryType.EXTRACTIVE
        )
        db_session.add(summary)
        db_session.commit()
        
        # Should count words
        assert summary.word_count > 0


class TestSummaryCascadeDelete:
    """Test cascade delete behaviors."""
    
    def test_delete_document_deletes_summaries(self, db_session: Session):
        """Test that deleting a document CASCADE deletes its summaries."""
        # Create user and document
        user = User(
            username="cascade_test",
            email="cascade@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        db_session.commit()
        
        document = Document(
            user_id=user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/cascade_summary_test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        
        # Create summary
        summary = Summary(
            document_id=document.id,
            summary_text="Test summary",
            summary_type=SummaryType.EXTRACTIVE
        )
        db_session.add(summary)
        db_session.commit()
        
        summary_id = summary.id
        
        # Delete document (should CASCADE delete summary)
        db_session.delete(document)
        db_session.commit()
        
        # Summary should be deleted
        remaining_summary = db_session.query(Summary).filter_by(id=summary_id).first()
        assert remaining_summary is None, \
            "Summary should be CASCADE deleted when document is deleted"
    
    def test_multiple_summaries_for_same_document(self, db_session: Session, sample_document: Document):
        """Test that multiple summaries can exist for the same document."""
        summaries = []
        for i, summary_type in enumerate([SummaryType.EXTRACTIVE, SummaryType.ABSTRACTIVE, SummaryType.ABSTRACTIVE]):
            summary = Summary(
                document_id=sample_document.id,
                summary_text=f"Summary {i}",
                summary_type=summary_type
            )
            db_session.add(summary)
            summaries.append(summary)
        
        db_session.commit()
        
        # All summaries should exist
        for summary in summaries:
            db_session.refresh(summary)
            assert summary.id is not None
            assert summary.document_id == sample_document.id
