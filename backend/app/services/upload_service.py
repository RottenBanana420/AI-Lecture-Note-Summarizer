"""
Document Upload Service.

This module orchestrates the complete document upload workflow including:
- PDF validation and processing
- Text extraction and chunking
- Database transaction management
- File storage with cleanup on failure
- Status tracking throughout the process
"""

import logging
from pathlib import Path
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.services.pdf_processor import (
    PDFProcessorService,
    PDFValidationError,
    PDFProcessingError,
)
from app.services.text_chunker import TextChunkerService, TextChunkerError
from app.crud.document import document as document_crud
from app.crud.note_chunk import note_chunk as note_chunk_crud
from app.models.document import ProcessingStatus
from app.core.config import settings

logger = logging.getLogger(__name__)


class UploadServiceError(Exception):
    """Base exception for upload service errors."""
    pass


class UploadService:
    """
    Service for orchestrating document upload workflow.
    
    This service manages the complete upload process with proper transaction
    management, error handling, and cleanup on failure.
    """
    
    def __init__(self):
        """Initialize upload service with PDF processor and text chunker."""
        self.pdf_processor = PDFProcessorService(upload_dir=settings.UPLOAD_DIR)
        self.text_chunker = TextChunkerService()
    
    def process_upload(
        self,
        db: Session,
        file_content: bytes,
        filename: str,
        content_type: str,
        title: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Tuple[int, dict]:
        """
        Process complete document upload workflow.
        
        This method orchestrates the entire upload process:
        1. Create initial document record with PENDING status
        2. Validate and process PDF
        3. Extract and chunk text
        4. Store chunks in database
        5. Update document status to COMPLETED
        
        If any step fails, the transaction is rolled back and files are cleaned up.
        
        Args:
            db: Database session
            file_content: Raw file content bytes
            filename: Original filename
            content_type: MIME type
            title: Optional document title (defaults to filename)
            user_id: Optional user ID
            
        Returns:
            Tuple of (document_id, metadata_dict)
            
        Raises:
            UploadServiceError: If upload process fails
            PDFValidationError: If PDF validation fails
            PDFProcessingError: If PDF processing fails
            TextChunkerError: If text chunking fails
        """
        document_id = None
        file_path = None
        
        try:
            logger.info(f"Starting upload process for file: {filename}")
            
            # Step 1: Create initial document record with PENDING status
            document_id = self._create_initial_document(
                db=db,
                filename=filename,
                content_type=content_type,
                file_size=len(file_content),
                title=title,
                user_id=user_id,
            )
            logger.info(f"Created document record with ID: {document_id}")
            
            # Step 2: Update status to PROCESSING
            self._update_document_status(
                db=db,
                document_id=document_id,
                status=ProcessingStatus.PROCESSING,
            )
            
            # Step 3: Process PDF (validate, extract text, save file)
            file_id, extracted_text, file_path, page_count = self._process_pdf(
                file_content=file_content,
                filename=filename,
            )
            logger.info(
                f"PDF processed successfully: {page_count} pages, "
                f"{len(extracted_text)} characters"
            )
            
            # Step 4: Update document with file path and metadata
            self._update_document_metadata(
                db=db,
                document_id=document_id,
                file_path=str(file_path),
                page_count=page_count,
            )
            
            # Step 5: Chunk text and store in database
            chunk_count = self._chunk_and_store(
                db=db,
                document_id=document_id,
                text=extracted_text,
            )
            logger.info(f"Created {chunk_count} text chunks")
            
            # Step 6: Update status to COMPLETED
            self._update_document_status(
                db=db,
                document_id=document_id,
                status=ProcessingStatus.COMPLETED,
            )
            
            # Commit all changes
            db.commit()
            
            logger.info(f"Upload completed successfully for document {document_id}")
            
            # Return document metadata
            metadata = {
                "document_id": document_id,
                "page_count": page_count,
                "chunk_count": chunk_count,
                "file_size": len(file_content),
            }
            
            return document_id, metadata
            
        except (PDFValidationError, PDFProcessingError, TextChunkerError) as e:
            # These are expected errors from processing
            logger.error(f"Processing error during upload: {str(e)}")
            self._cleanup_on_failure(
                db=db,
                document_id=document_id,
                file_path=file_path,
                error_message=str(e),
            )
            raise
            
        except SQLAlchemyError as e:
            # Database errors
            logger.error(f"Database error during upload: {str(e)}", exc_info=True)
            self._cleanup_on_failure(
                db=db,
                document_id=document_id,
                file_path=file_path,
                error_message=f"Database error: {str(e)}",
            )
            raise UploadServiceError(f"Database error: {str(e)}") from e
            
        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error during upload: {str(e)}", exc_info=True)
            self._cleanup_on_failure(
                db=db,
                document_id=document_id,
                file_path=file_path,
                error_message=f"Unexpected error: {str(e)}",
            )
            raise UploadServiceError(f"Upload failed: {str(e)}") from e
    
    def _create_initial_document(
        self,
        db: Session,
        filename: str,
        content_type: str,
        file_size: int,
        title: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> int:
        """
        Create initial document record with PENDING status.
        
        Args:
            db: Database session
            filename: Original filename
            content_type: MIME type
            file_size: File size in bytes
            title: Optional document title
            user_id: Optional user ID
            
        Returns:
            Document ID
        """
        # Use filename as title if not provided
        if not title:
            title = Path(filename).stem
        
        # Create document with temporary file path (will be updated after processing)
        document = document_crud.create_document(
            db=db,
            title=title,
            original_filename=filename,
            file_size=file_size,
            mime_type=content_type,
            file_path="pending",  # Temporary, will be updated
            user_id=user_id,
            processing_status=ProcessingStatus.PENDING,
        )
        
        db.flush()  # Flush to get the ID without committing
        return document.id
    
    def _process_pdf(
        self,
        file_content: bytes,
        filename: str,
    ) -> Tuple[str, str, Path, int]:
        """
        Process PDF file: validate, extract text, save to storage.
        
        Args:
            file_content: Raw PDF content
            filename: Original filename
            
        Returns:
            Tuple of (file_id, extracted_text, file_path, page_count)
            
        Raises:
            PDFValidationError: If PDF validation fails
            PDFProcessingError: If PDF processing fails
        """
        # Process PDF (validates, extracts text, saves file)
        file_id, extracted_text, file_path = self.pdf_processor.process_pdf(
            file_content=file_content,
            original_filename=filename,
        )
        
        # Get page count from PDF
        import fitz
        doc = fitz.open(stream=file_content, filetype="pdf")
        page_count = doc.page_count
        doc.close()
        
        return file_id, extracted_text, file_path, page_count
    
    def _chunk_and_store(
        self,
        db: Session,
        document_id: int,
        text: str,
    ) -> int:
        """
        Chunk text and store chunks in database.
        
        Args:
            db: Database session
            document_id: Document ID
            text: Extracted text to chunk
            
        Returns:
            Number of chunks created
            
        Raises:
            TextChunkerError: If chunking fails
        """
        # Chunk the text
        chunks = self.text_chunker.chunk_text(
            text=text,
            parent_doc_id=str(document_id),
        )
        
        # Prepare chunk data for batch insert
        chunks_data = []
        for chunk_text, metadata in chunks:
            chunk_data = {
                "document_id": document_id,
                "chunk_text": chunk_text,
                "chunk_index": metadata.index,
                "character_count": len(chunk_text),
                "token_count": metadata.token_count,
                "chunk_metadata": {
                    "char_start": metadata.char_start,
                    "char_end": metadata.char_end,
                    "sentence_count": metadata.sentence_count,
                },
                "embedding": None,  # Will be generated later
            }
            chunks_data.append(chunk_data)
        
        # Batch insert chunks
        note_chunk_crud.create_batch(db=db, chunks_data=chunks_data)
        
        return len(chunks_data)
    
    def _update_document_status(
        self,
        db: Session,
        document_id: int,
        status: ProcessingStatus,
    ) -> None:
        """
        Update document processing status.
        
        Args:
            db: Database session
            document_id: Document ID
            status: New processing status
        """
        document_crud.update_status(
            db=db,
            document_id=document_id,
            status=status,
        )
        db.flush()
    
    def _update_document_metadata(
        self,
        db: Session,
        document_id: int,
        file_path: str,
        page_count: int,
    ) -> None:
        """
        Update document with file path and metadata.
        
        Args:
            db: Database session
            document_id: Document ID
            file_path: Path to stored file
            page_count: Number of pages
        """
        document_crud.update_document(
            db=db,
            document_id=document_id,
            update_data={
                "file_path": file_path,
                "page_count": page_count,
            },
        )
        db.flush()
    
    def _cleanup_on_failure(
        self,
        db: Session,
        document_id: Optional[int],
        file_path: Optional[Path],
        error_message: str,
    ) -> None:
        """
        Clean up resources on upload failure.
        
        This method:
        1. Updates document status to FAILED with error message
        2. Rolls back database transaction
        3. Deletes uploaded file if it exists
        
        Args:
            db: Database session
            document_id: Document ID (if created)
            file_path: Path to uploaded file (if saved)
            error_message: Error message to store
        """
        try:
            # Update document status to FAILED if document was created
            if document_id:
                try:
                    document_crud.update_document(
                        db=db,
                        document_id=document_id,
                        update_data={
                            "processing_status": ProcessingStatus.FAILED,
                            "error_message": error_message,
                        },
                    )
                    db.commit()  # Commit the failure status
                except Exception as e:
                    logger.error(f"Failed to update document status: {e}")
                    db.rollback()
            else:
                # No document created, just rollback
                db.rollback()
            
            # Delete uploaded file if it exists
            if file_path and Path(file_path).exists():
                try:
                    Path(file_path).unlink()
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete file {file_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            # Ensure rollback even if cleanup fails
            try:
                db.rollback()
            except Exception:
                pass


# Create singleton instance
upload_service = UploadService()
