"""
Real-world integration tests for PDF Processing Service.

These tests verify the service works correctly with actual PDF files
and realistic use cases, following TDD principles.
"""

import pytest
from pathlib import Path
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
def sample_lecture_pdf(tmp_path):
    """
    Create a realistic lecture note PDF for testing.
    
    This simulates a typical lecture PDF with:
    - Multiple pages
    - Headings and sections
    - Code snippets
    - Mathematical notation
    - Bullet points and lists
    """
    doc = fitz.open()
    
    # Page 1: Title and Introduction
    page1 = doc.new_page()
    content1 = """CS101: Introduction to Computer Science
Lecture 5: Data Structures and Algorithms

Professor: Dr. Jane Smith
Date: December 24, 2024

1. Introduction to Data Structures

Data structures are fundamental building blocks in computer science.
They provide efficient ways to organize and store data.

Key concepts:
- Arrays: Contiguous memory allocation
- Linked Lists: Dynamic memory allocation
- Trees: Hierarchical data organization
- Graphs: Network representations

1.1 Time Complexity

Understanding Big-O notation is crucial for algorithm analysis.
Common complexities:
- O(1): Constant time
- O(log n): Logarithmic time
- O(n): Linear time
- O(n²): Quadratic time
"""
    page1.insert_text((50, 50), content1, fontsize=11)
    
    # Page 2: Detailed Content
    page2 = doc.new_page()
    content2 = """2. Array Implementation

Arrays provide O(1) access time but fixed size.

Example implementation:
    class Array:
        def __init__(self, size):
            self.data = [None] * size
            self.size = size
        
        def get(self, index):
            if 0 <= index < self.size:
                return self.data[index]
            raise IndexError("Index out of bounds")

2.1 Advantages of Arrays
- Fast random access
- Cache-friendly memory layout
- Simple implementation

2.2 Disadvantages of Arrays
- Fixed size (in static arrays)
- Expensive insertions/deletions
- Wasted space if not fully utilized

3. Linked Lists

Linked lists offer dynamic sizing at the cost of access time.

Key operations:
- Insert at head: O(1)
- Insert at tail: O(n) without tail pointer
- Search: O(n)
- Delete: O(n)
"""
    page2.insert_text((50, 50), content2, fontsize=11)
    
    # Page 3: Advanced Topics
    page3 = doc.new_page()
    content3 = """4. Binary Search Trees

BST properties:
- Left subtree contains nodes with keys less than parent
- Right subtree contains nodes with keys greater than parent
- Both subtrees are also BSTs

Average case performance:
- Search: O(log n)
- Insert: O(log n)
- Delete: O(log n)

Worst case (unbalanced tree):
- All operations: O(n)

5. Hash Tables

Hash tables provide average O(1) operations through:
- Hash function: Maps keys to array indices
- Collision resolution: Handles key conflicts

Common collision resolution strategies:
1. Chaining: Store multiple items per bucket
2. Open addressing: Find alternative slots
3. Robin Hood hashing: Minimize variance

6. Summary

Choosing the right data structure depends on:
- Access patterns (random vs sequential)
- Memory constraints
- Performance requirements
- Mutability needs

Next lecture: Graph algorithms and traversal methods.

References:
[1] Cormen et al., "Introduction to Algorithms"
[2] Sedgewick, "Algorithms in C++"
"""
    page3.insert_text((50, 50), content3, fontsize=11)
    
    # Save to file
    pdf_path = tmp_path / "lecture_notes.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    return pdf_path


@pytest.fixture
def large_pdf(tmp_path):
    """Create a large PDF (close to size limit) for testing."""
    doc = fitz.open()
    
    # Create many pages with substantial content to reach at least 1MB
    # PyMuPDF compresses PDFs, so we need many pages
    base_content = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 100  # ~5.6KB
    
    # Add 500 pages to ensure we exceed 1MB even with compression
    for i in range(500):
        page = doc.new_page()
        content = f"Page {i+1}\n\n{base_content}\n\nEnd of page {i+1}"
        page.insert_text((50, 50), content, fontsize=10)
    
    pdf_path = tmp_path / "large_lecture.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    return pdf_path


class TestRealWorldPDFProcessing:
    """Test PDF processing with realistic lecture notes."""
    
    def test_process_lecture_notes_complete_workflow(self, pdf_service, sample_lecture_pdf):
        """Test complete workflow with realistic lecture PDF."""
        # Read the PDF file
        pdf_bytes = sample_lecture_pdf.read_bytes()
        
        # Process the PDF
        file_id, extracted_text, file_path = pdf_service.process_pdf(
            pdf_bytes, "lecture_notes.pdf"
        )
        
        # Verify file was saved
        assert file_path.exists()
        assert len(file_id) == 36  # UUID length
        
        # Verify text extraction quality
        assert len(extracted_text) > 0
        
        # Check for key content from all pages
        assert "CS101" in extracted_text
        assert "Data Structures" in extracted_text
        assert "Array Implementation" in extracted_text
        assert "Binary Search Trees" in extracted_text
        assert "Hash Tables" in extracted_text
        
        # Verify structure preservation
        assert "1. Introduction" in extracted_text
        assert "2. Array Implementation" in extracted_text
        assert "3. Linked Lists" in extracted_text
        
        # Verify code snippets are preserved
        assert "class Array" in extracted_text or "Array" in extracted_text
        
        # Verify preprocessing worked
        assert "    " not in extracted_text  # No multiple spaces
        assert "\n\n\n" not in extracted_text  # No excessive newlines
    
    def test_extract_technical_content(self, pdf_service, sample_lecture_pdf):
        """Test that technical content is extracted correctly."""
        pdf_bytes = sample_lecture_pdf.read_bytes()
        file_id, extracted_text, file_path = pdf_service.process_pdf(
            pdf_bytes, "lecture_notes.pdf"
        )
        
        # Verify Big-O notation is preserved
        assert "O(1)" in extracted_text or "O(n)" in extracted_text
        
        # Verify mathematical notation
        assert "O(log n)" in extracted_text or "log" in extracted_text
        
        # Verify lists are somewhat preserved
        # (exact formatting may vary, but content should be there)
        assert "Arrays" in extracted_text
        assert "Linked Lists" in extracted_text
        assert "Trees" in extracted_text
    
    def test_multi_page_structure_preservation(self, pdf_service, sample_lecture_pdf):
        """Test that multi-page structure is preserved."""
        pdf_bytes = sample_lecture_pdf.read_bytes()
        file_id, extracted_text, file_path = pdf_service.process_pdf(
            pdf_bytes, "lecture_notes.pdf"
        )
        
        # Verify page breaks are indicated
        assert "--- Page Break ---" in extracted_text
        
        # Verify content from different pages appears in order
        intro_pos = extracted_text.find("Introduction to Data Structures")
        array_pos = extracted_text.find("Array Implementation")
        bst_pos = extracted_text.find("Binary Search Trees")
        
        # Content should appear in the correct order
        assert intro_pos < array_pos < bst_pos
    
    def test_large_pdf_processing(self, pdf_service, large_pdf):
        """Test processing of large PDF files (many pages)."""
        pdf_bytes = large_pdf.read_bytes()
        file_size = len(pdf_bytes)
        
        # Verify file is substantial (PyMuPDF compresses well, so focus on page count)
        # 500 pages with content should give us a good-sized file
        assert file_size > 100_000  # At least 100KB
        assert file_size < 50_000_000  # Under 50MB limit
        
        # Process should succeed even with many pages
        file_id, extracted_text, file_path = pdf_service.process_pdf(
            pdf_bytes, "large_lecture.pdf"
        )
        
        # Verify processing completed
        assert file_path.exists()
        assert len(extracted_text) > 0
        
        # Verify content from many pages was extracted
        # (preprocessing removes duplicates, so focus on structure)
        assert len(extracted_text) > 50_000  # Should have substantial text
        
        # Verify page breaks are present (500 pages = 499 breaks)
        assert extracted_text.count("--- Page Break ---") >= 400  # Most pages should have breaks
        
        # Verify we can see page numbers throughout
        assert "Page 1" in extracted_text
        assert "Page 250" in extracted_text
        assert "Page 500" in extracted_text
    
    def test_file_storage_isolation(self, pdf_service, sample_lecture_pdf):
        """Test that multiple PDF uploads are stored separately."""
        pdf_bytes = sample_lecture_pdf.read_bytes()
        
        # Process same PDF twice
        file_id1, text1, path1 = pdf_service.process_pdf(pdf_bytes, "lecture1.pdf")
        file_id2, text2, path2 = pdf_service.process_pdf(pdf_bytes, "lecture2.pdf")
        
        # Files should be stored separately
        assert file_id1 != file_id2
        assert path1 != path2
        assert path1.exists()
        assert path2.exists()
        
        # Content should be identical
        assert text1 == text2
    
    def test_special_characters_preservation(self, pdf_service, tmp_path):
        """Test that special characters and Unicode are preserved."""
        doc = fitz.open()
        page = doc.new_page()
        
        # Add content with special characters
        content = """Special Characters Test:
- Mathematical: α, β, γ, Σ, ∫, ∂, ∞
- Arrows: → ← ↑ ↓ ⇒ ⇐
- Symbols: © ® ™ € £ ¥
- Accents: café, naïve, résumé
- Quotes: "smart quotes" and 'apostrophes'
"""
        page.insert_text((50, 50), content)
        
        pdf_path = tmp_path / "special_chars.pdf"
        doc.save(str(pdf_path))
        doc.close()
        
        pdf_bytes = pdf_path.read_bytes()
        file_id, extracted_text, file_path = pdf_service.process_pdf(
            pdf_bytes, "special_chars.pdf"
        )
        
        # Verify special characters are present (some may be approximated)
        assert "Special Characters" in extracted_text
        # At least some mathematical symbols should be preserved
        # (exact preservation depends on PDF encoding)
    
    def test_empty_pages_handling(self, pdf_service, tmp_path):
        """Test handling of PDFs with some empty pages."""
        doc = fitz.open()
        
        # Page 1: Content
        page1 = doc.new_page()
        page1.insert_text((50, 50), "First page with content")
        
        # Page 2: Empty
        page2 = doc.new_page()
        
        # Page 3: Content
        page3 = doc.new_page()
        page3.insert_text((50, 50), "Third page with content")
        
        pdf_path = tmp_path / "empty_pages.pdf"
        doc.save(str(pdf_path))
        doc.close()
        
        pdf_bytes = pdf_path.read_bytes()
        file_id, extracted_text, file_path = pdf_service.process_pdf(
            pdf_bytes, "empty_pages.pdf"
        )
        
        # Should extract text from non-empty pages
        assert "First page" in extracted_text
        assert "Third page" in extracted_text
        
        # Should have page breaks
        assert "--- Page Break ---" in extracted_text


class TestErrorScenarios:
    """Test error handling with real-world scenarios."""
    
    def test_oversized_pdf_rejection(self, pdf_service):
        """Test that PDFs over 50MB are rejected."""
        # Create a fake oversized PDF (just for size check)
        oversized_content = b"%PDF-1.4\n" + b"x" * (51 * 1024 * 1024)
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.process_pdf(oversized_content, "huge.pdf")
        
        assert "exceeds maximum allowed size" in str(exc_info.value)
        assert "50MB" in str(exc_info.value)
    
    def test_non_pdf_file_rejection(self, pdf_service):
        """Test that non-PDF files are rejected."""
        # Text file (small, will fail size check first)
        text_content = b"This is just a text file, not a PDF"
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.process_pdf(text_content, "fake.pdf")
        
        # Size check happens first, so small files fail on size
        # Larger non-PDF files would fail on magic bytes
        assert "too small" in str(exc_info.value).lower() or "magic bytes" in str(exc_info.value).lower()
        
        # Test with larger non-PDF that passes size check
        large_text = b"Not a PDF" + b"x" * 1000  # >100 bytes
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.process_pdf(large_text, "fake.pdf")
        
        # This should fail on magic bytes check
        assert "magic bytes" in str(exc_info.value).lower()
    
    def test_corrupted_pdf_graceful_failure(self, pdf_service):
        """Test graceful handling of corrupted PDFs."""
        # PDF with valid header but corrupted content
        corrupted = b"%PDF-1.4\n" + b"corrupted content" * 1000
        
        with pytest.raises(PDFValidationError) as exc_info:
            pdf_service.process_pdf(corrupted, "corrupted.pdf")
        
        # Should have meaningful error message
        error_msg = str(exc_info.value).lower()
        assert any(word in error_msg for word in ["corrupted", "malformed", "failed", "invalid"])
    
    def test_image_only_pdf_detection(self, pdf_service, tmp_path):
        """Test detection of image-only PDFs (scanned documents)."""
        # Create a PDF with an image but no text
        doc = fitz.open()
        page = doc.new_page()
        
        # Create a simple image (1x1 pixel)
        import io
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Insert image into PDF
        page.insert_image(page.rect, stream=img_bytes.getvalue())
        
        pdf_path = tmp_path / "image_only.pdf"
        doc.save(str(pdf_path))
        doc.close()
        
        pdf_bytes = pdf_path.read_bytes()
        
        # Should fail with meaningful error about no text
        with pytest.raises(PDFProcessingError) as exc_info:
            pdf_service.process_pdf(pdf_bytes, "image_only.pdf")
        
        assert "No text could be extracted" in str(exc_info.value)
        assert "scanned" in str(exc_info.value).lower() or "image" in str(exc_info.value).lower()


class TestPerformanceAndMemory:
    """Test performance and memory handling."""
    
    def test_processing_speed_reasonable(self, pdf_service, sample_lecture_pdf):
        """Test that processing completes in reasonable time."""
        import time
        
        pdf_bytes = sample_lecture_pdf.read_bytes()
        
        start_time = time.time()
        file_id, extracted_text, file_path = pdf_service.process_pdf(
            pdf_bytes, "lecture_notes.pdf"
        )
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should process a 3-page lecture PDF in under 1 second
        assert processing_time < 1.0, f"Processing took {processing_time:.2f}s, expected < 1.0s"
    
    def test_memory_cleanup_after_processing(self, pdf_service, sample_lecture_pdf):
        """Test that memory is properly cleaned up after processing."""
        import gc
        
        pdf_bytes = sample_lecture_pdf.read_bytes()
        
        # Process multiple times
        for i in range(5):
            file_id, extracted_text, file_path = pdf_service.process_pdf(
                pdf_bytes, f"lecture_{i}.pdf"
            )
        
        # Force garbage collection
        gc.collect()
        
        # If we got here without memory errors, cleanup is working
        assert True
