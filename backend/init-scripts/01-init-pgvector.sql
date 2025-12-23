-- Initialize pgvector extension for the lecture_summarizer_dev database
-- This script runs automatically when the PostgreSQL container is first created
-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
-- Verify extension is installed
DO $$ BEGIN IF EXISTS (
    SELECT 1
    FROM pg_extension
    WHERE extname = 'vector'
) THEN RAISE NOTICE 'pgvector extension successfully installed';
ELSE RAISE EXCEPTION 'Failed to install pgvector extension';
END IF;
END $$;
-- Create a comment for documentation
COMMENT ON EXTENSION vector IS 'Vector similarity search extension for PostgreSQL';