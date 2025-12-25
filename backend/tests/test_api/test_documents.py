"""
Tests for document upload API endpoint.

Following TDD principles - these tests drive the API implementation.
"""

import pytest
from io import BytesIO
from fastapi.testclient import TestClient

from app.models.document import ProcessingStatus


class TestDocumentUploadEndpoint:
    """Test document upload API endpoint."""
    
    def test_upload_valid_pdf(self, client: TestClient, valid_pdf_bytes):
        """Test successful PDF upload."""
        # Arrange
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        data = {"title": "Test Document"}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files, data=data)
        
        # Assert
        assert response.status_code == 201
        
        json_data = response.json()
        assert "id" in json_data
        assert json_data["title"] == "Test Document"
        assert json_data["original_filename"] == "test.pdf"
        assert json_data["mime_type"] == "application/pdf"
        assert json_data["processing_status"] == "completed"
        assert json_data["page_count"] is not None
        assert json_data["chunk_count"] > 0
        assert "uploaded_at" in json_data
    
    def test_upload_without_title(self, client: TestClient, valid_pdf_bytes):
        """Test upload without title uses filename."""
        # Arrange
        files = {"file": ("my_lecture.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Assert
        assert response.status_code == 201
        json_data = response.json()
        assert json_data["title"] == "my_lecture"
    
    def test_upload_without_file(self, client: TestClient):
        """Test upload without file returns 400."""
        # Act
        response = client.post("/api/v1/documents/upload", data={"title": "Test"})
        
        # Assert
        assert response.status_code == 422  # FastAPI validation error
    
    def test_upload_invalid_content_type(self, client: TestClient):
        """Test upload with invalid content type returns 400."""
        # Arrange
        fake_content = b"This is not a PDF"
        files = {"file": ("test.txt", BytesIO(fake_content), "text/plain")}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Assert
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    def test_upload_oversized_file(self, client: TestClient, valid_pdf_bytes):
        """Test upload of oversized file returns 413."""
        # Arrange - Create oversized content (over 50MB)
        oversized_content = valid_pdf_bytes * 70000  # Over 50MB
        files = {"file": ("huge.pdf", BytesIO(oversized_content), "application/pdf")}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Assert
        assert response.status_code == 413
        assert "exceeds maximum" in response.json()["detail"].lower()
    
    def test_upload_empty_file(self, client: TestClient):
        """Test upload of empty file returns 400."""
        # Arrange
        files = {"file": ("empty.pdf", BytesIO(b""), "application/pdf")}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Assert
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
    
    def test_upload_corrupted_pdf(self, client: TestClient):
        """Test upload of corrupted PDF returns 400."""
        # Arrange - PDF with valid magic bytes but corrupted content
        corrupted = b"%PDF-1.4\n" + b"corrupted data" * 100
        files = {"file": ("corrupted.pdf", BytesIO(corrupted), "application/pdf")}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Assert
        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"].lower()
    
    def test_upload_creates_chunks(self, client: TestClient, valid_pdf_bytes, db_session):
        """Test that upload creates text chunks in database."""
        # Arrange
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Assert
        assert response.status_code == 201
        
        document_id = response.json()["id"]
        chunk_count = response.json()["chunk_count"]
        
        # Verify chunks in database
        from app.crud.note_chunk import note_chunk as note_chunk_crud
        chunks = note_chunk_crud.get_multi_by_document(
            db_session, document_id=document_id
        )
        assert len(chunks) == chunk_count
        assert len(chunks) > 0
    
    def test_upload_with_user_id(self, client: TestClient, valid_pdf_bytes, sample_user, db_session):
        """Test upload with user_id associates document with user."""
        # Arrange
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        data = {"user_id": sample_user.id}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files, data=data)
        
        # Assert
        assert response.status_code == 201
        
        # Verify user association in database
        from app.crud.document import document as document_crud
        document_id = response.json()["id"]
        document = document_crud.get(db_session, document_id)
        assert document.user_id == sample_user.id


class TestDocumentUploadResponseFormat:
    """Test response format and schema validation."""
    
    def test_response_schema(self, client: TestClient, valid_pdf_bytes):
        """Test that response matches expected schema."""
        # Arrange
        files = {"file": ("test.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        data = {"title": "Schema Test"}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files, data=data)
        
        # Assert
        assert response.status_code == 201
        
        json_data = response.json()
        
        # Required fields
        required_fields = [
            "id", "title", "original_filename", "file_size",
            "mime_type", "processing_status", "chunk_count", "uploaded_at"
        ]
        for field in required_fields:
            assert field in json_data, f"Missing required field: {field}"
        
        # Type validation
        assert isinstance(json_data["id"], int)
        assert isinstance(json_data["title"], str)
        assert isinstance(json_data["file_size"], int)
        assert isinstance(json_data["chunk_count"], int)
        assert json_data["file_size"] > 0
        assert json_data["chunk_count"] > 0
    
    def test_error_response_format(self, client: TestClient):
        """Test that error responses have consistent format."""
        # Arrange
        fake_content = b"not a pdf"
        files = {"file": ("fake.txt", BytesIO(fake_content), "text/plain")}
        
        # Act
        response = client.post("/api/v1/documents/upload", files=files)
        
        # Assert
        assert response.status_code == 400
        
        json_data = response.json()
        assert "detail" in json_data
        assert isinstance(json_data["detail"], str)
        assert len(json_data["detail"]) > 0


class TestDocumentUploadIntegration:
    """Integration tests for complete upload workflow."""
    
    def test_end_to_end_upload_workflow(
        self, client: TestClient, valid_pdf_bytes, db_session
    ):
        """Test complete end-to-end upload workflow."""
        # Arrange
        files = {"file": ("lecture.pdf", BytesIO(valid_pdf_bytes), "application/pdf")}
        data = {"title": "Complete Workflow Test"}
        
        # Act - Upload
        response = client.post("/api/v1/documents/upload", files=files, data=data)
        
        # Assert - Response
        assert response.status_code == 201
        document_id = response.json()["id"]
        
        # Assert - Document in database
        from app.crud.document import document as document_crud
        document = document_crud.get(db_session, document_id)
        assert document is not None
        assert document.processing_status == ProcessingStatus.COMPLETED
        
        # Assert - File on disk
        from pathlib import Path
        file_path = Path(document.file_path)
        assert file_path.exists()
        
        # Assert - Chunks in database
        from app.crud.note_chunk import note_chunk as note_chunk_crud
        chunks = note_chunk_crud.get_multi_by_document(
            db_session, document_id=document_id
        )
        assert len(chunks) > 0
        
        # Assert - Chunks are ordered
        for idx, chunk in enumerate(chunks):
            assert chunk.chunk_index == idx
