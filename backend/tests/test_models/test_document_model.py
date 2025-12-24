"""
Comprehensive Document model tests designed to find bugs and validate constraints.

These tests are aggressive and designed to BREAK the code by testing:
- Foreign key constraints
- Enum validation (ProcessingStatus)
- Unique constraints (file_path)
- Required field validation
- Boundary values
- Cascade delete behaviors
"""

import pytest
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import Session

from app.models.document import Document, ProcessingStatus
from app.models.user import User


class TestDocumentModelCreation:
    """Test creating Document instances with valid data."""
    
    def test_create_document_with_all_valid_fields(self, db_session: Session, sample_user: User):
        """Test creating a document with all valid fields."""
        document = Document(
            user_id=sample_user.id,
            title="Test Document",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            processing_status=ProcessingStatus.PENDING
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert document.id is not None
        assert document.user_id == sample_user.id
        assert document.title == "Test Document"
        assert document.original_filename == "test.pdf"
        assert document.file_path == "/uploads/test.pdf"
        assert document.file_size == 1024
        assert document.mime_type == "application/pdf"
        assert document.processing_status == ProcessingStatus.PENDING
        assert document.uploaded_at is not None
    
    def test_create_document_with_minimal_fields(self, db_session: Session, sample_user: User):
        """Test creating a document with only required fields."""
        document = Document(
            user_id=sample_user.id,
            title="Minimal Doc",
            original_filename="min.pdf",
            file_path="/uploads/min.pdf",
            file_size=100,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert document.id is not None
        assert document.processing_status == ProcessingStatus.PENDING  # Default value
    
    def test_create_document_with_null_user_id(self, db_session: Session):
        """Test creating a document with NULL user_id (should succeed - nullable=True)."""
        document = Document(
            user_id=None,
            title="No User Doc",
            original_filename="nouser.pdf",
            file_path="/uploads/nouser.pdf",
            file_size=100,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert document.user_id is None


class TestDocumentRequiredFields:
    """Test that required fields are enforced."""
    
    def test_create_document_without_title_fails(self, db_session: Session, sample_user: User):
        """Test that creating a document without title fails."""
        document = Document(
            user_id=sample_user.id,
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "title" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_document_without_original_filename_fails(self, db_session: Session, sample_user: User):
        """Test that creating a document without original_filename fails."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            file_path="/uploads/test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "original_filename" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_document_without_file_path_fails(self, db_session: Session, sample_user: User):
        """Test that creating a document without file_path fails."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "file_path" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_document_without_file_size_fails(self, db_session: Session, sample_user: User):
        """Test that creating a document without file_size fails."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            mime_type="application/pdf"
        )
        db_session.add(document)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "file_size" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_document_without_mime_type_fails(self, db_session: Session, sample_user: User):
        """Test that creating a document without mime_type fails."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024
        )
        db_session.add(document)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "mime_type" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()


class TestDocumentForeignKeyConstraints:
    """Test foreign key constraint violations."""
    
    def test_create_document_with_invalid_user_id_fails(self, db_session: Session):
        """Test that creating a document with non-existent user_id fails."""
        document = Document(
            user_id=99999,  # Non-existent user
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/test_invalid_user.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        error_msg = str(exc_info.value).lower()
        assert "foreign key" in error_msg or \
               "violates foreign key constraint" in error_msg or \
               "fk_" in error_msg
        db_session.rollback()


class TestDocumentUniqueConstraints:
    """Test unique constraint violations."""
    
    def test_duplicate_file_path_fails(self, db_session: Session, sample_user: User):
        """Test that duplicate file_path raises IntegrityError."""
        # Create first document
        doc1 = Document(
            user_id=sample_user.id,
            title="Doc 1",
            original_filename="test1.pdf",
            file_path="/uploads/duplicate.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(doc1)
        db_session.commit()
        
        # Try to create second document with same file_path
        doc2 = Document(
            user_id=sample_user.id,
            title="Doc 2",
            original_filename="test2.pdf",
            file_path="/uploads/duplicate.pdf",  # Same path
            file_size=2048,
            mime_type="application/pdf"
        )
        db_session.add(doc2)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        error_msg = str(exc_info.value).lower()
        assert "unique" in error_msg or "duplicate" in error_msg
        assert "file_path" in error_msg
        db_session.rollback()


class TestDocumentEnumValidation:
    """Test ProcessingStatus enum validation."""
    
    def test_valid_processing_status_values(self, db_session: Session, sample_user: User):
        """Test all valid ProcessingStatus enum values."""
        statuses = [
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED
        ]
        
        for i, status in enumerate(statuses):
            doc = Document(
                user_id=sample_user.id,
                title=f"Doc {i}",
                original_filename=f"test{i}.pdf",
                file_path=f"/uploads/test{i}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                processing_status=status
            )
            db_session.add(doc)
            db_session.commit()
            db_session.refresh(doc)
            
            assert doc.processing_status == status
    
    def test_invalid_processing_status_fails(self, db_session: Session, sample_user: User):
        """Test that invalid processing_status value fails."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/invalid_status.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        
        # Try to set invalid status (bypass enum)
        with pytest.raises((ValueError, DataError, IntegrityError)):
            # This should fail at Python level (ValueError) or DB level (DataError)
            document.processing_status = "invalid_status"
            db_session.add(document)
            db_session.commit()
        
        db_session.rollback()
    
    def test_default_processing_status(self, db_session: Session, sample_user: User):
        """Test that default processing_status is PENDING."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/default_status.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert document.processing_status == ProcessingStatus.PENDING


class TestDocumentBoundaryValues:
    """Test boundary values and edge cases."""
    
    def test_title_at_max_length(self, db_session: Session, sample_user: User):
        """Test title at maximum length (255 chars)."""
        max_title = "A" * 255
        document = Document(
            user_id=sample_user.id,
            title=max_title,
            original_filename="test.pdf",
            file_path="/uploads/max_title.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert len(document.title) == 255
    
    def test_title_exceeds_max_length_fails(self, db_session: Session, sample_user: User):
        """Test that title exceeding 255 chars fails."""
        too_long_title = "A" * 256
        document = Document(
            user_id=sample_user.id,
            title=too_long_title,
            original_filename="test.pdf",
            file_path="/uploads/toolong_title.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        
        with pytest.raises(DataError) as exc_info:
            db_session.commit()
        
        assert "value too long" in str(exc_info.value).lower() or \
               "string" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_file_path_at_max_length(self, db_session: Session, sample_user: User):
        """Test file_path at maximum length (500 chars)."""
        max_path = "/uploads/" + "a" * 490
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path=max_path,
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert len(document.file_path) <= 500
    
    def test_file_size_zero(self, db_session: Session, sample_user: User):
        """Test that file_size of 0 is allowed."""
        document = Document(
            user_id=sample_user.id,
            title="Empty File",
            original_filename="empty.txt",
            file_path="/uploads/empty.txt",
            file_size=0,
            mime_type="text/plain"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert document.file_size == 0
    
    def test_file_size_negative_fails(self, db_session: Session, sample_user: User):
        """Test that negative file_size fails."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/negative_size.pdf",
            file_size=-1,
            mime_type="application/pdf"
        )
        db_session.add(document)
        
        # Should fail with CHECK constraint or data type constraint
        with pytest.raises((IntegrityError, DataError)):
            db_session.commit()
        
        db_session.rollback()
    
    def test_file_size_very_large(self, db_session: Session, sample_user: User):
        """Test very large file_size (within BigInteger range)."""
        large_size = 10 * 1024 * 1024 * 1024  # 10 GB
        document = Document(
            user_id=sample_user.id,
            title="Large File",
            original_filename="large.zip",
            file_path="/uploads/large.zip",
            file_size=large_size,
            mime_type="application/zip"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        assert document.file_size == large_size


class TestDocumentRelationships:
    """Test Document model relationships."""
    
    def test_document_owner_relationship(self, db_session: Session, sample_user: User):
        """Test that document has owner relationship."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/owner_test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        # Should have owner attribute
        assert hasattr(document, 'owner')
        assert document.owner is not None
        assert document.owner.id == sample_user.id
    
    def test_document_summaries_relationship(self, db_session: Session, sample_user: User):
        """Test that document has summaries relationship."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/summaries_test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        # Should have summaries attribute
        assert hasattr(document, 'summaries')
        summaries = document.summaries.all()
        assert isinstance(summaries, list)
        assert len(summaries) == 0  # No summaries yet
    
    def test_document_note_chunks_relationship(self, db_session: Session, sample_user: User):
        """Test that document has note_chunks relationship."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/chunks_test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        db_session.refresh(document)
        
        # Should have note_chunks attribute
        assert hasattr(document, 'note_chunks')
        chunks = document.note_chunks.all()
        assert isinstance(chunks, list)
        assert len(chunks) == 0  # No chunks yet


class TestDocumentModelMethods:
    """Test Document model methods and properties."""
    
    def test_document_repr(self, db_session: Session, sample_user: User):
        """Test Document __repr__ method."""
        document = Document(
            user_id=sample_user.id,
            title="Test Doc",
            original_filename="test.pdf",
            file_path="/uploads/repr_test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            processing_status=ProcessingStatus.COMPLETED
        )
        db_session.add(document)
        db_session.commit()
        
        repr_str = repr(document)
        assert "Document" in repr_str
        assert "Test Doc" in repr_str
        assert "completed" in repr_str.lower()
    
    def test_size_mb_property(self, db_session: Session, sample_user: User):
        """Test size_mb property conversion."""
        # 1 MB = 1024 * 1024 bytes
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/size_mb_test.pdf",
            file_size=1024 * 1024,  # 1 MB
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        
        assert document.size_mb == 1.0
        
        # Test with 2.5 MB
        document.file_size = int(2.5 * 1024 * 1024)
        db_session.commit()
        
        assert document.size_mb == 2.5
    
    def test_is_processed_property(self, db_session: Session, sample_user: User):
        """Test is_processed property."""
        document = Document(
            user_id=sample_user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/processed_test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            processing_status=ProcessingStatus.PENDING
        )
        db_session.add(document)
        db_session.commit()
        
        assert document.is_processed is False
        
        document.processing_status = ProcessingStatus.COMPLETED
        db_session.commit()
        
        assert document.is_processed is True


class TestDocumentCascadeDelete:
    """Test cascade delete behaviors."""
    
    def test_delete_user_with_documents(self, db_session: Session):
        """Test that deleting a user CASCADE deletes their documents."""
        # Create user
        user = User(
            username="cascade_test",
            email="cascade@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create document
        document = Document(
            user_id=user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/cascade_test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        
        doc_id = document.id
        
        # Delete user (should CASCADE delete documents due to ondelete="CASCADE")
        db_session.delete(user)
        db_session.commit()
        
        # Document should be deleted due to CASCADE
        remaining_doc = db_session.query(Document).filter_by(id=doc_id).first()
        assert remaining_doc is None, \
            "Document should be CASCADE deleted when user is deleted"
