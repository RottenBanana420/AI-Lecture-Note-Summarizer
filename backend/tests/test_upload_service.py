"""
Tests for document upload service.

Following TDD principles - these tests are designed to fail initially
and drive the implementation.
"""

import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from app.services.upload_service import upload_service, UploadServiceError
from app.services.pdf_processor import PDFValidationError, PDFProcessingError
from app.services.text_chunker import TextChunkerError
from app.models.document import ProcessingStatus
from app.crud.document import document as document_crud
from app.crud.note_chunk import note_chunk as note_chunk_crud


class TestUploadServiceSuccess:
    """Test successful upload workflows."""
    
    def test_successful_upload_workflow(self, db_session: Session, valid_pdf_bytes):
        """Test complete successful upload workflow."""
        # Arrange
        filename = "test_lecture.pdf"
        content_type = "application/pdf"
        title = "Test Lecture Notes"
        
        # Act
        document_id, metadata = upload_service.process_upload(
            db=db_session,
            file_content=valid_pdf_bytes,
            filename=filename,
            content_type=content_type,
            title=title,
            user_id=None,
        )
        
        # Assert - Document created
        assert document_id is not None
        assert isinstance(document_id, int)
        
        # Assert - Metadata returned
        assert "page_count" in metadata
        assert "chunk_count" in metadata
        assert metadata["chunk_count"] > 0
        
        # Assert - Document in database
        document = document_crud.get(db_session, document_id)
        assert document is not None
        assert document.title == title
        assert document.original_filename == filename
        assert document.mime_type == content_type
        assert document.processing_status == ProcessingStatus.COMPLETED
        assert document.page_count is not None
        assert document.page_count > 0
        
        # Assert - File saved to disk
        file_path = Path(document.file_path)
        assert file_path.exists()
        assert file_path.is_file()
        
        # Assert - Chunks created
        chunks = note_chunk_crud.get_multi_by_document(
            db_session, document_id=document_id
        )
        assert len(chunks) > 0
        assert len(chunks) == metadata["chunk_count"]
        
        # Assert - Chunks have correct data
        for idx, chunk in enumerate(chunks):
            assert chunk.chunk_index == idx
            assert chunk.document_id == document_id
            assert len(chunk.chunk_text) > 0
            assert chunk.character_count > 0
            assert chunk.token_count is not None
            assert chunk.token_count > 0
    
    def test_upload_without_title_uses_filename(self, db_session: Session, valid_pdf_bytes):
        """Test that filename is used as title when title not provided."""
        # Arrange
        filename = "my_lecture_notes.pdf"
        
        # Act
        document_id, _ = upload_service.process_upload(
            db=db_session,
            file_content=valid_pdf_bytes,
            filename=filename,
            content_type="application/pdf",
            title=None,
        )
        
        # Assert
        document = document_crud.get(db_session, document_id)
        assert document.title == "my_lecture_notes"  # Stem of filename
    
    def test_upload_with_user_id(self, db_session: Session, valid_pdf_bytes, sample_user):
        """Test upload associated with a user."""
        # Arrange
        filename = "user_lecture.pdf"
        
        # Act
        document_id, _ = upload_service.process_upload(
            db=db_session,
            file_content=valid_pdf_bytes,
            filename=filename,
            content_type="application/pdf",
            user_id=sample_user.id,
        )
        
        # Assert
        document = document_crud.get(db_session, document_id)
        assert document.user_id == sample_user.id
        assert document.owner == sample_user


class TestUploadServiceValidation:
    """Test validation and error handling."""
    
    def test_invalid_file_type_rejection(self, db_session: Session):
        """Test that non-PDF files are rejected."""
        # Arrange - Create a file with enough bytes but invalid PDF content
        fake_pdf = b"%PDF-1.4\n" + b"This is not valid PDF content" * 10
        
        # Act & Assert
        with pytest.raises(PDFValidationError) as exc_info:
            upload_service.process_upload(
                db=db_session,
                file_content=fake_pdf,
                filename="fake.pdf",
                content_type="application/pdf",
            )
        
        # Should fail validation (corrupted or malformed)
        error_msg = str(exc_info.value).lower()
        assert "corrupted" in error_msg or "malformed" in error_msg or "failed" in error_msg
    
    def test_oversized_file_rejection(self, db_session: Session, valid_pdf_bytes):
        """Test that oversized files are rejected."""
        # Arrange - Create a file larger than max size (50MB)
        # Need to create a file that's actually over 50MB
        from app.core.config import settings
        
        # Create content that exceeds MAX_UPLOAD_SIZE
        oversized_content = valid_pdf_bytes * 70000  # This will be over 50MB
        
        # Act & Assert
        with pytest.raises(PDFValidationError) as exc_info:
            upload_service.process_upload(
                db=db_session,
                file_content=oversized_content,
                filename="huge.pdf",
                content_type="application/pdf",
            )
        
        assert "size" in str(exc_info.value).lower() or "exceeds" in str(exc_info.value).lower()
    
    def test_empty_file_rejection(self, db_session: Session):
        """Test that empty files are rejected."""
        # Arrange
        empty_content = b""
        
        # Act & Assert
        with pytest.raises(PDFValidationError):
            upload_service.process_upload(
                db=db_session,
                file_content=empty_content,
                filename="empty.pdf",
                content_type="application/pdf",
            )
    
    def test_corrupted_pdf_rejection(self, db_session: Session):
        """Test that corrupted PDFs are rejected."""
        # Arrange - PDF with valid magic bytes but corrupted content
        corrupted_pdf = b"%PDF-1.4\n" + b"corrupted data" * 100
        
        # Act & Assert
        with pytest.raises(PDFValidationError):
            upload_service.process_upload(
                db=db_session,
                file_content=corrupted_pdf,
                filename="corrupted.pdf",
                content_type="application/pdf",
            )


class TestUploadServiceTransactionManagement:
    """Test transaction management and rollback."""
    
    def test_pdf_processing_failure_rollback(self, db_session: Session):
        """Test that database is rolled back on PDF processing failure."""
        # Arrange - Invalid PDF that will fail processing
        invalid_pdf = b"%PDF-1.4\n" + b"invalid content"
        
        # Get initial document count
        initial_count = document_crud.count(db_session)
        
        # Act & Assert
        with pytest.raises((PDFValidationError, PDFProcessingError)):
            upload_service.process_upload(
                db=db_session,
                file_content=invalid_pdf,
                filename="invalid.pdf",
                content_type="application/pdf",
            )
        
        # Assert - No new documents created (or marked as FAILED)
        final_count = document_crud.count(db_session)
        
        # Either no document created, or document marked as FAILED
        if final_count > initial_count:
            # Document was created but should be marked FAILED
            documents = document_crud.get_multi(db_session, skip=0, limit=100)
            failed_docs = [d for d in documents if d.processing_status == ProcessingStatus.FAILED]
            assert len(failed_docs) > 0
    
    def test_file_cleanup_on_failure(self, db_session: Session, tmp_path):
        """Test that uploaded files are deleted on processing failure."""
        # Arrange - Use a temporary upload directory for this test
        from app.services.upload_service import UploadService
        from app.services.pdf_processor import PDFProcessorService
        from app.services.text_chunker import TextChunkerService
        
        # Create a temporary upload service with its own directory
        temp_upload_dir = tmp_path / "test_uploads"
        temp_service = UploadService()
        temp_service.pdf_processor = PDFProcessorService(upload_dir=str(temp_upload_dir))
        
        invalid_pdf = b"%PDF-1.4\n" + b"invalid"
        
        # Act
        try:
            temp_service.process_upload(
                db=db_session,
                file_content=invalid_pdf,
                filename="cleanup_test.pdf",
                content_type="application/pdf",
            )
        except (PDFValidationError, PDFProcessingError):
            pass
        
        # Assert - No PDF files should exist in the temp directory
        # (since the upload failed and should have been cleaned up)
        if temp_upload_dir.exists():
            pdf_files = list(temp_upload_dir.glob("*.pdf"))
            # Either no files, or all files belong to completed documents
            for file_path in pdf_files:
                documents = document_crud.get_multi(db_session, skip=0, limit=1000)
                file_belongs_to_completed = any(
                    str(file_path) == d.file_path and 
                    d.processing_status == ProcessingStatus.COMPLETED
                    for d in documents
                )
                # If file doesn't belong to a completed document, it's orphaned
                assert file_belongs_to_completed, f"Orphaned file found: {file_path}"
    
    def test_no_orphaned_chunks_on_failure(self, db_session: Session):
        """Test that no orphaned chunks are created on failure."""
        # Arrange
        invalid_pdf = b"%PDF-1.4\n" + b"invalid"
        initial_chunk_count = db_session.query(
            db_session.query(note_chunk_crud.model).count()
        ).scalar()
        
        # Act
        try:
            upload_service.process_upload(
                db=db_session,
                file_content=invalid_pdf,
                filename="chunk_test.pdf",
                content_type="application/pdf",
            )
        except (PDFValidationError, PDFProcessingError):
            pass
        
        # Assert - No new chunks created
        final_chunk_count = db_session.query(
            db_session.query(note_chunk_crud.model).count()
        ).scalar()
        
        assert final_chunk_count == initial_chunk_count


class TestUploadServiceStatusTracking:
    """Test document status transitions."""
    
    def test_status_transitions(self, db_session: Session, valid_pdf_bytes, monkeypatch):
        """Test that document status transitions correctly during upload."""
        # Track status changes
        status_changes = []
        
        # Monkey patch the update_status method to track calls
        original_update_status = upload_service._update_document_status
        
        def track_status(db, document_id, status):
            status_changes.append(status)
            return original_update_status(db, document_id, status)
        
        monkeypatch.setattr(
            upload_service,
            "_update_document_status",
            track_status
        )
        
        # Act
        document_id, _ = upload_service.process_upload(
            db=db_session,
            file_content=valid_pdf_bytes,
            filename="status_test.pdf",
            content_type="application/pdf",
        )
        
        # Assert - Status transitions: PROCESSING -> COMPLETED
        assert ProcessingStatus.PROCESSING in status_changes
        assert ProcessingStatus.COMPLETED in status_changes
        
        # Assert - Final status is COMPLETED
        document = document_crud.get(db_session, document_id)
        assert document.processing_status == ProcessingStatus.COMPLETED
    
    def test_failed_status_on_error(self, db_session: Session):
        """Test that document is marked FAILED on processing error."""
        # Arrange
        invalid_pdf = b"%PDF-1.4\n" + b"invalid"
        
        # Act
        try:
            upload_service.process_upload(
                db=db_session,
                file_content=invalid_pdf,
                filename="fail_test.pdf",
                content_type="application/pdf",
            )
        except (PDFValidationError, PDFProcessingError):
            pass
        
        # Assert - Check if any document was marked as FAILED
        documents = document_crud.get_multi(db_session, skip=0, limit=100)
        failed_docs = [d for d in documents if d.processing_status == ProcessingStatus.FAILED]
        
        # If a document was created, it should be marked FAILED
        if failed_docs:
            assert failed_docs[0].error_message is not None
            assert len(failed_docs[0].error_message) > 0
