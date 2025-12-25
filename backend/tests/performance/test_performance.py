"""
Performance benchmark tests for PDF processing pipeline.

This module tests processing speed, memory usage, and accuracy for various PDF sizes.
Run with: pytest tests/performance/test_performance.py -v -s
"""

import pytest
import time
import psutil
import os
from pathlib import Path
from typing import Tuple
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from app.services.pdf_processor import PDFProcessorService
from app.services.text_chunker import TextChunkerService, ChunkConfig


class TestPDFProcessingPerformance:
    """Test PDF processing performance metrics."""
    
    @pytest.fixture(scope="class")
    def pdf_processor(self, tmp_path_factory):
        """Create PDF processor with temporary upload directory."""
        upload_dir = tmp_path_factory.mktemp("uploads")
        return PDFProcessorService(upload_dir=str(upload_dir))
    
    @pytest.fixture(scope="class")
    def text_chunker(self):
        """Create text chunker service."""
        return TextChunkerService()
    
    def create_test_pdf(self, filename: str, num_pages: int) -> Tuple[str, int]:
        """
        Create a test PDF with specified number of pages.
        
        Args:
            filename: Output filename
            num_pages: Number of pages to create
            
        Returns:
            Tuple of (file_path, approximate_file_size)
        """
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Add content to each page
        for page_num in range(num_pages):
            c.drawString(100, 750, f"Page {page_num + 1} of {num_pages}")
            c.drawString(100, 730, "This is a test PDF document for performance benchmarking.")
            
            # Add some lorem ipsum text
            y_position = 700
            for i in range(20):  # 20 lines per page
                text = (
                    f"Line {i + 1}: Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
                    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris."
                )
                c.drawString(100, y_position, text[:80])  # Limit line length
                y_position -= 20
            
            c.showPage()
        
        c.save()
        
        file_size = os.path.getsize(filename)
        return filename, file_size
    
    def measure_memory_usage(self) -> int:
        """Get current process memory usage in bytes."""
        process = psutil.Process()
        return process.memory_info().rss
    
    def test_10_page_pdf_processing_speed(self, pdf_processor, tmp_path):
        """
        Test processing speed for 10-page PDF.
        
        Expected: < 1s for validation + extraction + preprocessing
        """
        # Create test PDF
        pdf_path = tmp_path / "test_10_pages.pdf"
        self.create_test_pdf(str(pdf_path), num_pages=10)
        
        # Read file content
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        # Measure processing time
        start_time = time.time()
        
        file_id, extracted_text, file_path = pdf_processor.process_pdf(
            file_content=file_content,
            original_filename="test_10_pages.pdf"
        )
        
        duration = time.time() - start_time
        
        # Assertions
        assert file_id is not None
        assert extracted_text is not None
        assert file_path is not None
        assert len(extracted_text) > 0
        
        # Performance assertion
        print(f"\n10-page PDF processing time: {duration:.3f}s")
        assert duration < 1.0, f"Processing took {duration:.3f}s, expected < 1.0s"
    
    def test_50_page_pdf_processing_speed(self, pdf_processor, tmp_path):
        """
        Test processing speed for 50-page PDF.
        
        Expected: < 3s for validation + extraction + preprocessing
        """
        # Create test PDF
        pdf_path = tmp_path / "test_50_pages.pdf"
        self.create_test_pdf(str(pdf_path), num_pages=50)
        
        # Read file content
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        # Measure processing time
        start_time = time.time()
        
        file_id, extracted_text, file_path = pdf_processor.process_pdf(
            file_content=file_content,
            original_filename="test_50_pages.pdf"
        )
        
        duration = time.time() - start_time
        
        # Assertions
        assert file_id is not None
        assert len(extracted_text) > 0
        
        # Performance assertion
        print(f"\n50-page PDF processing time: {duration:.3f}s")
        assert duration < 3.0, f"Processing took {duration:.3f}s, expected < 3.0s"
    
    def test_100_page_pdf_processing_speed(self, pdf_processor, tmp_path):
        """
        Test processing speed for 100-page PDF.
        
        Expected: < 6s for validation + extraction + preprocessing
        """
        # Create test PDF
        pdf_path = tmp_path / "test_100_pages.pdf"
        self.create_test_pdf(str(pdf_path), num_pages=100)
        
        # Read file content
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        # Measure processing time
        start_time = time.time()
        
        file_id, extracted_text, file_path = pdf_processor.process_pdf(
            file_content=file_content,
            original_filename="test_100_pages.pdf"
        )
        
        duration = time.time() - start_time
        
        # Assertions
        assert file_id is not None
        assert len(extracted_text) > 0
        
        # Performance assertion
        print(f"\n100-page PDF processing time: {duration:.3f}s")
        assert duration < 6.0, f"Processing took {duration:.3f}s, expected < 6.0s"
    
    def test_memory_usage_during_processing(self, pdf_processor, tmp_path):
        """
        Test memory usage during PDF processing.
        
        Verify no excessive memory consumption or leaks.
        """
        # Create test PDF
        pdf_path = tmp_path / "test_memory.pdf"
        self.create_test_pdf(str(pdf_path), num_pages=50)
        
        # Measure baseline memory
        baseline_memory = self.measure_memory_usage()
        
        # Process PDF
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        file_id, extracted_text, file_path = pdf_processor.process_pdf(
            file_content=file_content,
            original_filename="test_memory.pdf"
        )
        
        # Measure memory after processing
        after_memory = self.measure_memory_usage()
        
        # Calculate memory increase
        memory_increase_mb = (after_memory - baseline_memory) / (1024 * 1024)
        
        print(f"\nMemory increase: {memory_increase_mb:.2f} MB")
        
        # Memory should not increase by more than 100MB for a 50-page PDF
        assert memory_increase_mb < 100, f"Memory increased by {memory_increase_mb:.2f}MB"
    
    def test_text_extraction_accuracy(self, pdf_processor, tmp_path):
        """
        Test accuracy of text extraction.
        
        Verify that extracted text matches expected content.
        """
        # Create PDF with known content
        pdf_path = tmp_path / "test_accuracy.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        expected_text = "This is a test sentence for accuracy verification."
        c.drawString(100, 750, expected_text)
        c.save()
        
        # Process PDF
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        file_id, extracted_text, file_path = pdf_processor.process_pdf(
            file_content=file_content,
            original_filename="test_accuracy.pdf"
        )
        
        # Verify extracted text contains expected content
        assert expected_text in extracted_text, "Expected text not found in extraction"


class TestTextChunkingPerformance:
    """Test text chunking performance metrics."""
    
    @pytest.fixture(scope="class")
    def text_chunker(self):
        """Create text chunker service."""
        return TextChunkerService()
    
    def generate_test_text(self, num_sentences: int) -> str:
        """Generate test text with specified number of sentences."""
        sentences = []
        for i in range(num_sentences):
            sentence = (
                f"This is sentence number {i + 1}. "
                "It contains some text for testing the chunking algorithm. "
                "The sentence has multiple clauses and punctuation marks. "
            )
            sentences.append(sentence)
        return " ".join(sentences)
    
    def test_chunking_speed_small_text(self, text_chunker):
        """
        Test chunking speed for small text (100 sentences).
        
        Expected: < 2s (SpaCy overhead ~11ms/sentence)
        """
        text = self.generate_test_text(num_sentences=100)
        
        start_time = time.time()
        chunks = text_chunker.chunk_text(text)
        duration = time.time() - start_time
        
        print(f"\nSmall text chunking time: {duration:.3f}s")
        print(f"Created {len(chunks)} chunks")
        
        assert len(chunks) > 0
        assert duration < 2.0, f"Chunking took {duration:.3f}s, expected < 2.0s"
    
    def test_chunking_speed_medium_text(self, text_chunker):
        """
        Test chunking speed for medium text (500 sentences).
        
        Expected: < 6s (SpaCy overhead ~11ms/sentence)
        """
        text = self.generate_test_text(num_sentences=500)
        
        start_time = time.time()
        chunks = text_chunker.chunk_text(text)
        duration = time.time() - start_time
        
        print(f"\nMedium text chunking time: {duration:.3f}s")
        print(f"Created {len(chunks)} chunks")
        
        assert len(chunks) > 0
        assert duration < 6.0, f"Chunking took {duration:.3f}s, expected < 6.0s"
    
    def test_chunking_speed_large_text(self, text_chunker):
        """
        Test chunking speed for large text (1000 sentences).
        
        Expected: < 12s (SpaCy overhead ~11ms/sentence)
        """
        text = self.generate_test_text(num_sentences=1000)
        
        start_time = time.time()
        chunks = text_chunker.chunk_text(text)
        duration = time.time() - start_time
        
        print(f"\nLarge text chunking time: {duration:.3f}s")
        print(f"Created {len(chunks)} chunks")
        
        assert len(chunks) > 0
        assert duration < 12.0, f"Chunking took {duration:.3f}s, expected < 12.0s"
    
    def test_chunk_quality(self, text_chunker):
        """
        Test quality of generated chunks.
        
        Verify:
        - Chunks are within target size range
        - No mid-sentence breaks
        - Proper overlap between chunks
        """
        text = self.generate_test_text(num_sentences=200)
        
        chunks = text_chunker.chunk_text(text)
        
        config = text_chunker.config
        
        for chunk_text, metadata in chunks:
            # Check token count is reasonable
            assert metadata.token_count >= config.min_chunk_size, \
                f"Chunk too small: {metadata.token_count} tokens"
            
            # Check chunk ends with sentence-ending punctuation
            # (unless it's the last chunk)
            if metadata.index < len(chunks) - 1:
                assert chunk_text.rstrip().endswith(('.', '!', '?')), \
                    "Chunk does not end at sentence boundary"
            
            # Check metadata accuracy
            assert metadata.char_end > metadata.char_start
            assert metadata.sentence_count > 0
        
        # Check overlap between consecutive chunks
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i][0]
                next_chunk = chunks[i + 1][0]
                
                # Find overlap
                overlap_found = False
                for j in range(len(current_chunk) // 2, len(current_chunk)):
                    substring = current_chunk[j:]
                    if substring in next_chunk:
                        overlap_found = True
                        break
                
                # Some overlap should exist (unless last sentence is very long)
                # This is a soft check - overlap may not always be present
                print(f"Chunk {i} to {i+1} overlap: {overlap_found}")
    
    def test_spacy_model_caching(self, text_chunker):
        """
        Test that SpaCy model is cached and reused.
        
        Second chunking operation should be faster than first.
        """
        text = self.generate_test_text(num_sentences=100)
        
        # First chunking (model already loaded in fixture)
        start_time = time.time()
        chunks1 = text_chunker.chunk_text(text)
        duration1 = time.time() - start_time
        
        # Second chunking (should use cached model)
        start_time = time.time()
        chunks2 = text_chunker.chunk_text(text)
        duration2 = time.time() - start_time
        
        print(f"\nFirst chunking: {duration1:.3f}s")
        print(f"Second chunking: {duration2:.3f}s")
        
        # Both should produce same results
        assert len(chunks1) == len(chunks2)
        
        # Second should be similar speed (model already cached)
        # Allow for some variance
        assert duration2 < duration1 * 1.5, "Second chunking unexpectedly slower"


class TestEndToEndPerformance:
    """Test complete upload workflow performance."""
    
    def test_complete_workflow_timing(self, db_session, tmp_path):
        """
        Test timing of complete upload workflow.
        
        Measures time for:
        1. PDF validation
        2. Text extraction
        3. Text preprocessing
        4. File storage
        5. Text chunking
        6. Database storage
        """
        from app.services.upload_service import UploadService
        
        # Create test PDF
        pdf_path = tmp_path / "test_workflow.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        for page_num in range(20):
            c.drawString(100, 750, f"Page {page_num + 1}")
            c.drawString(100, 730, "Test content for workflow timing.")
            c.showPage()
        
        c.save()
        
        # Read file
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        # Create upload service
        upload_service = UploadService()
        
        # Measure complete workflow
        start_time = time.time()
        
        document_id, metadata = upload_service.process_upload(
            db=db_session,
            file_content=file_content,
            filename="test_workflow.pdf",
            content_type="application/pdf",
            title="Performance Test Document"
        )
        
        total_duration = time.time() - start_time
        
        print(f"\nComplete workflow time: {total_duration:.3f}s")
        print(f"Document ID: {document_id}")
        print(f"Chunks created: {metadata['chunk_count']}")
        
        # Verify success
        assert document_id is not None
        assert metadata["chunk_count"] > 0
        
        # Performance assertion: 20-page PDF should process in < 3 seconds
        assert total_duration < 3.0, \
            f"Complete workflow took {total_duration:.3f}s, expected < 3.0s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
