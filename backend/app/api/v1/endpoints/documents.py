"""
Document API endpoints.

This module provides API endpoints for document operations including upload.
"""

import logging
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.document import DocumentUploadResponse, DocumentUploadError
from app.services.upload_service import upload_service, UploadServiceError
from app.services.pdf_processor import PDFValidationError, PDFProcessingError
from app.services.text_chunker import TextChunkerError
from app.crud.document import document as document_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": DocumentUploadError, "description": "Validation error"},
        413: {"model": DocumentUploadError, "description": "File too large"},
        500: {"model": DocumentUploadError, "description": "Server error"},
    },
    summary="Upload a document",
    description="""
    Upload a PDF document for processing.
    
    The endpoint accepts multipart/form-data with the following fields:
    - file: PDF file (required)
    - title: Document title (optional, defaults to filename)
    - user_id: User ID (optional)
    
    The upload process includes:
    1. File validation (type, size, integrity)
    2. PDF text extraction
    3. Text chunking for semantic search
    4. Database storage with transaction management
    
    Returns document metadata including ID, status, and chunk count.
    """,
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload"),
    title: Optional[str] = Form(None, description="Document title"),
    user_id: Optional[int] = Form(None, description="User ID"),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Upload and process a PDF document.
    
    Args:
        file: Uploaded PDF file
        title: Optional document title
        user_id: Optional user ID
        db: Database session
        
    Returns:
        DocumentUploadResponse with document metadata
        
    Raises:
        HTTPException: On validation or processing errors
    """
    try:
        # Validate file is present
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided",
            )
        
        # Validate content type
        if file.content_type not in settings.ALLOWED_MIME_TYPES_LIST:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(settings.ALLOWED_MIME_TYPES_LIST)}",
            )
        
        # Read file content
        file_content = await file.read()
        
        # Validate file size
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB",
            )
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty",
            )
        
        logger.info(
            f"Processing upload: filename={file.filename}, "
            f"size={len(file_content)} bytes, "
            f"content_type={file.content_type}"
        )
        
        # Process upload
        document_id, metadata = upload_service.process_upload(
            db=db,
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type,
            title=title,
            user_id=user_id,
        )
        
        # Get document from database for response
        document = document_crud.get_or_404(db, document_id)
        
        # Build response
        response = DocumentUploadResponse(
            id=document.id,
            title=document.title,
            original_filename=document.original_filename,
            file_size=document.file_size,
            mime_type=document.mime_type,
            processing_status=document.processing_status.value,
            page_count=document.page_count,
            chunk_count=metadata["chunk_count"],
            uploaded_at=document.uploaded_at,
        )
        
        logger.info(f"Upload completed successfully: document_id={document_id}")
        return response
        
    except PDFValidationError as e:
        logger.warning(f"PDF validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PDF validation failed: {str(e)}",
        )
        
    except PDFProcessingError as e:
        logger.error(f"PDF processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF processing failed: {str(e)}",
        )
        
    except TextChunkerError as e:
        logger.error(f"Text chunking error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text chunking failed: {str(e)}",
        )
        
    except UploadServiceError as e:
        logger.error(f"Upload service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during upload",
        )
