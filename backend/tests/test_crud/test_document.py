"""
Tests for Document CRUD operations.

Following TDD approach - these tests are written first and should fail initially.
"""

import pytest
from sqlalchemy.orm import Session

from app.crud.document import document as document_crud
from app.crud.user import user as user_crud
from app.crud.exceptions import RecordNotFoundError
from app.models.document import Document, ProcessingStatus


class TestDocumentCRUD:
    """Test Document CRUD operations."""
    
    @pytest.fixture
    def test_user(self, db: Session):
        """Create a test user for document tests."""
        user = user_crud.create_user(
            db,
            username="docuser",
            email="docuser@example.com",
            hashed_password="password",
        )
        db.commit()
        return user
    
    def test_create_document(self, db: Session, test_user):
        """Test creating a new document."""
        title = "Test Document"
        original_filename = "test.pdf"
        file_size = 1024
        mime_type = "application/pdf"
        file_path = "/uploads/test.pdf"
        
        doc = document_crud.create_document(
            db,
            title=title,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            file_path=file_path,
            user_id=test_user.id,
        )
        db.commit()
        
        assert doc.id is not None
        assert doc.title == title
        assert doc.original_filename == original_filename
        assert doc.file_size == file_size
        assert doc.mime_type == mime_type
        assert doc.file_path == file_path
        assert doc.user_id == test_user.id
        assert doc.processing_status == ProcessingStatus.PENDING
        assert doc.uploaded_at is not None
    
    def test_get_document_by_id(self, db: Session, test_user):
        """Test getting document by ID."""
        doc = document_crud.create_document(
            db,
            title="Get By ID Test",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/test1.pdf",
            user_id=test_user.id,
        )
        db.commit()
        
        retrieved_doc = document_crud.get(db, doc.id)
        
        assert retrieved_doc is not None
        assert retrieved_doc.id == doc.id
        assert retrieved_doc.title == doc.title
    
    def test_get_document_not_found(self, db: Session):
        """Test getting non-existent document returns None."""
        doc = document_crud.get(db, 99999)
        assert doc is None
    
    def test_get_or_404_raises_error(self, db: Session):
        """Test get_or_404 raises RecordNotFoundError."""
        with pytest.raises(RecordNotFoundError) as exc_info:
            document_crud.get_or_404(db, 99999)
        
        assert "Document" in str(exc_info.value)
    
    def test_get_multi_by_user(self, db: Session, test_user):
        """Test getting all documents for a user."""
        # Create multiple documents
        for i in range(5):
            document_crud.create_document(
                db,
                title=f"Document {i}",
                original_filename=f"doc{i}.pdf",
                file_size=1024 * i,
                mime_type="application/pdf",
                file_path=f"/uploads/doc{i}.pdf",
                user_id=test_user.id,
            )
        db.commit()
        
        # Get all documents for user
        docs = document_crud.get_multi_by_user(db, user_id=test_user.id)
        
        assert len(docs) == 5
        assert all(doc.user_id == test_user.id for doc in docs)
    
    def test_get_multi_by_user_with_pagination(self, db: Session, test_user):
        """Test pagination when getting user documents."""
        # Create 10 documents
        for i in range(10):
            document_crud.create_document(
                db,
                title=f"Document {i}",
                original_filename=f"doc{i}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                file_path=f"/uploads/doc{i}.pdf",
                user_id=test_user.id,
            )
        db.commit()
        
        # Get first 5
        docs_page1 = document_crud.get_multi_by_user(
            db, user_id=test_user.id, skip=0, limit=5
        )
        assert len(docs_page1) == 5
        
        # Get next 5
        docs_page2 = document_crud.get_multi_by_user(
            db, user_id=test_user.id, skip=5, limit=5
        )
        assert len(docs_page2) == 5
        
        # Ensure different documents
        page1_ids = {doc.id for doc in docs_page1}
        page2_ids = {doc.id for doc in docs_page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_get_multi_by_user_with_status_filter(self, db: Session, test_user):
        """Test filtering documents by status."""
        # Create documents with different statuses
        document_crud.create_document(
            db,
            title="Pending Doc",
            original_filename="pending.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/pending.pdf",
            user_id=test_user.id,
            processing_status=ProcessingStatus.PENDING,
        )
        document_crud.create_document(
            db,
            title="Processing Doc",
            original_filename="processing.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/processing.pdf",
            user_id=test_user.id,
            processing_status=ProcessingStatus.PROCESSING,
        )
        document_crud.create_document(
            db,
            title="Completed Doc",
            original_filename="completed.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/completed.pdf",
            user_id=test_user.id,
            processing_status=ProcessingStatus.COMPLETED,
        )
        db.commit()
        
        # Get only completed documents
        completed_docs = document_crud.get_multi_by_user(
            db, user_id=test_user.id, status=ProcessingStatus.COMPLETED
        )
        
        assert len(completed_docs) == 1
        assert completed_docs[0].processing_status == ProcessingStatus.COMPLETED
    
    def test_get_by_status(self, db: Session, test_user):
        """Test getting documents by status across all users."""
        # Create documents with different statuses
        for status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING, ProcessingStatus.COMPLETED]:
            document_crud.create_document(
                db,
                title=f"{status.value} Doc",
                original_filename=f"{status.value}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                file_path=f"/uploads/{status.value}.pdf",
                user_id=test_user.id,
                processing_status=status,
            )
        db.commit()
        
        # Get pending documents
        pending_docs = document_crud.get_by_status(
            db, status=ProcessingStatus.PENDING
        )
        
        assert len(pending_docs) >= 1
        assert all(doc.processing_status == ProcessingStatus.PENDING for doc in pending_docs)
    
    def test_update_document(self, db: Session, test_user):
        """Test updating document metadata."""
        doc = document_crud.create_document(
            db,
            title="Original Title",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/test.pdf",
            user_id=test_user.id,
        )
        db.commit()
        
        # Update title
        new_title = "Updated Title"
        updated_doc = document_crud.update_document(
            db,
            document_id=doc.id,
            update_data={"title": new_title},
        )
        db.commit()
        
        assert updated_doc.id == doc.id
        assert updated_doc.title == new_title
        assert updated_doc.original_filename == doc.original_filename
    
    def test_update_document_not_found(self, db: Session):
        """Test updating non-existent document raises error."""
        with pytest.raises(RecordNotFoundError):
            document_crud.update_document(
                db,
                document_id=99999,
                update_data={"title": "New Title"},
            )
    
    def test_update_status(self, db: Session, test_user):
        """Test updating document processing status."""
        doc = document_crud.create_document(
            db,
            title="Status Test",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/status.pdf",
            user_id=test_user.id,
            processing_status=ProcessingStatus.PENDING,
        )
        db.commit()
        
        # Update to processing
        updated_doc = document_crud.update_status(
            db,
            document_id=doc.id,
            status=ProcessingStatus.PROCESSING,
        )
        db.commit()
        
        assert updated_doc.processing_status == ProcessingStatus.PROCESSING
        
        # Update to completed
        updated_doc = document_crud.update_status(
            db,
            document_id=doc.id,
            status=ProcessingStatus.COMPLETED,
        )
        db.commit()
        
        assert updated_doc.processing_status == ProcessingStatus.COMPLETED
    
    def test_delete_document(self, db: Session, test_user):
        """Test deleting a document."""
        doc = document_crud.create_document(
            db,
            title="Delete Test",
            original_filename="delete.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/delete.pdf",
            user_id=test_user.id,
        )
        db.commit()
        doc_id = doc.id
        
        # Delete document
        deleted_doc = document_crud.delete(db, id=doc_id)
        db.commit()
        
        assert deleted_doc.id == doc_id
        
        # Verify document no longer exists
        retrieved_doc = document_crud.get(db, doc_id)
        assert retrieved_doc is None
    
    def test_count_by_user(self, db: Session, test_user):
        """Test counting documents for a user."""
        initial_count = document_crud.count_by_user(db, user_id=test_user.id)
        
        # Create 3 documents
        for i in range(3):
            document_crud.create_document(
                db,
                title=f"Count Test {i}",
                original_filename=f"count{i}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                file_path=f"/uploads/count{i}.pdf",
                user_id=test_user.id,
            )
        db.commit()
        
        new_count = document_crud.count_by_user(db, user_id=test_user.id)
        assert new_count == initial_count + 3
    
    def test_get_total_size_by_user(self, db: Session, test_user):
        """Test calculating total file size for user."""
        # Create documents with different sizes
        sizes = [1024, 2048, 4096]
        for i, size in enumerate(sizes):
            document_crud.create_document(
                db,
                title=f"Size Test {i}",
                original_filename=f"size{i}.pdf",
                file_size=size,
                mime_type="application/pdf",
                file_path=f"/uploads/size{i}.pdf",
                user_id=test_user.id,
            )
        db.commit()
        
        total_size = document_crud.get_total_size_by_user(db, user_id=test_user.id)
        assert total_size >= sum(sizes)
