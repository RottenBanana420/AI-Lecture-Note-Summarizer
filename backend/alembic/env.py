"""
Alembic environment configuration for database migrations.

This module configures Alembic to work with our SQLAlchemy models,
including support for autogeneration, naming conventions, and pgvector.
"""

from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool, MetaData
from alembic import context

# Add the parent directory to the path so we can import our app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import application settings and database configuration
from app.core.config import settings
from app.core.database import Base

# Import all models to ensure they're registered with SQLAlchemy
# This is critical for autogenerate to detect all tables
from app.models.user import User
from app.models.document import Document
from app.models.summary import Summary
from app.models.note_chunk import NoteChunk

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the SQLAlchemy URL from our application settings
# This overrides the placeholder in alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure naming conventions for constraints
# This ensures consistent naming across databases and makes migrations more reliable
# Following SQLAlchemy best practices: https://alembic.sqlalchemy.org/en/latest/naming.html
convention = {
    "ix": "ix_%(column_0_label)s",  # Index
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # Unique constraint
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # Check constraint
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # Foreign key
    "pk": "pk_%(table_name)s"  # Primary key
}

# Create metadata with naming conventions
metadata = MetaData(naming_convention=convention)

# Set target metadata for autogenerate support
# This tells Alembic which models to track for schema changes
target_metadata = Base.metadata
target_metadata.naming_convention = convention


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include object names in autogenerate
        compare_type=True,
        compare_server_default=True,
        # Render schema changes for enums
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override the ini file sqlalchemy.url with our application's database URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't use connection pooling for migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Include object names in autogenerate
            compare_type=True,
            compare_server_default=True,
            # Render schema changes for enums
            render_as_batch=False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
