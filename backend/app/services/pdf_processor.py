"""
PDF Processing Service.

This module provides comprehensive PDF processing capabilities including:
- File validation (magic bytes, size limits, integrity checks)
- Text extraction with structure preservation
- Text preprocessing and cleaning
- File storage with UUID-based naming
- Robust error handling for various failure scenarios
"""

import logging
import re
import uuid
from pathlib import Path
from typing import Optional, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFValidationError(Exception):
    """Raised when PDF validation fails."""

    pass


class PDFProcessingError(Exception):
    """Raised when PDF processing fails."""

    pass


class PDFProcessorService:
    """
    Service class for processing PDF files.

    Handles the complete PDF processing workflow including validation,
    text extraction, preprocessing, and file storage.
    """

    # PDF magic bytes (PDF file signature)
    PDF_MAGIC_BYTES = b"%PDF-"

    # Maximum file size in bytes (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    # Minimum file size in bytes (100 bytes - a valid minimal PDF)
    MIN_FILE_SIZE = 100

    def __init__(self, upload_dir: str = "uploads"):
        """
        Initialize the PDF processor service.

        Args:
            upload_dir: Directory path for storing uploaded PDF files
        """
        self.upload_dir = Path(upload_dir)
        self._ensure_upload_directory()

    def _ensure_upload_directory(self) -> None:
        """
        Create upload directory if it doesn't exist.

        Raises:
            PDFProcessingError: If directory creation fails
        """
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Upload directory ensured: {self.upload_dir}")
        except Exception as e:
            logger.error(f"Failed to create upload directory: {e}")
            raise PDFProcessingError(f"Failed to create upload directory: {e}")

    def validate_file_size(self, file_size: int) -> None:
        """
        Validate file size is within acceptable limits.

        Args:
            file_size: Size of the file in bytes

        Raises:
            PDFValidationError: If file size is invalid
        """
        if file_size > self.MAX_FILE_SIZE:
            raise PDFValidationError(
                f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds maximum allowed size "
                f"({self.MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            )

        if file_size < self.MIN_FILE_SIZE:
            raise PDFValidationError(
                f"File size ({file_size} bytes) is too small to be a valid PDF"
            )

    def validate_pdf_magic_bytes(self, file_content: bytes) -> None:
        """
        Validate file is actually a PDF by checking magic bytes.

        Args:
            file_content: Raw file content bytes

        Raises:
            PDFValidationError: If file is not a valid PDF
        """
        if not file_content.startswith(self.PDF_MAGIC_BYTES):
            raise PDFValidationError(
                "File is not a valid PDF (magic bytes check failed)"
            )

    def validate_pdf_integrity(self, file_content: bytes) -> fitz.Document:
        """
        Validate PDF integrity and check for encryption.

        Args:
            file_content: Raw PDF file content

        Returns:
            Opened PyMuPDF Document object

        Raises:
            PDFValidationError: If PDF is corrupted, encrypted, or empty
        """
        try:
            # Open PDF document from bytes
            doc = fitz.open(stream=file_content, filetype="pdf")

            # Check if PDF is encrypted/password-protected
            if doc.is_encrypted:
                doc.close()
                raise PDFValidationError(
                    "PDF is password-protected or encrypted and cannot be processed"
                )

            # Check if PDF has pages
            if doc.page_count == 0:
                doc.close()
                raise PDFValidationError("PDF is empty (contains no pages)")

            # Check if we can access the first page (integrity check)
            try:
                _ = doc[0]
            except Exception as e:
                doc.close()
                raise PDFValidationError(f"PDF appears to be corrupted: {e}")

            return doc

        except fitz.FileDataError as e:
            raise PDFValidationError(f"PDF file is corrupted or malformed: {e}")
        except PDFValidationError:
            raise
        except Exception as e:
            raise PDFValidationError(f"Failed to validate PDF integrity: {e}")

    def validate_pdf(self, file_content: bytes, file_size: int) -> fitz.Document:
        """
        Perform complete PDF validation.

        Args:
            file_content: Raw PDF file content
            file_size: Size of the file in bytes

        Returns:
            Opened and validated PyMuPDF Document object

        Raises:
            PDFValidationError: If any validation check fails
        """
        logger.info(f"Validating PDF file ({file_size} bytes)")

        # Validate file size
        self.validate_file_size(file_size)

        # Validate magic bytes
        self.validate_pdf_magic_bytes(file_content)

        # Validate integrity and return opened document
        doc = self.validate_pdf_integrity(file_content)

        logger.info(
            f"PDF validation successful: {doc.page_count} pages, "
            f"{file_size / 1024:.2f}KB"
        )

        return doc

    def extract_text_from_pdf(self, doc: fitz.Document) -> str:
        """
        Extract text from PDF while preserving document structure.

        Args:
            doc: Opened PyMuPDF Document object

        Returns:
            Extracted text with preserved structure

        Raises:
            PDFProcessingError: If text extraction fails
        """
        try:
            logger.info(f"Extracting text from {doc.page_count} pages")

            extracted_text = []

            for page_num in range(doc.page_count):
                try:
                    page = doc[page_num]

                    # Extract text with reading order sorting
                    # This helps maintain proper text flow
                    text = page.get_text("text", sort=True)

                    if text.strip():
                        # Add page separator for multi-page documents
                        if page_num > 0:
                            extracted_text.append("\n\n--- Page Break ---\n\n")

                        extracted_text.append(text)

                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num + 1}: {e}"
                    )
                    # Continue with other pages even if one fails
                    continue

            full_text = "".join(extracted_text)

            if not full_text.strip():
                raise PDFProcessingError(
                    "No text could be extracted from PDF. "
                    "This might be a scanned document or image-based PDF."
                )

            logger.info(
                f"Text extraction successful: {len(full_text)} characters extracted"
            )

            return full_text

        except PDFProcessingError:
            raise
        except Exception as e:
            raise PDFProcessingError(f"Failed to extract text from PDF: {e}")

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess extracted text to remove artifacts and normalize formatting.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned and preprocessed text

        Raises:
            PDFProcessingError: If preprocessing fails
        """
        try:
            logger.info("Preprocessing extracted text")

            # Remove common page headers/footers patterns
            # (page numbers, common footer text)
            text = re.sub(r"\n\s*\d+\s*\n", "\n", text)  # Standalone page numbers
            text = re.sub(
                r"\n\s*Page \d+ of \d+\s*\n", "\n", text, flags=re.IGNORECASE
            )

            # Fix hyphenated words at line breaks
            # "exam-\nple" -> "example"
            text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

            # Normalize whitespace
            # Multiple spaces -> single space
            text = re.sub(r" +", " ", text)

            # Multiple blank lines -> maximum 2 blank lines
            text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

            # Remove leading/trailing whitespace from each line
            lines = [line.strip() for line in text.split("\n")]
            text = "\n".join(lines)

            # Remove leading/trailing whitespace from entire text
            text = text.strip()

            logger.info(
                f"Text preprocessing complete: {len(text)} characters after cleaning"
            )

            return text

        except Exception as e:
            raise PDFProcessingError(f"Failed to preprocess text: {e}")

    def generate_file_path(self, original_filename: str) -> Path:
        """
        Generate unique file path for storing PDF.

        Args:
            original_filename: Original name of the uploaded file

        Returns:
            Path object for storing the file
        """
        # Generate UUID for unique filename
        file_id = uuid.uuid4()

        # Preserve original extension (should be .pdf)
        extension = Path(original_filename).suffix or ".pdf"

        # Create filename: uuid + extension
        filename = f"{file_id}{extension}"

        # Return full path
        return self.upload_dir / filename

    def save_pdf_file(self, file_content: bytes, original_filename: str) -> Tuple[str, Path]:
        """
        Save PDF file to storage with unique identifier.

        Args:
            file_content: Raw PDF file content
            original_filename: Original name of the uploaded file

        Returns:
            Tuple of (file_id as string, file_path as Path)

        Raises:
            PDFProcessingError: If file storage fails
        """
        try:
            file_path = self.generate_file_path(original_filename)
            file_id = file_path.stem  # UUID without extension

            logger.info(f"Saving PDF file: {file_path}")

            # Write file to disk
            file_path.write_bytes(file_content)

            # Verify file was written correctly
            if not file_path.exists():
                raise PDFProcessingError("File was not saved successfully")

            saved_size = file_path.stat().st_size
            if saved_size != len(file_content):
                raise PDFProcessingError(
                    f"File size mismatch: expected {len(file_content)} bytes, "
                    f"got {saved_size} bytes"
                )

            logger.info(f"PDF file saved successfully: {file_id}")

            return file_id, file_path

        except PDFProcessingError:
            raise
        except Exception as e:
            # Clean up partial file if it exists
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass

            raise PDFProcessingError(f"Failed to save PDF file: {e}")

    def process_pdf(
        self, file_content: bytes, original_filename: str
    ) -> Tuple[str, str, Path]:
        """
        Complete PDF processing workflow.

        This is the main entry point for processing a PDF file. It performs:
        1. Validation (magic bytes, size, integrity, encryption)
        2. Text extraction with structure preservation
        3. Text preprocessing and cleaning
        4. File storage with UUID-based naming

        Args:
            file_content: Raw PDF file content
            original_filename: Original name of the uploaded file

        Returns:
            Tuple of (file_id, extracted_text, file_path)

        Raises:
            PDFValidationError: If validation fails
            PDFProcessingError: If processing or storage fails
        """
        doc = None

        try:
            logger.info(f"Starting PDF processing: {original_filename}")

            file_size = len(file_content)

            # Step 1: Validate PDF
            doc = self.validate_pdf(file_content, file_size)

            # Step 2: Extract text
            raw_text = self.extract_text_from_pdf(doc)

            # Step 3: Preprocess text
            cleaned_text = self.preprocess_text(raw_text)

            # Step 4: Save file
            file_id, file_path = self.save_pdf_file(file_content, original_filename)

            logger.info(
                f"PDF processing complete: {file_id}, "
                f"{len(cleaned_text)} characters extracted"
            )

            return file_id, cleaned_text, file_path

        finally:
            # Always close the document to free resources
            if doc is not None:
                try:
                    doc.close()
                except Exception as e:
                    logger.warning(f"Failed to close PDF document: {e}")
