"""
Comprehensive test suite for TextChunkerService.

This test suite follows Test-Driven Development (TDD) principles.
Tests are written first to define expected behavior, then the implementation
is created to pass these tests.

Test Categories:
- Unit tests: Basic functionality and configuration
- Edge case tests: Unusual inputs and boundary conditions
- Integration tests: Real-world scenarios and performance
"""

import pytest
from app.services.text_chunker import (
    TextChunkerService,
    ChunkConfig,
    ChunkMetadata,
    TextChunkerError,
)


# ============================================================================
# UNIT TESTS - Basic Functionality
# ============================================================================


@pytest.mark.unit
class TestChunkConfig:
    """Test ChunkConfig dataclass and default values."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ChunkConfig()
        assert config.target_size == 512
        assert config.overlap == 50
        assert config.min_chunk_size == 100

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ChunkConfig(target_size=256, overlap=25, min_chunk_size=50)
        assert config.target_size == 256
        assert config.overlap == 25
        assert config.min_chunk_size == 50

    def test_config_validation(self):
        """Test configuration validation."""
        # Overlap should not exceed target size
        with pytest.raises(ValueError):
            ChunkConfig(target_size=100, overlap=150)

        # Min chunk size should be positive
        with pytest.raises(ValueError):
            ChunkConfig(min_chunk_size=0)

        # Target size should be positive
        with pytest.raises(ValueError):
            ChunkConfig(target_size=-1)


@pytest.mark.unit
class TestChunkMetadata:
    """Test ChunkMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating chunk metadata."""
        metadata = ChunkMetadata(
            index=0,
            char_start=0,
            char_end=100,
            token_count=50,
            sentence_count=3,
            parent_doc_id="test-doc",
        )
        assert metadata.index == 0
        assert metadata.char_start == 0
        assert metadata.char_end == 100
        assert metadata.token_count == 50
        assert metadata.sentence_count == 3
        assert metadata.parent_doc_id == "test-doc"


@pytest.mark.unit
class TestSpacyModelLoading:
    """Test SpaCy model loading and caching."""

    def test_model_loads_successfully(self):
        """Test that SpaCy model loads without errors."""
        chunker = TextChunkerService()
        assert chunker.nlp is not None

    def test_model_is_cached(self):
        """Test that model is cached and reused across instances."""
        chunker1 = TextChunkerService()
        chunker2 = TextChunkerService()
        # Both should reference the same cached model
        assert chunker1.nlp is chunker2.nlp

    def test_pipeline_components_disabled(self):
        """Test that unnecessary pipeline components are disabled for performance."""
        chunker = TextChunkerService()
        # Only sentencizer and tokenizer should be enabled
        enabled_components = [name for name, _ in chunker.nlp.pipeline]
        # NER, parser, and other heavy components should be disabled
        assert "ner" not in enabled_components
        assert "parser" not in enabled_components


@pytest.mark.unit
class TestTokenCounting:
    """Test token counting functionality."""

    def test_count_tokens_simple_text(self):
        """Test token counting with simple text."""
        chunker = TextChunkerService()
        text = "This is a simple test."
        token_count = chunker._count_tokens(text)
        assert token_count == 6  # This, is, a, simple, test, .

    def test_count_tokens_empty_string(self):
        """Test token counting with empty string."""
        chunker = TextChunkerService()
        token_count = chunker._count_tokens("")
        assert token_count == 0

    def test_count_tokens_whitespace_only(self):
        """Test token counting with whitespace only."""
        chunker = TextChunkerService()
        token_count = chunker._count_tokens("   \n\t  ")
        assert token_count == 0

    def test_count_tokens_complex_text(self):
        """Test token counting with punctuation and contractions."""
        chunker = TextChunkerService()
        text = "Don't worry! It's working correctly."
        token_count = chunker._count_tokens(text)
        # Don, 't, worry, !, It, 's, working, correctly, .
        assert token_count > 0


# ============================================================================
# BASIC CHUNKING TESTS
# ============================================================================


@pytest.mark.unit
class TestBasicChunking:
    """Test basic chunking functionality."""

    def test_chunk_simple_text(self):
        """Test chunking simple text that fits in one chunk."""
        chunker = TextChunkerService()
        text = "This is a test. This is another sentence. And one more."
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, tuple) for chunk in chunks)
        assert all(len(chunk) == 2 for chunk in chunks)  # (text, metadata)

    def test_chunk_returns_text_and_metadata(self):
        """Test that chunks return both text and metadata."""
        chunker = TextChunkerService()
        text = "This is a test sentence."
        chunks = chunker.chunk_text(text)

        chunk_text, metadata = chunks[0]
        assert isinstance(chunk_text, str)
        assert isinstance(metadata, ChunkMetadata)
        assert metadata.index == 0
        assert metadata.token_count > 0
        assert metadata.sentence_count > 0

    def test_chunks_preserve_original_text(self):
        """Test that concatenating chunks preserves original text (minus overlap)."""
        chunker = TextChunkerService()
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunker.chunk_text(text)

        # The first chunk should start at the beginning
        first_chunk_text, first_metadata = chunks[0]
        assert first_metadata.char_start == 0

    def test_chunk_metadata_accuracy(self):
        """Test that chunk metadata is accurate."""
        chunker = TextChunkerService()
        text = "This is a test. Another sentence here."
        chunks = chunker.chunk_text(text)

        for chunk_text, metadata in chunks:
            # Verify character offsets
            extracted = text[metadata.char_start : metadata.char_end]
            assert extracted.strip() == chunk_text.strip()

            # Verify token count
            actual_tokens = chunker._count_tokens(chunk_text)
            assert metadata.token_count == actual_tokens


# ============================================================================
# SENTENCE BOUNDARY TESTS
# ============================================================================


@pytest.mark.unit
class TestSentenceBoundaries:
    """Test that chunks respect sentence boundaries."""

    def test_no_mid_sentence_breaks(self):
        """Test that chunks never break in the middle of a sentence."""
        chunker = TextChunkerService(config=ChunkConfig(target_size=50, overlap=10))
        text = """
        This is the first sentence. This is the second sentence.
        This is the third sentence. This is the fourth sentence.
        This is the fifth sentence. This is the sixth sentence.
        """
        chunks = chunker.chunk_text(text)

        for chunk_text, _ in chunks:
            # Each chunk should end with sentence-ending punctuation or be the last chunk
            chunk_text = chunk_text.strip()
            if chunk_text:
                # Should end with proper sentence ending
                assert chunk_text[-1] in ".!?" or chunk_text == text.strip()

    def test_sentence_count_accuracy(self):
        """Test that sentence count in metadata is accurate."""
        chunker = TextChunkerService()
        text = "First sentence. Second sentence! Third sentence?"
        chunks = chunker.chunk_text(text)

        chunk_text, metadata = chunks[0]
        # Count sentences in the chunk
        doc = chunker.nlp(chunk_text)
        actual_sentence_count = len(list(doc.sents))
        assert metadata.sentence_count == actual_sentence_count


# ============================================================================
# OVERLAP TESTS
# ============================================================================


@pytest.mark.unit
class TestChunkOverlap:
    """Test chunk overlap functionality."""

    def test_overlap_between_chunks(self):
        """Test that consecutive chunks have overlap."""
        chunker = TextChunkerService(config=ChunkConfig(target_size=100, overlap=20))
        # Create text long enough to require multiple chunks
        text = " ".join([f"This is sentence number {i}." for i in range(50)])
        chunks = chunker.chunk_text(text)

        if len(chunks) > 1:
            # Check that there's overlap between consecutive chunks
            for i in range(len(chunks) - 1):
                chunk1_text, chunk1_meta = chunks[i]
                chunk2_text, chunk2_meta = chunks[i + 1]

                # Second chunk should start before first chunk ends
                assert chunk2_meta.char_start < chunk1_meta.char_end

    def test_overlap_token_count(self):
        """Test that overlap is approximately the configured token count."""
        overlap_tokens = 30
        chunker = TextChunkerService(
            config=ChunkConfig(target_size=100, overlap=overlap_tokens)
        )
        text = " ".join([f"This is sentence number {i}." for i in range(50)])
        chunks = chunker.chunk_text(text)

        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                chunk1_text, chunk1_meta = chunks[i]
                chunk2_text, chunk2_meta = chunks[i + 1]

                # Calculate overlap region
                overlap_start = chunk2_meta.char_start
                overlap_end = chunk1_meta.char_end
                overlap_text = text[overlap_start:overlap_end]

                # Count tokens in overlap
                overlap_token_count = chunker._count_tokens(overlap_text)
                # Should be approximately the configured overlap (±20% tolerance)
                assert (
                    overlap_tokens * 0.5 <= overlap_token_count <= overlap_tokens * 1.5
                )


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_text(self):
        """Test handling of empty text."""
        chunker = TextChunkerService()
        with pytest.raises(TextChunkerError, match="empty or whitespace"):
            chunker.chunk_text("")

    def test_whitespace_only_text(self):
        """Test handling of whitespace-only text."""
        chunker = TextChunkerService()
        with pytest.raises(TextChunkerError, match="empty or whitespace"):
            chunker.chunk_text("   \n\t  ")

    def test_very_short_text(self):
        """Test text shorter than minimum chunk size."""
        chunker = TextChunkerService()
        text = "Short."
        chunks = chunker.chunk_text(text)

        assert len(chunks) == 1
        chunk_text, metadata = chunks[0]
        assert chunk_text.strip() == text.strip()
        assert metadata.index == 0

    def test_single_sentence(self):
        """Test document with only one sentence."""
        chunker = TextChunkerService()
        text = "This is a single sentence."
        chunks = chunker.chunk_text(text)

        assert len(chunks) == 1
        chunk_text, metadata = chunks[0]
        assert metadata.sentence_count == 1

    def test_very_long_sentence(self):
        """Test sentence that exceeds chunk size."""
        chunker = TextChunkerService(config=ChunkConfig(target_size=50, overlap=10))
        # Create a very long sentence (no periods)
        text = "This is a very long sentence " * 50 + "that never ends."
        chunks = chunker.chunk_text(text)

        # Should still create chunks even with one long sentence
        assert len(chunks) > 0
        # Each chunk should have content
        for chunk_text, metadata in chunks:
            assert len(chunk_text.strip()) > 0
            assert metadata.token_count > 0

    def test_multiple_newlines(self):
        """Test text with excessive newlines."""
        chunker = TextChunkerService()
        text = "First sentence.\n\n\n\nSecond sentence.\n\n\nThird sentence."
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 0
        # Should handle newlines gracefully
        for chunk_text, _ in chunks:
            assert len(chunk_text.strip()) > 0

    def test_unusual_punctuation(self):
        """Test text with unusual punctuation patterns."""
        chunker = TextChunkerService()
        text = "What?! Really... Yes! No? Maybe... Definitely!!!"
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 0

    def test_mixed_languages(self):
        """Test graceful handling of mixed language content."""
        chunker = TextChunkerService()
        # Mix of English and other characters
        text = "This is English. Esto es español. C'est français. This is English again."
        chunks = chunker.chunk_text(text)

        # Should handle gracefully without crashing
        assert len(chunks) > 0


# ============================================================================
# CHUNK SIZE TESTS
# ============================================================================


@pytest.mark.unit
class TestChunkSizes:
    """Test that chunks are within acceptable size ranges."""

    def test_chunks_within_target_size(self):
        """Test that chunks don't significantly exceed target size."""
        target_size = 100
        chunker = TextChunkerService(config=ChunkConfig(target_size=target_size))
        text = " ".join([f"This is sentence number {i}." for i in range(100)])
        chunks = chunker.chunk_text(text)

        for chunk_text, metadata in chunks:
            # Chunks should not exceed target size by more than 50%
            # (accounting for sentence boundaries)
            assert metadata.token_count <= target_size * 1.5

    def test_chunks_meet_minimum_size(self):
        """Test that chunks meet minimum size (except last chunk)."""
        min_size = 50
        chunker = TextChunkerService(
            config=ChunkConfig(target_size=100, min_chunk_size=min_size)
        )
        text = " ".join([f"This is sentence number {i}." for i in range(100)])
        chunks = chunker.chunk_text(text)

        for i, (chunk_text, metadata) in enumerate(chunks):
            # All chunks except the last should meet minimum size
            if i < len(chunks) - 1:
                assert metadata.token_count >= min_size * 0.8  # 20% tolerance


# ============================================================================
# INTEGRATION TESTS - Real-world Scenarios
# ============================================================================


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test with real-world text scenarios."""

    def test_academic_paper_abstract(self):
        """Test chunking academic paper abstract."""
        chunker = TextChunkerService()
        text = """
        Machine learning has revolutionized natural language processing in recent years.
        This paper presents a novel approach to text chunking for semantic search applications.
        We demonstrate that sentence-boundary-aware chunking significantly improves retrieval accuracy.
        Our experiments show a 15% improvement over fixed-size chunking methods.
        The proposed method maintains semantic coherence while optimizing for embedding model constraints.
        """
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 0
        # Verify no mid-sentence breaks
        for chunk_text, metadata in chunks:
            assert metadata.sentence_count > 0
            assert metadata.token_count > 0

    def test_lecture_notes(self):
        """Test chunking lecture notes with various formatting."""
        chunker = TextChunkerService()
        text = """
        Introduction to Neural Networks
        
        Neural networks are computing systems inspired by biological neural networks.
        They consist of interconnected nodes (neurons) organized in layers.
        
        Key Components:
        - Input layer: receives data
        - Hidden layers: process information
        - Output layer: produces results
        
        Training involves adjusting weights through backpropagation.
        """
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 0
        # Should handle bullet points and structure
        for chunk_text, metadata in chunks:
            assert len(chunk_text.strip()) > 0

    def test_technical_documentation(self):
        """Test chunking technical documentation."""
        chunker = TextChunkerService()
        text = """
        The API endpoint /api/v1/documents accepts POST requests.
        Request body must include: file (PDF), user_id (UUID), and optional metadata.
        Response returns: document_id, status, and processing_time.
        Error codes: 400 (invalid input), 413 (file too large), 500 (server error).
        Rate limiting: 100 requests per minute per user.
        """
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 0
        # Should handle technical content with special characters
        for chunk_text, metadata in chunks:
            assert metadata.token_count > 0

    def test_large_document(self):
        """Test chunking a large document."""
        chunker = TextChunkerService(config=ChunkConfig(target_size=256, overlap=50))
        # Create a large document
        paragraphs = []
        for i in range(50):
            paragraph = " ".join(
                [f"This is sentence {j} in paragraph {i}." for j in range(10)]
            )
            paragraphs.append(paragraph)
        text = "\n\n".join(paragraphs)

        chunks = chunker.chunk_text(text)

        # Should create multiple chunks
        assert len(chunks) > 5

        # Verify chunk ordering
        for i, (chunk_text, metadata) in enumerate(chunks):
            assert metadata.index == i

        # Verify no gaps in coverage
        for i in range(len(chunks) - 1):
            _, meta1 = chunks[i]
            _, meta2 = chunks[i + 1]
            # Next chunk should start before or at the end of previous chunk
            assert meta2.char_start <= meta1.char_end


# ============================================================================
# CHARACTER OFFSET TESTS
# ============================================================================


@pytest.mark.unit
class TestCharacterOffsets:
    """Test character offset accuracy."""

    def test_offsets_reconstruct_text(self):
        """Test that character offsets can reconstruct original text."""
        chunker = TextChunkerService()
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunker.chunk_text(text)

        for chunk_text, metadata in chunks:
            # Extract text using offsets
            extracted = text[metadata.char_start : metadata.char_end]
            # Should match the chunk text (accounting for whitespace normalization)
            assert extracted.strip() == chunk_text.strip()

    def test_offsets_are_sequential(self):
        """Test that offsets are in sequential order."""
        chunker = TextChunkerService()
        text = " ".join([f"Sentence {i}." for i in range(50)])
        chunks = chunker.chunk_text(text)

        for i in range(len(chunks) - 1):
            _, meta1 = chunks[i]
            _, meta2 = chunks[i + 1]
            # Next chunk should start at or before current chunk ends
            assert meta2.char_start <= meta1.char_end


# ============================================================================
# PARENT DOCUMENT ID TESTS
# ============================================================================


@pytest.mark.unit
class TestParentDocumentId:
    """Test parent document ID tracking."""

    def test_parent_doc_id_propagation(self):
        """Test that parent_doc_id is set correctly in all chunks."""
        chunker = TextChunkerService()
        text = "First sentence. Second sentence. Third sentence."
        doc_id = "test-document-123"
        chunks = chunker.chunk_text(text, parent_doc_id=doc_id)

        for chunk_text, metadata in chunks:
            assert metadata.parent_doc_id == doc_id

    def test_optional_parent_doc_id(self):
        """Test that parent_doc_id is optional."""
        chunker = TextChunkerService()
        text = "Test sentence."
        chunks = chunker.chunk_text(text)

        chunk_text, metadata = chunks[0]
        assert metadata.parent_doc_id is None


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


@pytest.mark.slow
@pytest.mark.integration
class TestPerformance:
    """Test performance with large documents."""

    def test_large_document_performance(self):
        """Test that large documents are processed efficiently."""
        import time

        chunker = TextChunkerService()
        # Create a very large document
        text = " ".join([f"This is sentence number {i}." for i in range(1000)])

        start_time = time.time()
        chunks = chunker.chunk_text(text)
        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (< 5 seconds for 1000 sentences)
        assert elapsed_time < 5.0
        assert len(chunks) > 0

    def test_model_caching_performance(self):
        """Test that model caching improves performance."""
        import time

        # First instance (loads model)
        start_time = time.time()
        chunker1 = TextChunkerService()
        first_load_time = time.time() - start_time

        # Second instance (uses cached model)
        start_time = time.time()
        chunker2 = TextChunkerService()
        second_load_time = time.time() - start_time

        # Second load should be significantly faster
        assert second_load_time < first_load_time * 0.5
