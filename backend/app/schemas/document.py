"""
Pydantic schemas for document-related API requests and responses.

This module defines the data transfer objects (DTOs) for document operations.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DocumentUploadResponse(BaseModel):
    """
    Response schema for successful document upload.
    
    Attributes:
        id: Document ID
        title: Document title
        original_filename: Original filename
        file_size: File size in bytes
        mime_type: MIME type
        processing_status: Current processing status
        page_count: Number of pages in the PDF
        chunk_count: Number of text chunks created
        uploaded_at: Upload timestamp
    """
    id: int = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    original_filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes", ge=0)
    mime_type: str = Field(..., description="MIME type")
    processing_status: str = Field(..., description="Processing status")
    page_count: Optional[int] = Field(None, description="Number of pages", ge=0)
    chunk_count: int = Field(..., description="Number of chunks created", ge=0)
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "Machine Learning Lecture 1",
                "original_filename": "ml_lecture_01.pdf",
                "file_size": 2048576,
                "mime_type": "application/pdf",
                "processing_status": "completed",
                "page_count": 25,
                "chunk_count": 42,
                "uploaded_at": "2024-01-01T12:00:00Z"
            }
        }
    }


class DocumentUploadError(BaseModel):
    """
    Response schema for upload errors.
    
    Attributes:
        error: Error type
        message: Human-readable error message
        details: Optional additional error details
        request_id: Request ID for tracking
    """
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "ValidationError",
                "message": "File size exceeds maximum allowed size",
                "details": "Maximum allowed size is 50MB",
                "request_id": "abc-123-def"
            }
        }
    }


class DocumentMetadata(BaseModel):
    """
    Document metadata for response.
    
    Attributes:
        id: Document ID
        title: Document title
        file_size: File size in bytes
        page_count: Number of pages
        processing_status: Current status
        uploaded_at: Upload timestamp
    """
    id: int
    title: str
    file_size: int
    page_count: Optional[int] = None
    processing_status: str
    uploaded_at: datetime
    
    model_config = {
        "from_attributes": True
    }
