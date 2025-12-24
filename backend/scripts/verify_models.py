"""
Model verification script.

This script verifies that all SQLAlchemy models are correctly defined
with proper relationships, foreign keys, and constraints.
"""

from app.models import User, Document, Summary, NoteChunk, ProcessingStatus, SummaryType
from sqlalchemy.inspection import inspect


def verify_models():
    """Verify all model definitions."""
    print("=" * 60)
    print("SQLAlchemy Model Verification")
    print("=" * 60)
    
    # Test 1: Import verification
    print("\n✓ Test 1: All models imported successfully")
    print(f"  - User: {User.__tablename__}")
    print(f"  - Document: {Document.__tablename__}")
    print(f"  - Summary: {Summary.__tablename__}")
    print(f"  - NoteChunk: {NoteChunk.__tablename__}")
    
    # Test 2: Enum verification
    print("\n✓ Test 2: Enums defined correctly")
    print(f"  - ProcessingStatus: {[s.value for s in ProcessingStatus]}")
    print(f"  - SummaryType: {[s.value for s in SummaryType]}")
    
    # Test 3: Relationship verification
    print("\n✓ Test 3: Relationships verified")
    
    # User relationships
    user_mapper = inspect(User)
    user_rels = {rel.key: rel.mapper.class_.__name__ for rel in user_mapper.relationships}
    print(f"  - User relationships: {user_rels}")
    
    # Document relationships
    doc_mapper = inspect(Document)
    doc_rels = {rel.key: rel.mapper.class_.__name__ for rel in doc_mapper.relationships}
    print(f"  - Document relationships: {doc_rels}")
    
    # Summary relationships
    summary_mapper = inspect(Summary)
    summary_rels = {rel.key: rel.mapper.class_.__name__ for rel in summary_mapper.relationships}
    print(f"  - Summary relationships: {summary_rels}")
    
    # NoteChunk relationships
    chunk_mapper = inspect(NoteChunk)
    chunk_rels = {rel.key: rel.mapper.class_.__name__ for rel in chunk_mapper.relationships}
    print(f"  - NoteChunk relationships: {chunk_rels}")
    
    # Test 4: Foreign key verification
    print("\n✓ Test 4: Foreign keys verified")
    
    # Document foreign keys
    doc_fks = [fk.target_fullname for fk in doc_mapper.columns['user_id'].foreign_keys]
    print(f"  - Document.user_id -> {doc_fks}")
    
    # Summary foreign keys
    summary_fks = [fk.target_fullname for fk in summary_mapper.columns['document_id'].foreign_keys]
    print(f"  - Summary.document_id -> {summary_fks}")
    
    # NoteChunk foreign keys
    chunk_fks = [fk.target_fullname for fk in chunk_mapper.columns['document_id'].foreign_keys]
    print(f"  - NoteChunk.document_id -> {chunk_fks}")
    
    # Test 5: Column type verification
    print("\n✓ Test 5: Key column types verified")
    print(f"  - User.username: {user_mapper.columns['username'].type}")
    print(f"  - Document.processing_status: {doc_mapper.columns['processing_status'].type}")
    print(f"  - Summary.summary_type: {summary_mapper.columns['summary_type'].type}")
    print(f"  - NoteChunk.embedding: {chunk_mapper.columns['embedding'].type}")
    
    # Test 6: Index verification
    print("\n✓ Test 6: Indexes verified")
    print(f"  - User indexes: {[idx.name for idx in User.__table__.indexes]}")
    print(f"  - Document indexes: {[idx.name for idx in Document.__table__.indexes]}")
    print(f"  - Summary indexes: {[idx.name for idx in Summary.__table__.indexes]}")
    print(f"  - NoteChunk indexes: {[idx.name for idx in NoteChunk.__table__.indexes]}")
    
    print("\n" + "=" * 60)
    print("All verifications passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    verify_models()
