# PostgreSQL Database Setup Guide

This guide covers the setup and management of PostgreSQL with pgvector extension for the AI Lecture Note Summarizer application.

## Prerequisites

- Docker and Docker Compose installed on your system
- Basic familiarity with PostgreSQL and Docker commands

## Quick Start

### 1. Start the Database

You can use the provided helper script:

```bash
./backend/scripts/start-db.sh
```

Or run manually:

```bash
docker-compose up -d
```

This command will:

- Pull the `pgvector/pgvector:pg15` Docker image (if not already present)
- Create a PostgreSQL container named `lecture_summarizer_postgres`
- Create a persistent volume named `lecture_summarizer_postgres_data`
- Automatically enable the pgvector extension via initialization script
- Start the database on port 5432

### 2. Verify Database is Running

You can use the provided verification script:

```bash
./backend/scripts/verify-db.sh
```

Or check manually:

```bash
# Check container status
cd backend && docker-compose ps

# View logs
cd backend && docker-compose logs postgres

# Check health status
cd backend && docker-compose ps postgres
```

Expected output should show the container as "healthy".

### 3. Connect to the Database

#### Using Docker Exec (Recommended for first-time setup)

```bash
docker-compose -f backend/docker-compose.yml exec postgres psql -U postgres -d lecture_summarizer_dev
```

#### Using psql Client from Host Machine

```bash
psql -h localhost -p 5432 -U postgres -d lecture_summarizer_dev
```

When prompted, enter the password from your `.env` file.

## Database Configuration

### Environment Variables

All database configuration is managed through environment variables in the `.env` file:

| Variable | Description | Default |
| --- | --- | --- |
| `POSTGRES_USER` | PostgreSQL superuser name | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password (auto-generated) | - |
| `POSTGRES_DB` | Database name | `lecture_summarizer_dev` |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `DATABASE_URL` | Complete connection string | Constructed from above |

### Connection String Format

```text
postgresql://[user]:[password]@[host]:[port]/[database]
```

Example:

```text
postgresql://postgres:qsv8IiVXXQp4FULIwmp5eeOlv4ZavVxpqRO0EsJnhg0=@localhost:5432/lecture_summarizer_dev
```

## pgvector Extension

### Verify Extension is Enabled

Connect to the database and run:

```sql
-- List all installed extensions
\dx

-- Check vector extension specifically
SELECT * FROM pg_extension WHERE extname = 'vector';
```

You should see `vector` in the list of installed extensions.

### Manual Extension Installation (if needed)

If the extension wasn't automatically installed:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Test Vector Functionality

```sql
-- Create a test table with vector column (384 dimensions for sentence embeddings)
CREATE TABLE test_embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO test_embeddings (content, embedding) 
VALUES 
    ('Machine learning is fascinating', '[0.1, 0.2, 0.3]'::vector),
    ('Deep learning uses neural networks', '[0.15, 0.25, 0.35]'::vector),
    ('Natural language processing', '[0.12, 0.22, 0.32]'::vector);

-- Perform cosine similarity search
-- The <-> operator calculates L2 distance (Euclidean)
-- The <#> operator calculates negative inner product
-- The <=> operator calculates cosine distance
SELECT 
    content,
    embedding <-> '[0.1, 0.2, 0.3]'::vector AS distance
FROM test_embeddings
ORDER BY embedding <-> '[0.1, 0.2, 0.3]'::vector
LIMIT 5;

-- Create an index for faster similarity searches (recommended for production)
CREATE INDEX ON test_embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Clean up test table
DROP TABLE test_embeddings;
```

## Common Operations

### Stop the Database

```bash
cd backend && docker-compose down
```

This stops and removes the container but **preserves data** in the volume.

### Stop and Remove All Data

```bash
# WARNING: This will delete all database data!
cd backend && docker-compose down -v
```

### Restart the Database

```bash
docker-compose restart postgres
```

### View Real-time Logs

```bash
docker-compose logs -f postgres
```

### Access PostgreSQL Shell

```bash
docker-compose exec postgres bash
```

## Data Persistence

Database data is stored in a Docker named volume: `lecture_summarizer_postgres_data`

### Verify Volume Exists

```bash
docker volume ls | grep lecture_summarizer
```

### Inspect Volume

```bash
docker volume inspect lecture_summarizer_postgres_data
```

### Backup Database

```bash
# Backup to SQL file
docker-compose exec -T postgres pg_dump -U postgres lecture_summarizer_dev > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup entire database cluster
docker-compose exec -T postgres pg_dumpall -U postgres > backup_all_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Database

```bash
# Restore from SQL file
docker-compose exec -T postgres psql -U postgres -d lecture_summarizer_dev < backup.sql
```

## Troubleshooting

### Container Won't Start

1. Check if port 5432 is already in use:

   ```bash
   lsof -i :5432
   ```

2. View detailed logs:

   ```bash
   docker-compose logs postgres
   ```

3. Verify environment variables:

   ```bash
   docker-compose config
   ```

### Cannot Connect from Host Machine

1. Verify container is running:

   ```bash
   docker-compose ps
   ```

2. Check if port is mapped correctly:

   ```bash
   docker-compose port postgres 5432
   ```

3. Test connection:

   ```bash
   nc -zv localhost 5432
   ```

### pgvector Extension Not Found

1. Verify you're using the correct image:

   ```bash
   docker-compose exec postgres psql -U postgres -c "SELECT version();"
   ```

2. Check available extensions:

   ```bash
   docker-compose exec postgres psql -U postgres -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
   ```

3. Manually create extension:

   ```bash
   docker-compose exec postgres psql -U postgres -d lecture_summarizer_dev -c "CREATE EXTENSION vector;"
   ```

### Performance Issues

1. Check container resources:

   ```bash
   docker stats lecture_summarizer_postgres
   ```

2. Review PostgreSQL configuration:

   ```bash
   docker-compose exec postgres psql -U postgres -c "SHOW ALL;"
   ```

## Security Best Practices

1. **Never commit `.env` file** - It contains sensitive credentials
2. **Use strong passwords** - Generate with `openssl rand -base64 32`
3. **Limit network access** - In production, restrict to specific IPs
4. **Regular backups** - Automate database backups
5. **Update regularly** - Keep PostgreSQL and pgvector updated
6. **Use SSL/TLS** - For production deployments
7. **Principle of least privilege** - Create application-specific users with limited permissions

## Production Considerations

For production deployment, consider:

1. **Dedicated Database User**: Create a user with limited privileges instead of using `postgres`

   ```sql
   CREATE USER app_user WITH PASSWORD 'secure_password';
   GRANT CONNECT ON DATABASE lecture_summarizer_dev TO app_user;
   GRANT USAGE ON SCHEMA public TO app_user;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
   ```

2. **Connection Pooling**: Use PgBouncer or similar for connection management

3. **Monitoring**: Set up monitoring with tools like pgAdmin, Prometheus, or Datadog

4. **Managed Service**: Consider using managed PostgreSQL services (AWS RDS, Google Cloud SQL, Azure Database)

5. **SSL Connections**: Enable SSL for encrypted connections

6. **Regular Maintenance**: Schedule VACUUM, ANALYZE, and REINDEX operations

## Additional Resources

- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/)
- [pgvector GitHub Repository](https://github.com/pgvector/pgvector)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
