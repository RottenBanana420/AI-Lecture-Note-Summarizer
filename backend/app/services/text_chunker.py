"""
Text Chunking Service using SpaCy for intelligent sentence-boundary-aware chunking.

This module provides text chunking capabilities optimized for semantic search
and summarization tasks. It uses SpaCy for accurate sentence boundary detection
and implements configurable chunking with overlap to maintain context.

Key Features:
- Sentence-boundary-aware chunking (no mid-sentence breaks)
- Configurable chunk size and overlap
- Comprehensive metadata tracking (offsets, token counts, indices)
- Efficient SpaCy model caching
- Robust edge case handling
- Performance optimized for large documents
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import spacy
from spacy.language import Language

logger = logging.getLogger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class TextChunkerError(Exception):
    """Base exception for text chunking errors."""

    pass


# ============================================================================
# CONFIGURATION AND METADATA CLASSES
# ============================================================================


@dataclass
class ChunkConfig:
    """
    Configuration for text chunking behavior.

    Attributes:
        target_size: Target number of tokens per chunk (default: 512)
        overlap: Number of tokens to overlap between chunks (default: 50)
        min_chunk_size: Minimum acceptable chunk size in tokens (default: 100)
    """

    target_size: int = 512
    overlap: int = 50
    min_chunk_size: int = 100

    def __post_init__(self):
        """Validate configuration values."""
        if self.target_size <= 0:
            raise ValueError("target_size must be positive")

        if self.overlap < 0:
            raise ValueError("overlap cannot be negative")

        if self.overlap >= self.target_size:
            raise ValueError("overlap must be less than target_size")

        if self.min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be positive")


@dataclass
class ChunkMetadata:
    """
    Metadata for a text chunk.

    Attributes:
        index: Position of chunk in the document (0-indexed)
        char_start: Starting character offset in original text
        char_end: Ending character offset in original text
        token_count: Number of tokens in the chunk
        sentence_count: Number of sentences in the chunk
        parent_doc_id: Optional identifier for the parent document
    """

    index: int
    char_start: int
    char_end: int
    token_count: int
    sentence_count: int
    parent_doc_id: Optional[str] = None


# ============================================================================
# TEXT CHUNKER SERVICE
# ============================================================================


class TextChunkerService:
    """
    Service for intelligent text chunking using SpaCy.

    This service provides sentence-boundary-aware text chunking optimized for
    semantic search and summarization. It uses SpaCy for accurate sentence
    tokenization and implements configurable chunking with overlap.

    The service caches the SpaCy model for performance and disables unnecessary
    pipeline components to optimize processing speed.
    """

    # Class-level cache for SpaCy model (shared across instances)
    _cached_nlp: Optional[Language] = None
    _model_name: str = "en_core_web_sm"

    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        Initialize the text chunker service.

        Args:
            config: Optional chunking configuration. Uses defaults if not provided.
        """
        self.config = config or ChunkConfig()
        self.nlp = self._load_spacy_model()

    @classmethod
    def _load_spacy_model(cls) -> Language:
        """
        Load and cache SpaCy model with optimized pipeline.

        The model is loaded once and cached at the class level for reuse
        across all instances. Unnecessary pipeline components are disabled
        for performance.

        Returns:
            Loaded and configured SpaCy Language model

        Raises:
            TextChunkerError: If model loading fails
        """
        if cls._cached_nlp is not None:
            return cls._cached_nlp

        try:
            logger.info(f"Loading SpaCy model: {cls._model_name}")

            # Load model with only necessary components
            # Disable parser, NER, and other heavy components
            nlp = spacy.load(
                cls._model_name,
                disable=["parser", "ner", "lemmatizer", "textcat"],
            )

            # Ensure sentencizer is in the pipeline
            if "sentencizer" not in nlp.pipe_names:
                nlp.add_pipe("sentencizer")

            cls._cached_nlp = nlp
            logger.info("SpaCy model loaded and cached successfully")
            return nlp

        except OSError as e:
            error_msg = (
                f"Failed to load SpaCy model '{cls._model_name}'. "
                f"Please install it using: python -m spacy download {cls._model_name}"
            )
            logger.error(error_msg)
            raise TextChunkerError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error loading SpaCy model: {str(e)}"
            logger.error(error_msg)
            raise TextChunkerError(error_msg) from e

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using SpaCy tokenizer.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens in the text
        """
        if not text or not text.strip():
            return 0

        doc = self.nlp(text)
        # Count only non-whitespace tokens
        return len([token for token in doc if not token.is_space])

    def _validate_text(self, text: str) -> None:
        """
        Validate input text is not empty or whitespace-only.

        Args:
            text: Text to validate

        Raises:
            TextChunkerError: If text is empty or whitespace-only
        """
        if not text or not text.strip():
            raise TextChunkerError("Input text is empty or whitespace-only")

    def _handle_long_sentence(
        self, sentence_text: str, target_size: int
    ) -> List[str]:
        """
        Handle sentences that exceed target chunk size by splitting them.

        For very long sentences, we split them at token boundaries while
        trying to maintain semantic coherence.

        Args:
            sentence_text: The long sentence text
            target_size: Target token count for chunks

        Returns:
            List of sentence fragments
        """
        doc = self.nlp(sentence_text)
        tokens = [token.text for token in doc if not token.is_space]

        if len(tokens) <= target_size:
            return [sentence_text]

        # Split into chunks at token boundaries
        fragments = []
        current_fragment = []
        current_count = 0

        for token in tokens:
            current_fragment.append(token)
            current_count += 1

            if current_count >= target_size:
                fragments.append(" ".join(current_fragment))
                current_fragment = []
                current_count = 0

        # Add remaining tokens
        if current_fragment:
            fragments.append(" ".join(current_fragment))

        return fragments

    def _create_chunks_from_sentences(
        self, sentences: List[Tuple[str, int, int]], original_text: str
    ) -> List[Tuple[str, int, int, int, int]]:
        """
        Create chunks from sentences with overlap.

        Args:
            sentences: List of (sentence_text, char_start, char_end) tuples
            original_text: Original text for offset calculation

        Returns:
            List of (chunk_text, char_start, char_end, token_count, sentence_count) tuples
        """
        if not sentences:
            return []

        chunks = []
        current_chunk_sentences = []
        current_token_count = 0

        i = 0
        while i < len(sentences):
            sent_text, sent_start, sent_end = sentences[i]
            sent_token_count = self._count_tokens(sent_text)

            # Handle very long sentences
            if sent_token_count > self.config.target_size:
                # If we have accumulated sentences, finalize current chunk first
                if current_chunk_sentences:
                    chunks.append(self._finalize_chunk(current_chunk_sentences))
                    current_chunk_sentences = []
                    current_token_count = 0

                # Split long sentence and create chunks from fragments
                fragments = self._handle_long_sentence(
                    sent_text, self.config.target_size
                )
                for fragment in fragments:
                    fragment_tokens = self._count_tokens(fragment)
                    chunks.append(
                        (fragment, sent_start, sent_end, fragment_tokens, 1)
                    )

                i += 1
                continue

            # Check if adding this sentence would exceed target size
            if (
                current_chunk_sentences
                and current_token_count + sent_token_count > self.config.target_size
            ):
                # Finalize current chunk
                chunks.append(self._finalize_chunk(current_chunk_sentences))

                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk_sentences
                )
                current_chunk_sentences = overlap_sentences
                current_token_count = sum(
                    self._count_tokens(s[0]) for s in current_chunk_sentences
                )

            # Add sentence to current chunk
            current_chunk_sentences.append((sent_text, sent_start, sent_end))
            current_token_count += sent_token_count
            i += 1

        # Finalize last chunk
        if current_chunk_sentences:
            chunks.append(self._finalize_chunk(current_chunk_sentences))

        return chunks

    def _finalize_chunk(
        self, sentences: List[Tuple[str, int, int]]
    ) -> Tuple[str, int, int, int, int]:
        """
        Finalize a chunk from accumulated sentences.

        Args:
            sentences: List of (sentence_text, char_start, char_end) tuples

        Returns:
            Tuple of (chunk_text, char_start, char_end, token_count, sentence_count)
        """
        chunk_text = " ".join(s[0] for s in sentences)
        char_start = sentences[0][1]
        char_end = sentences[-1][2]
        token_count = self._count_tokens(chunk_text)
        sentence_count = len(sentences)

        return (chunk_text, char_start, char_end, token_count, sentence_count)

    def _get_overlap_sentences(
        self, sentences: List[Tuple[str, int, int]]
    ) -> List[Tuple[str, int, int]]:
        """
        Get sentences for overlap from the end of current chunk.

        Args:
            sentences: List of sentences in current chunk

        Returns:
            List of sentences to include in next chunk for overlap
        """
        if not sentences:
            return []

        # Work backwards to get approximately overlap tokens worth of sentences
        overlap_sentences = []
        overlap_tokens = 0

        for sent_text, sent_start, sent_end in reversed(sentences):
            sent_tokens = self._count_tokens(sent_text)
            if overlap_tokens + sent_tokens > self.config.overlap * 1.5:
                break
            overlap_sentences.insert(0, (sent_text, sent_start, sent_end))
            overlap_tokens += sent_tokens

        return overlap_sentences

    def chunk_text(
        self, text: str, parent_doc_id: Optional[str] = None
    ) -> List[Tuple[str, ChunkMetadata]]:
        """
        Chunk text into semantically coherent segments with overlap.

        This is the main entry point for text chunking. It processes the text
        using SpaCy for sentence boundary detection, groups sentences into
        chunks that approach the target token count, and adds overlap between
        chunks to maintain context.

        Args:
            text: Text to chunk
            parent_doc_id: Optional identifier for the parent document

        Returns:
            List of (chunk_text, metadata) tuples

        Raises:
            TextChunkerError: If text is empty or processing fails
        """
        try:
            # Validate input
            self._validate_text(text)

            # Process text with SpaCy
            doc = self.nlp(text)

            # Extract sentences with character offsets
            sentences = []
            for sent in doc.sents:
                sent_text = sent.text.strip()
                if sent_text:  # Skip empty sentences
                    sentences.append((sent_text, sent.start_char, sent.end_char))

            if not sentences:
                raise TextChunkerError("No sentences found in text")

            # Create chunks from sentences
            raw_chunks = self._create_chunks_from_sentences(sentences, text)

            # Build final chunks with metadata
            chunks = []
            for idx, (chunk_text, char_start, char_end, token_count, sent_count) in enumerate(raw_chunks):
                metadata = ChunkMetadata(
                    index=idx,
                    char_start=char_start,
                    char_end=char_end,
                    token_count=token_count,
                    sentence_count=sent_count,
                    parent_doc_id=parent_doc_id,
                )
                chunks.append((chunk_text, metadata))

            logger.info(
                f"Successfully chunked text into {len(chunks)} chunks "
                f"(avg {sum(m.token_count for _, m in chunks) / len(chunks):.1f} tokens/chunk)"
            )

            return chunks

        except TextChunkerError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during text chunking: {str(e)}"
            logger.error(error_msg)
            raise TextChunkerError(error_msg) from e
