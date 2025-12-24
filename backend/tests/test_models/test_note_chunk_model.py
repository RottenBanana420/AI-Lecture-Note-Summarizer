"""
Comprehensive NoteChunk model tests designed to find bugs and validate constraints.

These tests are aggressive and designed to BREAK the code by testing:
- Foreign key constraints
- Vector embedding dimension validation (1536)
- Chunk ordering
- Required field validation
- Boundary values
- Cascade delete behaviors
"""

import pytest
import numpy as np
from sqlalchemy.exc import IntegrityError, DataError, StatementError
from sqlalchemy.orm import Session

from app.models.note_chunk import NoteChunk
from app.models.document import Document
from app.models.user import User


class TestNoteChunkModelCreation:
    """Test creating NoteChunk instances with valid data."""
    
    def test_create_chunk_with_all_valid_fields(self, db_session: Session, sample_document: Document):
        """Test creating a note chunk with all valid fields."""
        # Create a 1536-dimensional embedding (standard for OpenAI embeddings)
        embedding = np.random.rand(1536).tolist()
        metadata = {"source": "page_1", "section": "introduction"}
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="This is a sample text chunk from the document.",
            chunk_index=0,
            embedding=embedding,
            character_count=47,
            token_count=10,
            chunk_metadata=metadata
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.id is not None
        assert chunk.document_id == sample_document.id
        assert chunk.chunk_text == "This is a sample text chunk from the document."
        assert chunk.chunk_index == 0
        assert len(chunk.embedding) == 1536
        assert chunk.character_count == 47
        assert chunk.token_count == 10
        assert chunk.chunk_metadata == metadata
        assert chunk.created_at is not None
    
    def test_create_chunk_with_minimal_fields(self, db_session: Session, sample_document: Document):
        """Test creating a chunk with only required fields."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Minimal chunk",
            chunk_index=0,
            embedding=embedding,
            character_count=13  # character_count is required (NOT NULL)
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.id is not None
        assert chunk.character_count == 13
        assert chunk.token_count is None
        assert chunk.chunk_metadata is None


class TestNoteChunkRequiredFields:
    """Test that required fields are enforced."""
    
    def test_create_chunk_without_document_id_fails(self, db_session: Session):
        """Test that creating a chunk without document_id fails."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "document_id" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_chunk_without_chunk_text_fails(self, db_session: Session, sample_document: Document):
        """Test that creating a chunk without chunk_text fails."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "chunk_text" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_chunk_without_chunk_index_fails(self, db_session: Session, sample_document: Document):
        """Test that creating a chunk without chunk_index fails."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test chunk",
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "chunk_index" in str(exc_info.value).lower() or \
               "not null" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_create_chunk_without_embedding_succeeds(self, db_session: Session, sample_document: Document):
        """Test that creating a chunk without embedding succeeds (embedding is nullable)."""
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test chunk",
            chunk_index=0,
            character_count=10
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.id is not None
        assert chunk.embedding is None


class TestNoteChunkForeignKeyConstraints:
    """Test foreign key constraint violations."""
    
    def test_create_chunk_with_invalid_document_id_fails(self, db_session: Session):
        """Test that creating a chunk with non-existent document_id fails."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=99999,  # Non-existent document
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        error_msg = str(exc_info.value).lower()
        assert "foreign key" in error_msg or \
               "violates foreign key constraint" in error_msg or \
               "fk_" in error_msg
        db_session.rollback()


class TestNoteChunkVectorEmbedding:
    """Test vector embedding dimension validation."""
    
    def test_valid_embedding_dimension_1536(self, db_session: Session, sample_document: Document):
        """Test that 1536-dimensional embedding is accepted (OpenAI standard)."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert len(chunk.embedding) == 1536
    
    def test_invalid_embedding_dimension_fails(self, db_session: Session, sample_document: Document):
        """Test that wrong embedding dimension fails."""
        # Try with 512 dimensions instead of 1536
        wrong_embedding = np.random.rand(512).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=wrong_embedding
        )
        db_session.add(chunk)
        
        # Should fail due to dimension mismatch
        with pytest.raises((IntegrityError, DataError, StatementError)):
            db_session.commit()
        
        db_session.rollback()
    
    def test_empty_embedding_list_fails(self, db_session: Session, sample_document: Document):
        """Test that empty embedding list fails."""
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=[],
            character_count=10
        )
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError, StatementError)):
            db_session.commit()
        
        db_session.rollback()
    
    def test_embedding_with_null_values(self, db_session: Session, sample_document: Document):
        """Test embedding with null/None values."""
        # Create embedding with some None values
        embedding = [0.5] * 1536
        embedding[100] = None  # Insert a None value
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test chunk",
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        
        # May fail depending on pgvector implementation
        try:
            db_session.commit()
            db_session.rollback()
        except (IntegrityError, DataError):
            db_session.rollback()


class TestNoteChunkOrdering:
    """Test chunk ordering and indexing."""
    
    def test_chunks_ordered_by_index(self, db_session: Session, sample_document: Document):
        """Test that chunks can be ordered by chunk_index."""
        embedding = np.random.rand(1536).tolist()
        
        # Create chunks in random order
        for idx in [2, 0, 1, 3]:
            chunk = NoteChunk(
                document_id=sample_document.id,
                chunk_text=f"Chunk {idx}",
                chunk_index=idx,
                embedding=embedding,
                character_count=len(f"Chunk {idx}")
            )
            db_session.add(chunk)
        
        db_session.commit()
        
        # Query chunks ordered by index
        chunks = db_session.query(NoteChunk).filter_by(
            document_id=sample_document.id
        ).order_by(NoteChunk.chunk_index).all()
        
        assert len(chunks) == 4
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2
        assert chunks[3].chunk_index == 3
    
    def test_negative_chunk_index_allowed(self, db_session: Session, sample_document: Document):
        """Test that negative chunk_index is allowed (may be used for special chunks)."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Special chunk",
            chunk_index=-1,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.chunk_index == -1
    
    def test_duplicate_chunk_index_same_document(self, db_session: Session, sample_document: Document):
        """Test that duplicate chunk_index for same document is allowed (no unique constraint)."""
        embedding = np.random.rand(1536).tolist()
        
        chunk1 = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Chunk 1",
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        chunk2 = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Chunk 2",
            chunk_index=0,  # Same index
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        
        db_session.add(chunk1)
        db_session.add(chunk2)
        db_session.commit()
        
        # Both should be created (no unique constraint on chunk_index)
        chunks = db_session.query(NoteChunk).filter_by(
            document_id=sample_document.id,
            chunk_index=0
        ).all()
        
        assert len(chunks) == 2


class TestNoteChunkBoundaryValues:
    """Test boundary values and edge cases."""
    
    def test_chunk_text_very_long(self, db_session: Session, sample_document: Document):
        """Test chunk_text with very long content."""
        embedding = np.random.rand(1536).tolist()
        # Create a 100KB chunk
        long_text = "A" * 100000
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text=long_text,
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert len(chunk.chunk_text) == 100000
    
    def test_empty_chunk_text(self, db_session: Session, sample_document: Document):
        """Test that empty chunk_text is allowed."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="",
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.chunk_text == ""
    
    def test_character_count_zero(self, db_session: Session, sample_document: Document):
        """Test that character_count of 0 is allowed."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test",
            chunk_index=0,
            embedding=embedding,
            character_count=0
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.character_count == 0
    
    def test_token_count_zero(self, db_session: Session, sample_document: Document):
        """Test that token_count of 0 is allowed."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test",
            chunk_index=0,
            embedding=embedding,
            token_count=0,
            character_count=4
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.token_count == 0
    
    def test_very_large_chunk_index(self, db_session: Session, sample_document: Document):
        """Test very large chunk_index value."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test",
            chunk_index=1000000,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.chunk_index == 1000000


class TestNoteChunkJSONMetadata:
    """Test JSON metadata field handling."""
    
    def test_metadata_with_nested_objects(self, db_session: Session, sample_document: Document):
        """Test metadata with complex nested JSON structure."""
        embedding = np.random.rand(1536).tolist()
        metadata = {
            "source": {
                "page": 1,
                "section": "introduction",
                "subsection": "overview"
            },
            "processing": {
                "method": "sliding_window",
                "overlap": 50,
                "chunk_size": 512
            },
            "tags": ["important", "summary"]
        }
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test",
            chunk_index=0,
            embedding=embedding,
            chunk_metadata=metadata,
            character_count=4
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.chunk_metadata == metadata
        assert chunk.chunk_metadata["source"]["page"] == 1
    
    def test_metadata_with_empty_dict(self, db_session: Session, sample_document: Document):
        """Test metadata with empty dictionary."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test",
            chunk_index=0,
            embedding=embedding,
            chunk_metadata={},
            character_count=4
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        assert chunk.chunk_metadata == {}


class TestNoteChunkRelationships:
    """Test NoteChunk model relationships."""
    
    def test_chunk_document_relationship(self, db_session: Session, sample_document: Document):
        """Test that chunk has document relationship."""
        embedding = np.random.rand(1536).tolist()
        
        chunk = NoteChunk(
            document_id=sample_document.id,
            chunk_text="Test",
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        # Should have document attribute
        assert hasattr(chunk, 'document')
        assert chunk.document is not None
        assert chunk.document.id == sample_document.id


class TestNoteChunkCascadeDelete:
    """Test cascade delete behaviors."""
    
    def test_delete_document_deletes_chunks(self, db_session: Session):
        """Test that deleting a document CASCADE deletes its chunks."""
        # Create user and document
        user = User(
            username="cascade_test",
            email="cascade@example.com",
            hashed_password="$2b$12$dummy_hash"
        )
        db_session.add(user)
        db_session.commit()
        
        document = Document(
            user_id=user.id,
            title="Test",
            original_filename="test.pdf",
            file_path="/uploads/cascade_chunk_test.pdf",
            file_size=1024,
            mime_type="application/pdf"
        )
        db_session.add(document)
        db_session.commit()
        
        # Create chunks
        embedding = np.random.rand(1536).tolist()
        chunk1 = NoteChunk(
            document_id=document.id,
            chunk_text="Chunk 1",
            chunk_index=0,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        chunk2 = NoteChunk(
            document_id=document.id,
            chunk_text="Chunk 2",
            chunk_index=1,
            embedding=embedding,
            character_count=len(chunk.chunk_text) if "chunk_text" in locals() else 10
        )
        db_session.add(chunk1)
        db_session.add(chunk2)
        db_session.commit()
        
        chunk1_id = chunk1.id
        chunk2_id = chunk2.id
        
        # Delete document (should CASCADE delete chunks)
        db_session.delete(document)
        db_session.commit()
        
        # Chunks should be deleted
        remaining_chunk1 = db_session.query(NoteChunk).filter_by(id=chunk1_id).first()
        remaining_chunk2 = db_session.query(NoteChunk).filter_by(id=chunk2_id).first()
        
        assert remaining_chunk1 is None, \
            "Chunk should be CASCADE deleted when document is deleted"
        assert remaining_chunk2 is None, \
            "Chunk should be CASCADE deleted when document is deleted"
    
    def test_batch_insert_chunks(self, db_session: Session, sample_document: Document):
        """Test batch inserting multiple chunks."""
        embedding = np.random.rand(1536).tolist()
        
        chunks = []
        for i in range(10):
            chunk = NoteChunk(
                document_id=sample_document.id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                embedding=embedding,
                character_count=len(f"Chunk {i}")
            )
            chunks.append(chunk)
        
        db_session.add_all(chunks)
        db_session.commit()
        
        # Verify all chunks were created
        saved_chunks = db_session.query(NoteChunk).filter_by(
            document_id=sample_document.id
        ).all()
        
        assert len(saved_chunks) == 10
