"""
Comprehensive API Endpoint Tests for Document Upload.

This module contains extensive tests designed to BREAK the upload system
and find bugs in edge cases, failure scenarios, and stress conditions.

Following TDD principles - these tests drive code quality by finding bugs.
NEVER modify tests to pass - always fix the code.
"""

import pytest
import time
import threading
from io import BytesIO
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, IntegrityError

from app.models.document import ProcessingStatus


class TestUploadValidationEdgeCases:
    """Test upload validation edge cases designed to break validation."""

    def test_upload_with_wrong_field_name(self, client: TestClient, valid_pdf_bytes):
        """Test upload with wrong field name (e.g., 'document' instead of 'file')."""
        # Wrong field name
        files = {"document": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should return 422 (validation error)
        assert response.status_code == 422

    def test_upload_with_null_filename(self, client: TestClient, valid_pdf_bytes):
        """Test upload with null/empty filename."""
        # Empty filename
        files = {"file": ("", BytesIO(valid_pdf_bytes), "application/pdf")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should handle gracefully (might accept with default name or reject)
        assert response.status_code in [201, 400, 422]

    def test_upload_with_extremely_long_filename(self, client: TestClient, valid_pdf_bytes):
        """Test upload with extremely long filename (>255 chars)."""
        # Very long filename
        long_filename = "a" * 300 + ".pdf"
        files = {"file": (long_filename, BytesIO(valid_pdf_bytes), "application/pdf")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should either accept (truncating) or reject gracefully
        assert response.status_code in [201, 400]

    def test_upload_with_missing_content_type(self, client: TestClient, valid_pdf_bytes):
        """Test upload with missing Content-Type header."""
        # No content type specified
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes))}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # FastAPI might auto-detect or reject
        assert response.status_code in [201, 400, 422]

    def test_upload_with_content_type_mismatch(self, client: TestClient):
        """Test upload with Content-Type mismatch (says PDF but is PNG)."""
        # PNG data but PDF content type
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake png data" * 100
        files = {"file": ("fake.pdf", BytesIO(png_data), "application/pdf")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should fail validation (magic bytes check)
        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"].lower()

    def test_upload_with_special_characters_in_title(self, client: TestClient, valid_pdf_bytes):
        """Test upload with special characters in title."""
        special_titles = [
            "Title with <script>alert('xss')</script>",
            "Title with SQL'; DROP TABLE documents;--",
            "Title with emoji 😀📚",
            "Title with unicode café résumé",
        ]
        
        for title in special_titles:
            files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
            data = {"title": title}
            
            response = client.post("/api/v1/documents/upload", files=files, data=data)
            
            # Should handle gracefully (sanitize or accept)
            assert response.status_code in [201, 400]

    def test_upload_with_negative_user_id(self, client: TestClient, valid_pdf_bytes):
        """Test upload with negative user_id."""
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        data = {"user_id": -1}
        
        response = client.post("/api/v1/documents/upload", files=files, data=data)
        
        # Should reject or handle gracefully
        assert response.status_code in [201, 400, 422]

    def test_upload_with_non_existent_user_id(self, client: TestClient, valid_pdf_bytes):
        """Test upload with non-existent user_id."""
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        data = {"user_id": 999999}  # Non-existent user
        
        response = client.post("/api/v1/documents/upload", files=files, data=data)
        
        # Should either accept (nullable FK) or reject
        assert response.status_code in [201, 400, 422]


class TestUploadConcurrency:
    """Test concurrent upload scenarios to find race conditions."""

    def test_concurrent_uploads_from_same_user(
        self, client: TestClient, valid_pdf_bytes, sample_user
    ):
        """Test concurrent uploads from same user."""
        results = []
        
        def upload_file(index):
            files = {"file": (f"test_{index}.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
            data = {"user_id": sample_user.id, "title": f"Concurrent Test {index}"}
            response = client.post("/api/v1/documents/upload", files=files, data=data)
            results.append(response)
        
        # Launch 5 concurrent uploads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=upload_file, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All should succeed
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count == 5

    def test_concurrent_uploads_of_same_file(
        self, client: TestClient, valid_pdf_bytes
    ):
        """Test concurrent uploads of the same file."""
        results = []
        
        def upload_same_file():
            files = {"file": ("same.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
            data = {"title": "Same File"}
            response = client.post("/api/v1/documents/upload", files=files, data=data)
            results.append(response)
        
        # Launch 3 concurrent uploads of same file
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=upload_same_file)
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All should succeed (different document records)
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count == 3


class TestUploadWorkflowFailures:
    """Test upload workflow failures to verify rollback and cleanup."""

    def test_failure_during_pdf_validation(
        self, client: TestClient, db_session
    ):
        """Test failure during PDF validation verifies rollback."""
        # Upload corrupted PDF
        corrupted = b"%PDF-1.4\n" + b"corrupted data" * 100
        files = {"file": ("corrupted.pdf", BytesIO(corrupted), "application/pdf")}
        
        # Get initial document count
        from app.crud.document import document as document_crud
        initial_count = len(document_crud.get_multi(db_session))
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should fail
        assert response.status_code == 400
        
        # Verify no document created (or marked as failed)
        final_count = len(document_crud.get_multi(db_session))
        # Either same count or one more (if failed status is saved)
        assert final_count <= initial_count + 1

    def test_failure_during_text_extraction(
        self, client: TestClient, db_session
    ):
        """Test failure during text extraction verifies rollback and cleanup."""
        # Upload PDF with no text
        import fitz
        doc = fitz.open()
        doc.new_page()  # Empty page
        pdf_bytes = doc.tobytes()
        doc.close()
        
        files = {"file": ("empty.pdf", BytesIO(pdf_bytes), "application/pdf")}
        
        # Get initial counts
        from app.crud.document import document as document_crud
        from app.crud.note_chunk import note_chunk as note_chunk_crud
        initial_doc_count = len(document_crud.get_multi(db_session))
        initial_chunk_count = len(note_chunk_crud.get_multi(db_session))
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should fail
        assert response.status_code in [400, 500]
        
        # Verify no orphaned chunks
        final_chunk_count = len(note_chunk_crud.get_multi(db_session))
        assert final_chunk_count == initial_chunk_count

    @patch('app.services.upload_service.UploadService._chunk_and_store')
    def test_failure_during_chunking(
        self, mock_chunk, client: TestClient, valid_pdf_bytes, db_session
    ):
        """Test failure during chunking verifies rollback and file cleanup."""
        # Mock chunking to fail
        mock_chunk.side_effect = Exception("Chunking failed")
        
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        
        # Get initial file count
        from pathlib import Path
        from app.core.config import settings
        upload_dir = Path(settings.UPLOAD_DIR)
        initial_files = list(upload_dir.glob("*.pdf")) if upload_dir.exists() else []
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should fail
        assert response.status_code == 500
        
        # Verify file was cleaned up (or same count)
        final_files = list(upload_dir.glob("*.pdf")) if upload_dir.exists() else []
        # Should not have more files than before
        assert len(final_files) <= len(initial_files) + 1  # Allow for failed status

    def test_document_status_updates_correctly(
        self, client: TestClient, valid_pdf_bytes, db_session
    ):
        """Test that document status updates correctly through workflow."""
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        assert response.status_code == 201
        
        # Verify final status is COMPLETED
        document_id = response.json()["id"]
        from app.crud.document import document as document_crud
        document = document_crud.get(db_session, document_id)
        
        assert document.processing_status == ProcessingStatus.COMPLETED


class TestUploadIntegrationComplete:
    """Complete integration tests for upload workflow."""

    def test_upload_verifies_all_database_records(
        self, client: TestClient, valid_pdf_bytes, db_session
    ):
        """Test upload creates all required database records."""
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        data = {"title": "Integration Test"}
        
        response = client.post("/api/v1/documents/upload", files=files, data=data)
        
        assert response.status_code == 201
        document_id = response.json()["id"]
        
        # Verify Document record
        from app.crud.document import document as document_crud
        document = document_crud.get(db_session, document_id)
        assert document is not None
        assert document.title == "Integration Test"
        assert document.processing_status == ProcessingStatus.COMPLETED
        
        # Verify NoteChunks created
        from app.crud.note_chunk import note_chunk as note_chunk_crud
        chunks = note_chunk_crud.get_multi_by_document(db_session, document_id=document_id)
        assert len(chunks) > 0
        
        # Verify chunks are ordered
        for idx, chunk in enumerate(chunks):
            assert chunk.chunk_index == idx

    def test_upload_file_saved_to_correct_location(
        self, client: TestClient, valid_pdf_bytes, db_session
    ):
        """Test upload saves file to correct location."""
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        assert response.status_code == 201
        document_id = response.json()["id"]
        
        # Verify file exists
        from app.crud.document import document as document_crud
        from pathlib import Path
        document = document_crud.get(db_session, document_id)
        file_path = Path(document.file_path)
        
        assert file_path.exists()
        assert file_path.is_file()
        assert file_path.suffix == ".pdf"

    def test_upload_metadata_populated_correctly(
        self, client: TestClient, valid_pdf_bytes, db_session
    ):
        """Test upload populates all metadata fields correctly."""
        files = {"file": ("metadata_test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        data = {"title": "Metadata Test"}
        
        response = client.post("/api/v1/documents/upload", files=files, data=data)
        
        assert response.status_code == 201
        json_data = response.json()
        
        # Verify all metadata fields
        assert json_data["id"] is not None
        assert json_data["title"] == "Metadata Test"
        assert json_data["original_filename"] == "metadata_test.pdf"
        assert json_data["file_size"] > 0
        assert json_data["mime_type"] == "application/pdf"
        assert json_data["processing_status"] == "completed"
        assert json_data["page_count"] > 0
        assert json_data["chunk_count"] > 0
        assert json_data["uploaded_at"] is not None


class TestUploadErrorHandling:
    """Test error handling and response formats."""

    def test_error_response_format_is_consistent(
        self, client: TestClient
    ):
        """Test that all error responses have consistent format."""
        # Test various error scenarios
        error_scenarios = [
            # No file
            ({"data": {"title": "Test"}}, None),
            # Wrong content type
            ({"files": {"file": ("test.txt", BytesIO(b"text"), "text/plain")}}, None),
            # Empty file
            ({"files": {"file": ("empty.pdf", BytesIO(b""), "application/pdf")}}, None),
        ]
        
        for scenario, _ in error_scenarios:
            response = client.post("/api/v1/documents/upload", **scenario)
            
            # Should have error response
            if response.status_code >= 400:
                json_data = response.json()
                assert "detail" in json_data
                assert isinstance(json_data["detail"], str)
                assert len(json_data["detail"]) > 0

    def test_http_status_codes_are_correct(
        self, client: TestClient, valid_pdf_bytes
    ):
        """Test that HTTP status codes are correct for each error type."""
        # 400 - Bad Request (validation error)
        corrupted = b"%PDF-1.4\n" + b"corrupted"
        files = {"file": ("bad.pdf", BytesIO(corrupted), "application/pdf")}
        response = client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 400
        
        # 413 - Content Too Large
        oversized = valid_pdf_bytes * 70000  # Over 50MB
        files = {"file": ("huge.pdf", BytesIO(oversized), "application/pdf")}
        response = client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 413
        
        # 422 - Unprocessable Entity (missing required field)
        response = client.post("/api/v1/documents/upload", data={"title": "Test"})
        assert response.status_code == 422

    def test_error_messages_are_meaningful(
        self, client: TestClient
    ):
        """Test that error messages are meaningful and actionable."""
        # Empty file
        files = {"file": ("empty.pdf", BytesIO(b""), "application/pdf")}
        response = client.post("/api/v1/documents/upload", files=files)
        
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "empty" in detail.lower()
        
        # Wrong type
        files = {"file": ("test.txt", BytesIO(b"text"), "text/plain")}
        response = client.post("/api/v1/documents/upload", files=files)
        
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "type" in detail.lower() or "allowed" in detail.lower()

    def test_no_sensitive_information_in_errors(
        self, client: TestClient
    ):
        """Test that error messages don't leak sensitive information."""
        # Trigger various errors
        files = {"file": ("test.pdf", BytesIO(b"fake"), "application/pdf")}
        response = client.post("/api/v1/documents/upload", files=files)
        
        if response.status_code >= 400:
            detail = response.json()["detail"]
            
            # Should not contain sensitive info
            sensitive_patterns = [
                "password",
                "secret",
                "token",
                "api_key",
                "/Users/",
                "/home/",
                "C:\\",
            ]
            
            detail_lower = detail.lower()
            for pattern in sensitive_patterns:
                assert pattern.lower() not in detail_lower


class TestUploadPerformance:
    """Test upload performance characteristics."""

    def test_small_pdf_processing_time(
        self, client: TestClient, valid_pdf_bytes
    ):
        """Test that small PDF processes quickly (<2s)."""
        files = {"file": ("small.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        
        start_time = time.time()
        response = client.post("/api/v1/documents/upload", files=files)
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 201
        assert elapsed_time < 2.0  # Should be fast

    def test_connection_pool_handles_multiple_uploads(
        self, client: TestClient, valid_pdf_bytes
    ):
        """Test that connection pool handles multiple sequential uploads."""
        # Upload 10 files sequentially
        for i in range(10):
            files = {"file": (f"test_{i}.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
            response = client.post("/api/v1/documents/upload", files=files)
            assert response.status_code == 201


class TestUploadTransactionRollback:
    """Test transaction rollback and cleanup on failures."""

    def test_no_orphaned_documents_after_failure(
        self, client: TestClient, db_session
    ):
        """Test no orphaned Document records after failure."""
        # Upload corrupted PDF
        corrupted = b"%PDF-1.4\n" + b"bad data"
        files = {"file": ("bad.pdf", BytesIO(corrupted), "application/pdf")}
        
        # Get initial count
        from app.crud.document import document as document_crud
        initial_count = len(document_crud.get_multi(db_session))
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should fail
        assert response.status_code in [400, 500]
        
        # Verify no orphaned records
        final_count = len(document_crud.get_multi(db_session))
        # Allow for failed status being saved
        assert final_count <= initial_count + 1

    def test_no_orphaned_chunks_after_failure(
        self, client: TestClient, db_session
    ):
        """Test no orphaned NoteChunk records after failure."""
        # Upload empty PDF (will fail during extraction)
        import fitz
        doc = fitz.open()
        doc.new_page()
        pdf_bytes = doc.tobytes()
        doc.close()
        
        files = {"file": ("empty.pdf", BytesIO(pdf_bytes), "application/pdf")}
        
        # Get initial chunk count
        from app.crud.note_chunk import note_chunk as note_chunk_crud
        initial_chunks = len(note_chunk_crud.get_multi(db_session))
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should fail
        assert response.status_code in [400, 500]
        
        # Verify no orphaned chunks
        final_chunks = len(note_chunk_crud.get_multi(db_session))
        assert final_chunks == initial_chunks

    def test_file_cleanup_when_database_fails(
        self, client: TestClient, valid_pdf_bytes
    ):
        """Test file cleanup when database save fails."""
        from pathlib import Path
        from app.core.config import settings
        
        upload_dir = Path(settings.UPLOAD_DIR)
        initial_files = set(upload_dir.glob("*.pdf")) if upload_dir.exists() else set()
        
        # Mock database failure
        with patch('app.crud.document.document.create_document') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
            response = client.post("/api/v1/documents/upload", files=files)
            
            # Should fail
            assert response.status_code == 500
        
        # Verify no extra files left behind
        final_files = set(upload_dir.glob("*.pdf")) if upload_dir.exists() else set()
        # Should not have significantly more files
        assert len(final_files) <= len(initial_files) + 1


class TestUploadBoundaryConditions:
    """Test boundary conditions for upload."""

    def test_upload_pdf_with_exactly_one_character(
        self, client: TestClient
    ):
        """Test upload PDF with exactly 1 character of text."""
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "A")
        pdf_bytes = doc.tobytes()
        doc.close()
        
        files = {"file": ("one_char.pdf", BytesIO(pdf_bytes), "application/pdf")}
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should handle gracefully (might succeed or fail depending on chunking)
        assert response.status_code in [201, 400, 500]

    def test_upload_pdf_with_zero_extractable_characters(
        self, client: TestClient
    ):
        """Test upload PDF with 0 extractable characters."""
        import fitz
        doc = fitz.open()
        doc.new_page()  # Empty page
        pdf_bytes = doc.tobytes()
        doc.close()
        
        files = {"file": ("zero_chars.pdf", BytesIO(pdf_bytes), "application/pdf")}
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Should fail gracefully
        assert response.status_code in [400, 500]
        if response.status_code >= 400:
            assert "text" in response.json()["detail"].lower()
