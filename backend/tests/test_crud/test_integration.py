"""
Integration tests for CRUD operations.

These tests verify complex scenarios like cascade deletes and transaction management.
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.crud.user import user as user_crud
from app.crud.document import document as document_crud
from app.crud.summary import summary as summary_crud
from app.crud.note_chunk import note_chunk as chunk_crud
from app.models.document import ProcessingStatus
from app.models.summary import SummaryType


class TestCascadeDelete:
    """Test cascade delete behaviors."""
    
    def test_delete_document_cascades_to_summaries_and_chunks(self, db: Session):
        """Test that deleting a document also deletes its summaries and chunks."""
        # Create user
        user = user_crud.create_user(
            db,
            username="cascadeuser",
            email="cascade@example.com",
            hashed_password="password",
        )
        
        # Create document
        doc = document_crud.create_document(
            db,
            title="Cascade Test Doc",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/cascade.pdf",
            user_id=user.id,
        )
        
        # Create summaries
        summary1 = summary_crud.create_summary(
            db,
            document_id=doc.id,
            summary_text="Extractive summary",
            summary_type=SummaryType.EXTRACTIVE,
        )
        summary2 = summary_crud.create_summary(
            db,
            document_id=doc.id,
            summary_text="Abstractive summary",
            summary_type=SummaryType.ABSTRACTIVE,
        )
        
        # Create chunks
        for i in range(5):
            chunk_crud.create_chunk(
                db,
                document_id=doc.id,
                chunk_text=f"Chunk {i}",
                chunk_index=i,
                character_count=10,
            )
        
        db.commit()
        
        # Verify everything exists
        assert document_crud.get(db, doc.id) is not None
        assert summary_crud.get(db, summary1.id) is not None
        assert summary_crud.get(db, summary2.id) is not None
        assert chunk_crud.count_by_document(db, document_id=doc.id) == 5
        
        # Delete document
        document_crud.delete(db, id=doc.id)
        db.commit()
        
        # Verify document is deleted
        assert document_crud.get(db, doc.id) is None
        
        # Verify summaries are cascade deleted
        assert summary_crud.get(db, summary1.id) is None
        assert summary_crud.get(db, summary2.id) is None
        
        # Verify chunks are cascade deleted
        assert chunk_crud.count_by_document(db, document_id=doc.id) == 0


class TestTransactionManagement:
    """Test transaction management and rollback behavior."""
    
    def test_transaction_rollback_on_error(self, db: Session):
        """Test that transactions rollback properly on errors."""
        # Create user
        user = user_crud.create_user(
            db,
            username="txuser",
            email="tx@example.com",
            hashed_password="password",
        )
        db.commit()
        
        initial_user_count = user_crud.count(db)
        
        # Start a transaction that will fail
        try:
            # Create a document
            doc = document_crud.create_document(
                db,
                title="TX Test",
                original_filename="test.pdf",
                file_size=1024,
                mime_type="application/pdf",
                file_path="/uploads/tx.pdf",
                user_id=user.id,
            )
            
            # Try to create another user with duplicate username (will fail)
            user_crud.create_user(
                db,
                username="txuser",  # Duplicate!
                email="different@example.com",
                hashed_password="password",
            )
            
            db.commit()  # This should fail
            
        except Exception:
            db.rollback()
        
        # Verify rollback worked - user count should be unchanged
        final_user_count = user_crud.count(db)
        assert final_user_count == initial_user_count
        
        # Verify document was not created (rolled back)
        docs = document_crud.get_multi_by_user(db, user_id=user.id)
        assert len(docs) == 0
    
    def test_flush_without_commit(self, db: Session):
        """Test that flush without commit doesn't persist data."""
        initial_count = user_crud.count(db)
        
        # Create user with flush but no commit
        user = user_crud.create_user(
            db,
            username="flushuser",
            email="flush@example.com",
            hashed_password="password",
        )
        # Note: create_user calls flush internally
        
        # User should have an ID (from flush)
        assert user.id is not None
        
        # But rollback instead of commit
        db.rollback()
        
        # Count should be unchanged
        final_count = user_crud.count(db)
        assert final_count == initial_count


class TestComplexQueries:
    """Test complex query scenarios."""
    
    def test_get_documents_with_multiple_filters(self, db: Session):
        """Test filtering documents by multiple criteria."""
        # Create users
        user1 = user_crud.create_user(
            db,
            username="queryuser1",
            email="query1@example.com",
            hashed_password="password",
        )
        user2 = user_crud.create_user(
            db,
            username="queryuser2",
            email="query2@example.com",
            hashed_password="password",
        )
        
        # Create documents for user1 with different statuses
        for status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING, ProcessingStatus.COMPLETED]:
            document_crud.create_document(
                db,
                title=f"User1 {status.value}",
                original_filename=f"{status.value}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                file_path=f"/uploads/user1_{status.value}.pdf",
                user_id=user1.id,
                processing_status=status,
            )
        
        # Create documents for user2
        document_crud.create_document(
            db,
            title="User2 Doc",
            original_filename="user2.pdf",
            file_size=2048,
            mime_type="application/pdf",
            file_path="/uploads/user2.pdf",
            user_id=user2.id,
            processing_status=ProcessingStatus.COMPLETED,
        )
        
        db.commit()
        
        # Get only completed documents for user1
        user1_completed = document_crud.get_multi_by_user(
            db,
            user_id=user1.id,
            status=ProcessingStatus.COMPLETED,
        )
        
        assert len(user1_completed) == 1
        assert user1_completed[0].processing_status == ProcessingStatus.COMPLETED
        assert user1_completed[0].user_id == user1.id
        
        # Get all documents for user1
        user1_all = document_crud.get_multi_by_user(db, user_id=user1.id)
        assert len(user1_all) == 3
        
        # Verify user2 documents are separate
        user2_docs = document_crud.get_multi_by_user(db, user_id=user2.id)
        assert len(user2_docs) == 1
        assert user2_docs[0].file_size == 2048
    
    def test_batch_operations_performance(self, db: Session):
        """Test batch insert performance for chunks."""
        # Create user and document
        user = user_crud.create_user(
            db,
            username="batchuser",
            email="batch@example.com",
            hashed_password="password",
        )
        doc = document_crud.create_document(
            db,
            title="Batch Test",
            original_filename="batch.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_path="/uploads/batch.pdf",
            user_id=user.id,
        )
        db.commit()
        
        # Create 100 chunks using batch insert
        chunks_data = [
            {
                "document_id": doc.id,
                "chunk_text": f"Chunk {i} text content",
                "chunk_index": i,
                "character_count": 20,
                "token_count": 5,
            }
            for i in range(100)
        ]
        
        chunks = chunk_crud.create_batch(db, chunks_data=chunks_data)
        db.commit()
        
        # Verify all chunks were created
        assert len(chunks) == 100
        assert chunk_crud.count_by_document(db, document_id=doc.id) == 100
        
        # Verify chunks are properly ordered
        retrieved_chunks = chunk_crud.get_multi_by_document(
            db, document_id=doc.id, limit=100
        )
        assert [c.chunk_index for c in retrieved_chunks] == list(range(100))
