"""
Tests for NoteChunk CRUD operations.

Following TDD approach - these tests are written first and should fail initially.
"""

import pytest
from sqlalchemy.orm import Session

from app.crud.note_chunk import note_chunk as chunk_crud
from app.crud.document import document as document_crud
from app.crud.user import user as user_crud
from app.crud.exceptions import RecordNotFoundError
from app.models.note_chunk import NoteChunk


class TestNoteChunkCRUD:
    """Test NoteChunk CRUD operations."""
    
    @pytest.fixture
    def test_document(self, db: Session):
        """Create a test document for chunk tests."""
        user = user_crud.create_user(
            db,
            username="chunkuser",
            email="chunkuser@example.com",
            hashed_password="password",
        )
        doc = document_crud.create_document(
            db,
            title="Chunk Test Doc",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/chunk_test.pdf",
            user_id=user.id,
        )
        db.commit()
        return doc
    
    def test_create_chunk(self, db: Session, test_document):
        """Test creating a single note chunk."""
        chunk_text = "This is a test chunk of text from the document."
        chunk_index = 0
        character_count = len(chunk_text)
        token_count = 10
        metadata = {"page": 1, "section": "introduction"}
        
        chunk = chunk_crud.create_chunk(
            db,
            document_id=test_document.id,
            chunk_text=chunk_text,
            chunk_index=chunk_index,
            character_count=character_count,
            token_count=token_count,
            chunk_metadata=metadata,
        )
        db.commit()
        
        assert chunk.id is not None
        assert chunk.document_id == test_document.id
        assert chunk.chunk_text == chunk_text
        assert chunk.chunk_index == chunk_index
        assert chunk.character_count == character_count
        assert chunk.token_count == token_count
        assert chunk.chunk_metadata == metadata
        assert chunk.embedding is None
        assert chunk.created_at is not None
    
    def test_create_batch(self, db: Session, test_document):
        """Test batch creating multiple chunks."""
        chunks_data = [
            {
                "document_id": test_document.id,
                "chunk_text": f"Chunk {i} text",
                "chunk_index": i,
                "character_count": 20,
                "token_count": 5,
            }
            for i in range(5)
        ]
        
        chunks = chunk_crud.create_batch(db, chunks_data=chunks_data)
        db.commit()
        
        assert len(chunks) == 5
        assert all(chunk.id is not None for chunk in chunks)
        assert all(chunk.document_id == test_document.id for chunk in chunks)
        assert [chunk.chunk_index for chunk in chunks] == list(range(5))
    
    def test_get_chunk_by_id(self, db: Session, test_document):
        """Test getting chunk by ID."""
        chunk = chunk_crud.create_chunk(
            db,
            document_id=test_document.id,
            chunk_text="Test chunk",
            chunk_index=0,
            character_count=10,
        )
        db.commit()
        
        retrieved_chunk = chunk_crud.get(db, chunk.id)
        
        assert retrieved_chunk is not None
        assert retrieved_chunk.id == chunk.id
        assert retrieved_chunk.chunk_text == chunk.chunk_text
    
    def test_get_chunk_not_found(self, db: Session):
        """Test getting non-existent chunk returns None."""
        chunk = chunk_crud.get(db, 99999)
        assert chunk is None
    
    def test_get_multi_by_document(self, db: Session, test_document):
        """Test getting all chunks for a document."""
        # Create multiple chunks
        for i in range(5):
            chunk_crud.create_chunk(
                db,
                document_id=test_document.id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                character_count=10,
            )
        db.commit()
        
        chunks = chunk_crud.get_multi_by_document(
            db, document_id=test_document.id
        )
        
        assert len(chunks) == 5
        assert all(chunk.document_id == test_document.id for chunk in chunks)
        # Verify chunks are ordered by index
        assert [chunk.chunk_index for chunk in chunks] == list(range(5))
    
    def test_get_multi_by_document_with_pagination(self, db: Session, test_document):
        """Test pagination when getting chunks."""
        # Create 10 chunks
        for i in range(10):
            chunk_crud.create_chunk(
                db,
                document_id=test_document.id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                character_count=10,
            )
        db.commit()
        
        # Get first 5
        chunks_page1 = chunk_crud.get_multi_by_document(
            db, document_id=test_document.id, skip=0, limit=5
        )
        assert len(chunks_page1) == 5
        assert [c.chunk_index for c in chunks_page1] == list(range(5))
        
        # Get next 5
        chunks_page2 = chunk_crud.get_multi_by_document(
            db, document_id=test_document.id, skip=5, limit=5
        )
        assert len(chunks_page2) == 5
        assert [c.chunk_index for c in chunks_page2] == list(range(5, 10))
    
    def test_get_by_index(self, db: Session, test_document):
        """Test getting chunk by document and index."""
        # Create chunks
        for i in range(3):
            chunk_crud.create_chunk(
                db,
                document_id=test_document.id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                character_count=10,
            )
        db.commit()
        
        # Get chunk at index 1
        chunk = chunk_crud.get_by_index(
            db,
            document_id=test_document.id,
            chunk_index=1,
        )
        
        assert chunk is not None
        assert chunk.chunk_index == 1
        assert chunk.chunk_text == "Chunk 1"
    
    def test_get_by_index_not_found(self, db: Session, test_document):
        """Test getting non-existent chunk index returns None."""
        chunk = chunk_crud.get_by_index(
            db,
            document_id=test_document.id,
            chunk_index=99,
        )
        assert chunk is None
    
    def test_update_embedding(self, db: Session, test_document):
        """Test updating chunk embedding."""
        chunk = chunk_crud.create_chunk(
            db,
            document_id=test_document.id,
            chunk_text="Test chunk",
            chunk_index=0,
            character_count=10,
        )
        db.commit()
        
        assert chunk.embedding is None
        
        # Update embedding
        embedding_vector = [0.1] * 1536  # 1536-dimensional vector
        updated_chunk = chunk_crud.update_embedding(
            db,
            chunk_id=chunk.id,
            embedding_vector=embedding_vector,
        )
        db.commit()
        
        assert updated_chunk.id == chunk.id
        assert updated_chunk.embedding is not None
        assert len(updated_chunk.embedding) == 1536
    
    def test_delete_chunk(self, db: Session, test_document):
        """Test deleting a chunk."""
        chunk = chunk_crud.create_chunk(
            db,
            document_id=test_document.id,
            chunk_text="Delete test",
            chunk_index=0,
            character_count=10,
        )
        db.commit()
        chunk_id = chunk.id
        
        # Delete chunk
        deleted_chunk = chunk_crud.delete(db, id=chunk_id)
        db.commit()
        
        assert deleted_chunk.id == chunk_id
        
        # Verify chunk no longer exists
        retrieved_chunk = chunk_crud.get(db, chunk_id)
        assert retrieved_chunk is None
    
    def test_delete_by_document(self, db: Session, test_document):
        """Test deleting all chunks for a document."""
        # Create multiple chunks
        for i in range(5):
            chunk_crud.create_chunk(
                db,
                document_id=test_document.id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                character_count=10,
            )
        db.commit()
        
        # Delete all chunks
        count = chunk_crud.delete_by_document(db, document_id=test_document.id)
        db.commit()
        
        assert count == 5
        
        # Verify no chunks remain
        chunks = chunk_crud.get_multi_by_document(
            db, document_id=test_document.id
        )
        assert len(chunks) == 0
    
    def test_count_by_document(self, db: Session, test_document):
        """Test counting chunks for a document."""
        # Create chunks
        for i in range(7):
            chunk_crud.create_chunk(
                db,
                document_id=test_document.id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                character_count=10,
            )
        db.commit()
        
        count = chunk_crud.count_by_document(db, document_id=test_document.id)
        assert count == 7
