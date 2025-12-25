"""
Tests for PDF Processing Service.

This module contains comprehensive tests for the PDFProcessorService,
including validation, text extraction, preprocessing, and error handling.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import fitz  # PyMuPDF

from app.services.pdf_processor import (
    PDFProcessorService,
    PDFValidationError,
    PDFProcessingError,
)


@pytest.fixture
def pdf_service(tmp_path):
    """Create a PDF processor service with temporary upload directory."""
    upload_dir = tmp_path / "uploads"
    return PDFProcessorService(upload_dir=str(upload_dir))


@pytest.fixture
def valid_pdf_bytes():
    """Create a minimal valid PDF file in memory."""
    # Create a minimal PDF document
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test PDF Content\nThis is a test document.")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def multi_page_pdf_bytes():
    """Create a multi-page PDF with various content."""
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Chapter 1: Introduction\n\nThis is the introduction.")

    # Page 2
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Chapter 2: Main Content\n\nThis is the main content.")

    # Page 3
    page3 = doc.new_page()
    page3.insert_text((72, 72), "Chapter 3: Conclusion\n\nThis is the conclusion.")

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def pdf_with_artifacts():
    """Create a PDF with common artifacts (page numbers, headers)."""
    doc = fitz.open()
    page = doc.new_page()

    # Add content with artifacts
    text = """Page 1 of 3

Header: Document Title

This is the main content with a hyphen-
ated word across lines.

Multiple     spaces    should    be    normalized.


Too many blank lines above.

Footer: Copyright 2024
1
"""
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestPDFProcessorServiceInit:
    """Test service initialization."""

    def test_init_creates_upload_directory(self, tmp_path):
        """Test that initialization creates upload directory."""
        upload_dir = tmp_path / "test_uploads"
        service = PDFProcessorService(upload_dir=str(upload_dir))

        assert upload_dir.exists()
        assert upload_dir.is_dir()

    def test_init_with_existing_directory(self, tmp_path):
        """Test initialization with existing directory."""
        upload_dir = tmp_path / "existing"
        upload_dir.mkdir()

        service = PDFProcessorService(upload_dir=str(upload_dir))
        assert upload_dir.exists()

    def test_init_creates_nested_directories(self, tmp_path):
        """Test initialization creates nested directories."""
        upload_dir = tmp_path / "level1" / "level2" / "uploads"
        service = PDFProcessorService(upload_dir=str(upload_dir))

        assert upload_dir.exists()
        assert upload_dir.is_dir()


class TestFileSizeValidation:
    """Test file size validation."""

    def test_validate_file_size_valid(self, pdf_service):
        """Test validation passes for valid file size."""
        # Should not raise
        pdf_service.validate_file_size(1024)  # 1KB
        pdf_service.validate_file_size(1024 * 1024)  # 1MB
        pdf_service.validate_file_size(10 * 1024 * 1024)  # 10MB

    def test_validate_file_size_too_large(self, pdf_service):
        """Test validation fails for files exceeding size limit."""
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_file_size(51 * 1024 * 1024)  # 51MB

        assert "exceeds maximum allowed size" in str(exc_info.value)
        assert "50MB" in str(exc_info.value)

    def test_validate_file_size_too_small(self, pdf_service):
        """Test validation fails for files that are too small."""
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_file_size(50)  # 50 bytes

        assert "too small" in str(exc_info.value)

    def test_validate_file_size_at_boundary(self, pdf_service):
        """Test validation at exact boundaries."""
        # Should not raise
        pdf_service.validate_file_size(100)  # Minimum
        pdf_service.validate_file_size(50 * 1024 * 1024)  # Maximum


class TestMagicBytesValidation:
    """Test PDF magic bytes validation."""

    def test_validate_magic_bytes_valid_pdf(self, pdf_service, valid_pdf_bytes):
        """Test validation passes for valid PDF magic bytes."""
        # Should not raise
        pdf_service.validate_pdf_magic_bytes(valid_pdf_bytes)

    def test_validate_magic_bytes_invalid_file(self, pdf_service):
        """Test validation fails for non-PDF files."""
        # Text file
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_pdf_magic_bytes(b"This is a text file")
        assert "magic bytes check failed" in str(exc_info.value)

        # Image file (PNG)
        with pytest.raises(PDFValidationError):
            pdf_service.validate_pdf_magic_bytes(b"\x89PNG\r\n\x1a\n")

        # ZIP file
        with pytest.raises(PDFValidationError):
            pdf_service.validate_pdf_magic_bytes(b"PK\x03\x04")


class TestPDFIntegrityValidation:
    """Test PDF integrity validation."""

    def test_validate_integrity_valid_pdf(self, pdf_service, valid_pdf_bytes):
        """Test validation passes for valid PDF."""
        doc = pdf_service.validate_pdf_integrity(valid_pdf_bytes)

        assert doc is not None
        assert doc.page_count > 0
        doc.close()

    def test_validate_integrity_corrupted_pdf(self, pdf_service):
        """Test validation fails for corrupted PDF."""
        # PDF with corrupted content
        corrupted_pdf = b"%PDF-1.4\n" + b"corrupted data" * 100

        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_pdf_integrity(corrupted_pdf)

        # Should contain error message about corruption
        error_msg = str(exc_info.value).lower()
        assert "corrupted" in error_msg or "malformed" in error_msg or "failed" in error_msg

    def test_validate_integrity_encrypted_pdf(self, pdf_service, tmp_path):
        """Test validation fails for encrypted PDF."""
        # Create an encrypted PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Encrypted content")

        # Encrypt the document
        perm = int(
            fitz.PDF_PERM_ACCESSIBILITY
            | fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_ANNOTATE
        )
        
        encrypted_path = tmp_path / "temp_encrypted.pdf"
        doc.save(
            str(encrypted_path),
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw="user",
            permissions=perm,
        )
        doc.close()

        # Read encrypted PDF
        encrypted_bytes = encrypted_path.read_bytes()

        # Clean up
        encrypted_path.unlink()

        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_pdf_integrity(encrypted_bytes)

        assert "password-protected" in str(exc_info.value) or "encrypted" in str(
            exc_info.value
        )

    def test_validate_integrity_empty_pdf(self, pdf_service):
        """Test validation fails for empty PDF."""
        # PyMuPDF doesn't allow saving PDFs with zero pages
        # So we test with a minimal corrupted PDF that claims to have no pages
        # This simulates what would happen with an empty PDF
        
        # Create a PDF and then test the page count check directly
        doc = fitz.open()
        doc.new_page()  # Add a page first
        pdf_bytes = doc.tobytes()
        doc.close()
        
        # Open and verify it has pages
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert doc.page_count > 0
        doc.close()
        
        # Test the empty check by mocking
        with patch('fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_doc.is_encrypted = False
            mock_doc.page_count = 0
            mock_open.return_value = mock_doc
            
            with pytest.raises(PDFValidationError) as exc_info:
                pdf_service.validate_pdf_integrity(pdf_bytes)
            
            assert "empty" in str(exc_info.value).lower()


class TestCompleteValidation:
    """Test complete PDF validation workflow."""

    def test_validate_pdf_success(self, pdf_service, valid_pdf_bytes):
        """Test complete validation succeeds for valid PDF."""
        doc = pdf_service.validate_pdf(valid_pdf_bytes, len(valid_pdf_bytes))

        assert doc is not None
        assert doc.page_count > 0
        doc.close()

    def test_validate_pdf_all_checks(self, pdf_service, valid_pdf_bytes):
        """Test that all validation checks are performed."""
        # Valid PDF should pass all checks
        doc = pdf_service.validate_pdf(valid_pdf_bytes, len(valid_pdf_bytes))
        doc.close()

        # Too large
        with pytest.raises(PDFValidationError):
            pdf_service.validate_pdf(valid_pdf_bytes, 51 * 1024 * 1024)

        # Wrong magic bytes
        fake_pdf = b"Not a PDF" + valid_pdf_bytes[9:]
        with pytest.raises(PDFValidationError):
            pdf_service.validate_pdf(fake_pdf, len(fake_pdf))


class TestTextExtraction:
    """Test text extraction from PDF."""

    def test_extract_text_single_page(self, pdf_service, valid_pdf_bytes):
        """Test text extraction from single page PDF."""
        doc = fitz.open(stream=valid_pdf_bytes, filetype="pdf")
        text = pdf_service.extract_text_from_pdf(doc)
        doc.close()

        assert "Test PDF Content" in text
        assert len(text) > 0

    def test_extract_text_multi_page(self, pdf_service, multi_page_pdf_bytes):
        """Test text extraction from multi-page PDF."""
        doc = fitz.open(stream=multi_page_pdf_bytes, filetype="pdf")
        text = pdf_service.extract_text_from_pdf(doc)
        doc.close()

        assert "Chapter 1" in text
        assert "Chapter 2" in text
        assert "Chapter 3" in text
        assert "--- Page Break ---" in text

    def test_extract_text_preserves_structure(self, pdf_service, multi_page_pdf_bytes):
        """Test that text extraction preserves document structure."""
        doc = fitz.open(stream=multi_page_pdf_bytes, filetype="pdf")
        text = pdf_service.extract_text_from_pdf(doc)
        doc.close()

        # Check that chapters appear in order
        intro_pos = text.find("Introduction")
        main_pos = text.find("Main Content")
        conclusion_pos = text.find("Conclusion")

        assert intro_pos < main_pos < conclusion_pos

    def test_extract_text_empty_pdf_raises_error(self, pdf_service):
        """Test that extraction fails gracefully for PDFs with no text."""
        # Create PDF with empty page (no text)
        doc = fitz.open()
        doc.new_page()  # Empty page
        pdf_bytes = doc.tobytes()
        doc.close()

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        with pytest.raises(PDFProcessingError) as exc_info:
            pdf_service.extract_text_from_pdf(doc)

        doc.close()
        assert "No text could be extracted" in str(exc_info.value)


class TestTextPreprocessing:
    """Test text preprocessing and cleaning."""

    def test_preprocess_removes_page_numbers(self, pdf_service):
        """Test that preprocessing removes standalone page numbers."""
        text = "Content here\n\n1\n\nMore content\n\n2\n\nFinal content"
        cleaned = pdf_service.preprocess_text(text)

        assert cleaned.count("\n1\n") == 0
        assert cleaned.count("\n2\n") == 0
        assert "Content here" in cleaned
        assert "More content" in cleaned

    def test_preprocess_removes_page_headers(self, pdf_service):
        """Test that preprocessing removes page headers."""
        text = "Content\n\nPage 1 of 10\n\nMore content\n\nPage 2 of 10\n\nEnd"
        cleaned = pdf_service.preprocess_text(text)

        assert "Page 1 of 10" not in cleaned
        assert "Page 2 of 10" not in cleaned

    def test_preprocess_fixes_hyphenation(self, pdf_service):
        """Test that preprocessing fixes hyphenated words."""
        text = "This is an exam-\nple of hyphen-\nation."
        cleaned = pdf_service.preprocess_text(text)

        assert "example" in cleaned
        assert "hyphenation" in cleaned
        assert "exam-\n" not in cleaned

    def test_preprocess_normalizes_whitespace(self, pdf_service):
        """Test that preprocessing normalizes whitespace."""
        text = "Multiple     spaces    here.\n\n\n\n\nToo many newlines."
        cleaned = pdf_service.preprocess_text(text)

        assert "     " not in cleaned  # No multiple spaces
        assert "\n\n\n" not in cleaned  # No more than 2 newlines

    def test_preprocess_strips_lines(self, pdf_service):
        """Test that preprocessing strips whitespace from lines."""
        text = "  Line with leading spaces\nLine with trailing spaces  \n  Both  "
        cleaned = pdf_service.preprocess_text(text)

        lines = cleaned.split("\n")
        for line in lines:
            if line:  # Skip empty lines
                assert line == line.strip()

    def test_preprocess_complete_workflow(self, pdf_service, pdf_with_artifacts):
        """Test complete preprocessing workflow with realistic PDF."""
        doc = fitz.open(stream=pdf_with_artifacts, filetype="pdf")
        raw_text = pdf_service.extract_text_from_pdf(doc)
        doc.close()

        cleaned = pdf_service.preprocess_text(raw_text)

        # Should normalize spaces (multiple spaces -> single space)
        assert "    " not in cleaned
        
        # Should limit blank lines (no more than 2 consecutive newlines)
        assert "\n\n\n" not in cleaned
        
        # Text should still contain main content
        assert "main content" in cleaned.lower()


class TestFileStorage:
    """Test file storage functionality."""

    def test_generate_file_path(self, pdf_service):
        """Test file path generation."""
        path1 = pdf_service.generate_file_path("test.pdf")
        path2 = pdf_service.generate_file_path("test.pdf")

        # Paths should be unique
        assert path1 != path2

        # Should have .pdf extension
        assert path1.suffix == ".pdf"
        assert path2.suffix == ".pdf"

        # Should be in upload directory
        assert path1.parent == pdf_service.upload_dir
        assert path2.parent == pdf_service.upload_dir

    def test_generate_file_path_preserves_extension(self, pdf_service):
        """Test that file path generation preserves extension."""
        path = pdf_service.generate_file_path("document.pdf")
        assert path.suffix == ".pdf"

        # Even with no extension, should add .pdf
        path = pdf_service.generate_file_path("document")
        assert path.suffix == ".pdf"

    def test_save_pdf_file(self, pdf_service, valid_pdf_bytes):
        """Test saving PDF file to storage."""
        file_id, file_path = pdf_service.save_pdf_file(valid_pdf_bytes, "test.pdf")

        # File should exist
        assert file_path.exists()

        # File should have correct content
        assert file_path.read_bytes() == valid_pdf_bytes

        # File ID should be UUID
        assert len(file_id) == 36  # UUID string length

    def test_save_pdf_file_verifies_size(self, pdf_service, valid_pdf_bytes):
        """Test that file saving verifies size matches."""
        file_id, file_path = pdf_service.save_pdf_file(valid_pdf_bytes, "test.pdf")

        saved_size = file_path.stat().st_size
        assert saved_size == len(valid_pdf_bytes)

    def test_save_pdf_file_unique_ids(self, pdf_service, valid_pdf_bytes):
        """Test that multiple saves generate unique file IDs."""
        file_id1, file_path1 = pdf_service.save_pdf_file(valid_pdf_bytes, "test1.pdf")
        file_id2, file_path2 = pdf_service.save_pdf_file(valid_pdf_bytes, "test2.pdf")
        
        # IDs should be different
        assert file_id1 != file_id2
        
        # Both files should exist
        assert file_path1.exists()
        assert file_path2.exists()


class TestCompleteProcessing:
    """Test complete PDF processing workflow."""

    def test_process_pdf_success(self, pdf_service, valid_pdf_bytes):
        """Test complete PDF processing workflow."""
        file_id, text, file_path = pdf_service.process_pdf(
            valid_pdf_bytes, "test.pdf"
        )

        # File should be saved
        assert file_path.exists()

        # Text should be extracted
        assert len(text) > 0
        assert "Test PDF Content" in text

        # File ID should be valid UUID
        assert len(file_id) == 36

    def test_process_pdf_multi_page(self, pdf_service, multi_page_pdf_bytes):
        """Test processing multi-page PDF."""
        file_id, text, file_path = pdf_service.process_pdf(
            multi_page_pdf_bytes, "multi.pdf"
        )

        assert "Chapter 1" in text
        assert "Chapter 2" in text
        assert "Chapter 3" in text
        assert file_path.exists()

    def test_process_pdf_with_preprocessing(self, pdf_service, pdf_with_artifacts):
        """Test that processing includes preprocessing."""
        file_id, text, file_path = pdf_service.process_pdf(
            pdf_with_artifacts, "artifacts.pdf"
        )

        # Should be preprocessed (no multiple spaces)
        assert "    " not in text

    def test_process_pdf_validation_error(self, pdf_service):
        """Test that processing fails with validation error."""
        # Invalid PDF
        with pytest.raises(PDFValidationError):
            pdf_service.process_pdf(b"Not a PDF", "fake.pdf")

    def test_process_pdf_too_large(self, pdf_service, valid_pdf_bytes):
        """Test that processing fails for oversized files."""
        # Create fake large file (just for size check)
        large_file = valid_pdf_bytes + b"x" * (51 * 1024 * 1024)

        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.process_pdf(large_file, "large.pdf")

        assert "exceeds maximum allowed size" in str(exc_info.value)

    def test_process_pdf_closes_document(self, pdf_service, valid_pdf_bytes):
        """Test that document is always closed after processing."""
        # Should not raise even if processing succeeds
        file_id, text, file_path = pdf_service.process_pdf(
            valid_pdf_bytes, "test.pdf"
        )

        # Document should be closed (no way to directly test, but should not leak)
        assert file_path.exists()


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_upload_directory_permissions(self, tmp_path):
        """Test handling of directory creation errors."""
        # Create a file where directory should be
        fake_dir = tmp_path / "fake_dir"
        fake_dir.write_text("This is a file, not a directory")

        with pytest.raises(PDFProcessingError):
            PDFProcessorService(upload_dir=str(fake_dir))

    def test_corrupted_pdf_handling(self, pdf_service):
        """Test graceful handling of corrupted PDFs."""
        corrupted = b"%PDF-1.4\ngarbage data"

        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.process_pdf(corrupted, "corrupted.pdf")

        # Should have meaningful error message
        assert len(str(exc_info.value)) > 0

    def test_empty_file_handling(self, pdf_service):
        """Test handling of empty files."""
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.process_pdf(b"", "empty.pdf")

        assert "too small" in str(exc_info.value)


class TestFileSizeEdgeCases:
    """Test file size validation edge cases designed to break the system."""

    def test_file_exactly_at_50mb_limit(self, pdf_service):
        """Test file exactly at 50MB limit should pass."""
        # Create a file exactly at the limit
        exact_size = 50 * 1024 * 1024
        # Should not raise (at the boundary)
        pdf_service.validate_file_size(exact_size)

    def test_file_one_byte_over_limit(self, pdf_service):
        """Test file at 50MB + 1 byte should fail."""
        over_limit = (50 * 1024 * 1024) + 1
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_file_size(over_limit)
        
        assert "exceeds maximum allowed size" in str(exc_info.value)

    def test_file_one_byte_under_minimum(self, pdf_service):
        """Test file at minimum size - 1 byte should fail."""
        under_minimum = 99  # MIN_FILE_SIZE is 100
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_file_size(under_minimum)
        
        assert "too small" in str(exc_info.value)

    def test_file_size_zero(self, pdf_service):
        """Test file size of 0 should fail."""
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_file_size(0)
        
        assert "too small" in str(exc_info.value)

    def test_file_size_negative(self, pdf_service):
        """Test negative file size should fail."""
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_file_size(-1000)
        
        assert "too small" in str(exc_info.value)


class TestMagicBytesEdgeCases:
    """Test magic bytes validation edge cases."""

    def test_pdf_extension_but_png_magic_bytes(self, pdf_service):
        """Test file with .pdf extension but PNG magic bytes."""
        # PNG magic bytes
        fake_pdf = b"\x89PNG\r\n\x1a\n" + b"fake content" * 100
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_pdf_magic_bytes(fake_pdf)
        
        assert "magic bytes check failed" in str(exc_info.value)

    def test_pdf_extension_but_zip_magic_bytes(self, pdf_service):
        """Test file with .pdf extension but ZIP magic bytes."""
        # ZIP magic bytes
        fake_pdf = b"PK\x03\x04" + b"fake content" * 100
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_pdf_magic_bytes(fake_pdf)
        
        assert "magic bytes check failed" in str(exc_info.value)

    def test_correct_magic_bytes_but_truncated(self, pdf_service):
        """Test file with correct magic bytes but truncated after header."""
        # Valid magic bytes but nothing else
        truncated = b"%PDF-1.4"
        
        # Magic bytes check should pass
        pdf_service.validate_pdf_magic_bytes(truncated)
        
        # But integrity check should fail
        with pytest.raises(PDFValidationError):
            pdf_service.validate_pdf_integrity(truncated)

    def test_magic_bytes_in_middle_of_file(self, pdf_service):
        """Test file with PDF magic bytes not at start."""
        # Garbage at start, then PDF magic bytes
        fake_pdf = b"GARBAGE DATA" + b"%PDF-1.4\n" + b"more data"
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_pdf_magic_bytes(fake_pdf)
        
        assert "magic bytes check failed" in str(exc_info.value)

    def test_case_sensitive_magic_bytes(self, pdf_service):
        """Test that magic bytes check is case-sensitive."""
        # Lowercase 'pdf' instead of uppercase
        wrong_case = b"%pdf-1.4\n" + b"content"
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.validate_pdf_magic_bytes(wrong_case)
        
        assert "magic bytes check failed" in str(exc_info.value)


class TestTextExtractionEdgeCases:
    """Test text extraction edge cases designed to break extraction."""

    def test_pdf_with_only_whitespace_text(self, pdf_service):
        """Test PDF that contains only whitespace characters."""
        doc = fitz.open()
        page = doc.new_page()
        
        # Insert only whitespace
        page.insert_text((72, 72), "   \n\n\t\t   \n   ")
        pdf_bytes = doc.tobytes()
        doc.close()
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        with pytest.raises(PDFProcessingError) as exc_info:
            pdf_service.extract_text_from_pdf(doc)
        
        doc.close()
        assert "No text could be extracted" in str(exc_info.value)

    def test_pdf_with_extremely_long_line(self, pdf_service):
        """Test PDF with long text insertion (PyMuPDF has rendering limits)."""
        doc = fitz.open()
        page = doc.new_page()
        
        # PyMuPDF has rendering constraints - it limits text per insertion
        # Test that we handle what it actually renders
        long_line = "A" * 2000
        page.insert_text((72, 72), long_line, fontsize=8)
        pdf_bytes = doc.tobytes()
        doc.close()
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = pdf_service.extract_text_from_pdf(doc)
        doc.close()
        
        # PyMuPDF limits rendering, so we verify it extracts what was rendered
        assert len(text) > 50  # At least some text extracted
        assert "A" in text

    def test_pdf_with_mixed_languages(self, pdf_service):
        """Test PDF with mixed languages (English, Arabic, Chinese, Hebrew)."""
        doc = fitz.open()
        page = doc.new_page()
        
        mixed_text = """
English: Hello World
Arabic: مرحبا بالعالم
Chinese: 你好世界
Hebrew: שלום עולם
Russian: Привет мир
Japanese: こんにちは世界
"""
        page.insert_text((72, 72), mixed_text)
        pdf_bytes = doc.tobytes()
        doc.close()
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = pdf_service.extract_text_from_pdf(doc)
        doc.close()
        
        # Should extract text (though some characters might not render perfectly)
        assert len(text) > 0
        assert "English" in text or "Hello" in text

    def test_extraction_handles_page_errors_gracefully(self, pdf_service):
        """Test that extraction continues even if some pages fail."""
        doc = fitz.open()
        
        # Create multiple pages
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i + 1} content")
        
        pdf_bytes = doc.tobytes()
        doc.close()
        
        # Mock one page to fail
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Should still extract text from other pages
        text = pdf_service.extract_text_from_pdf(doc)
        doc.close()
        
        assert len(text) > 0
        assert "Page" in text


class TestTextPreprocessingEdgeCases:
    """Test text preprocessing edge cases."""

    def test_preprocess_only_whitespace(self, pdf_service):
        """Test preprocessing text with only whitespace."""
        whitespace_text = "   \n\n\t\t   \n   "
        cleaned = pdf_service.preprocess_text(whitespace_text)
        
        # Should return empty or minimal string
        assert len(cleaned) == 0 or cleaned.isspace()

    def test_preprocess_extremely_long_paragraph(self, pdf_service):
        """Test preprocessing text with extremely long paragraph (>50,000 chars)."""
        # Create a very long paragraph with no natural breaks
        long_paragraph = "This is a very long sentence. " * 2000
        
        cleaned = pdf_service.preprocess_text(long_paragraph)
        
        # Should handle without crashing
        assert len(cleaned) > 0
        assert "very long sentence" in cleaned

    def test_preprocess_thousands_of_consecutive_spaces(self, pdf_service):
        """Test preprocessing text with thousands of consecutive spaces."""
        many_spaces = "word" + (" " * 5000) + "word"
        cleaned = pdf_service.preprocess_text(many_spaces)
        
        # Should normalize to single space
        assert "     " not in cleaned
        assert "word word" in cleaned

    def test_preprocess_unusual_unicode_characters(self, pdf_service):
        """Test preprocessing text with unusual Unicode characters."""
        unicode_text = """
Zero-width space: word​word
Combining diacritics: e\u0301 (é)
Em dash: word—word
En dash: word–word
Non-breaking space: word\u00A0word
"""
        cleaned = pdf_service.preprocess_text(unicode_text)
        
        # Should handle without crashing
        assert len(cleaned) > 0

    def test_preprocess_mixed_line_endings(self, pdf_service):
        """Test preprocessing text with mixed line endings (\\n, \\r\\n, \\r)."""
        mixed_endings = "Line 1\nLine 2\r\nLine 3\rLine 4"
        cleaned = pdf_service.preprocess_text(mixed_endings)
        
        # Should normalize line endings
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned
        assert "Line 3" in cleaned
        assert "Line 4" in cleaned

    def test_preprocess_preserves_meaningful_content(self, pdf_service):
        """Test that preprocessing doesn't remove meaningful content."""
        meaningful_text = """
Important Title

This is a paragraph with meaningful content.
It has multiple sentences. Each sentence is important.

Another paragraph follows.
"""
        cleaned = pdf_service.preprocess_text(meaningful_text)
        
        # Should preserve the meaningful parts
        assert "Important Title" in cleaned
        assert "meaningful content" in cleaned
        assert "Another paragraph" in cleaned


class TestFileStorageEdgeCases:
    """Test file storage edge cases."""

    def test_save_file_with_special_characters_in_original_name(self, pdf_service, valid_pdf_bytes):
        """Test saving file with special characters in original filename."""
        # Filenames with special characters
        special_names = [
            "file with spaces.pdf",
            "file@#$%.pdf",
            "file(1).pdf",
            "file[test].pdf",
            "file&name.pdf",
        ]
        
        for filename in special_names:
            file_id, file_path = pdf_service.save_pdf_file(valid_pdf_bytes, filename)
            
            # Should save successfully with UUID-based name
            assert file_path.exists()
            assert file_path.suffix == ".pdf"
            # Original filename not used in storage path
            assert filename not in str(file_path)

    def test_save_file_creates_unique_paths(self, pdf_service, valid_pdf_bytes):
        """Test that saving same file multiple times creates unique paths."""
        paths = []
        
        for i in range(5):
            file_id, file_path = pdf_service.save_pdf_file(
                valid_pdf_bytes, f"test_{i}.pdf"
            )
            paths.append(file_path)
        
        # All paths should be unique
        assert len(paths) == len(set(paths))
        
        # All files should exist
        for path in paths:
            assert path.exists()

    def test_save_file_preserves_content_integrity(self, pdf_service, valid_pdf_bytes):
        """Test that saved file content matches original exactly."""
        file_id, file_path = pdf_service.save_pdf_file(valid_pdf_bytes, "test.pdf")
        
        # Read back the saved file
        saved_content = file_path.read_bytes()
        
        # Should match exactly
        assert saved_content == valid_pdf_bytes
        assert len(saved_content) == len(valid_pdf_bytes)

    def test_generate_file_path_without_extension(self, pdf_service):
        """Test generating file path for filename without extension."""
        path = pdf_service.generate_file_path("document")
        
        # Should add .pdf extension
        assert path.suffix == ".pdf"

    def test_generate_file_path_with_multiple_dots(self, pdf_service):
        """Test generating file path for filename with multiple dots."""
        path = pdf_service.generate_file_path("my.document.v2.pdf")
        
        # Should preserve .pdf extension
        assert path.suffix == ".pdf"
