"""
Migration utility functions for Alembic.

This module provides reusable helper functions for common migration patterns,
especially for pgvector extension and HNSW index creation.
"""

from alembic import op
from sqlalchemy import text


def create_pgvector_extension():
    """
    Create the pgvector extension if it doesn't exist.
    
    This should be called in the upgrade() function of migrations
    that use vector columns.
    
    Example:
        def upgrade():
            create_pgvector_extension()
            # ... rest of migration
    """
    op.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def drop_pgvector_extension():
    """
    Drop the pgvector extension if no tables are using it.
    
    WARNING: Only call this in downgrade() if you're certain
    no other tables are using vector columns.
    
    Example:
        def downgrade():
            # ... drop tables with vector columns first
            drop_pgvector_extension()
    """
    op.execute(text("DROP EXTENSION IF EXISTS vector"))


def create_hnsw_index(
    index_name: str,
    table_name: str,
    column_name: str,
    m: int = 16,
    ef_construction: int = 64,
    distance_metric: str = "vector_cosine_ops"
):
    """
    Create an HNSW index for vector similarity search.
    
    HNSW (Hierarchical Navigable Small World) is a graph-based algorithm
    for approximate nearest neighbor search. It provides better performance
    than IVFFlat for most use cases.
    
    Args:
        index_name: Name of the index to create
        table_name: Name of the table containing the vector column
        column_name: Name of the vector column
        m: Number of connections per layer (default: 16)
            - Higher values = better recall, more memory
            - Recommended range: 4-64
        ef_construction: Size of dynamic candidate list (default: 64)
            - Higher values = better quality, slower build
            - Recommended range: 32-512
        distance_metric: Distance metric operator (default: vector_cosine_ops)
            - vector_cosine_ops: Cosine distance (1 - cosine similarity)
            - vector_l2_ops: Euclidean distance (L2)
            - vector_ip_ops: Inner product (negative for max inner product)
    
    Example:
        def upgrade():
            create_pgvector_extension()
            # ... create table with vector column
            create_hnsw_index(
                "ix_note_chunks_embedding_hnsw",
                "note_chunks",
                "embedding",
                m=16,
                ef_construction=64
            )
    
    References:
        - pgvector HNSW: https://github.com/pgvector/pgvector#hnsw
        - Parameter tuning: https://github.com/pgvector/pgvector#indexing
    """
    op.execute(text(
        f"CREATE INDEX {index_name} ON {table_name} "
        f"USING hnsw ({column_name} {distance_metric}) "
        f"WITH (m = {m}, ef_construction = {ef_construction})"
    ))


def drop_index(index_name: str):
    """
    Drop an index by name.
    
    Args:
        index_name: Name of the index to drop
    
    Example:
        def downgrade():
            drop_index("ix_note_chunks_embedding_hnsw")
    """
    op.execute(text(f"DROP INDEX IF EXISTS {index_name}"))


def check_extension_exists(extension_name: str) -> bool:
    """
    Check if a PostgreSQL extension exists.
    
    Args:
        extension_name: Name of the extension to check
    
    Returns:
        bool: True if extension exists, False otherwise
    
    Note:
        This is primarily for documentation purposes.
        In practice, using "IF NOT EXISTS" is safer for migrations.
    """
    # This is a helper for documentation
    # In migrations, always use "IF NOT EXISTS" instead
    pass
