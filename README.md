# AI Lecture Note Summarizer

A FastAPI-based backend application for the AI Lecture Note Summarizer project. This service provides RESTful APIs for processing and summarizing lecture notes using AI/ML models.

## Features

- **FastAPI Framework**: Modern, fast (high-performance) web framework for building APIs
- **PostgreSQL Database**: Robust relational database with SQLAlchemy ORM
- **pgvector Integration**: High-performance vector similarity search with semantic retrieval
- **Middleware Stack**: Production-ready middleware for Request ID tracing, GZip compression, and response timing
- **Enhanced Logging**: Structured logging for requests/responses and automatic error tracking
- **Health Monitoring**: Multiple health check endpoints for system, database, and connection pool status
- **CRUD Repository Pattern**: Generic base class for common database operations with model-specific extensions
- **Global Exception Handling**: Custom handlers for SQLAlchemy, validation, and general system errors
- **Connection Pooling**: Optimized session management with SQLAlchemy 2.0 best practices
- **Database Migrations**: Alembic for managing database schema changes
- **Type-Safe Configuration**: Secure settings management with Pydantic Settings and strict validation
- **Isolated Environment**: Python 3.11/3.12+ virtual environment support
- **PDF Processing**: Robust PDF validation, text extraction, and structure-aware cleaning using PyMuPDF
- **Intelligent Chunking**: Sentence-boundary-aware text segmentation using SpaCy for optimized semantic search
- **Vector Embeddings**: Support for high-dimensional embeddings (1536-D) for accurate retrieval
- **Document Upload API**: Production-ready endpoint for handling multipart PDF uploads with transaction-aware processing and automatic resource cleanup

## Core Data Models

The application implements a robust data model to manage the summarization lifecycle:

- **User**: Authentication and profile management (username, email, hashed password).
- **Document**: Metadata for uploaded lecture notes (title, file path, processing status).
- **Summary**: AI-generated summaries (extractive or abstractive) with processing metadata.
- **NoteChunk**: Text segments with high-dimensional vector embeddings (1536-D) for semantic search. These are automatically generated using our intelligent chunking service.

## Prerequisites

Before setting up the project, ensure you have the following installed:

- **pyenv**: Python version management tool
- **pyenv-virtualenv**: pyenv plugin for managing virtual environments
- **PostgreSQL**: Database server (managed via Docker)
- **Docker & Docker Compose**: For containerized database infrastructure
- **Git**: Version control system

### Installing Prerequisites (macOS)

```bash
# Install pyenv and pyenv-virtualenv
brew install pyenv pyenv-virtualenv

# Install PostgreSQL
brew install postgresql@15

# Add pyenv to your shell configuration
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.zshrc

# Restart your shell
exec "$SHELL"
```

## Project Structure

```text
.
├── backend/                 # FastAPI backend application
│   ├── app/                 # Application source code
│   │   ├── api/             # API versioned endpoints
│   │   │   ├── health.py    # Health check endpoints
│   │   │   └── v1/          # API v1 routes (future)
│   │   ├── core/            # Config, security, database setup
│   │   │   ├── config.py    # Settings and environment validation
│   │   │   ├── database.py  # SQLAlchemy engine and pooling
│   │   │   └── middleware.py # Request tracing and logging middleware
│   │   ├── crud/            # CRUD repository layer
│   │   │   ├── base.py      # Base CRUD class
│   │   │   ├── exceptions.py # CRUD-specific exceptions
│   │   │   └── user.py      # User-specific CRUD operations
│   │   ├── models/          # SQLAlchemy ORM models
│   │   │   ├── base_model.py # Base model with common fields
│   │   │   └── user.py      # User model definition
│   │   ├── schemas/         # Pydantic models (DTOs)
│   │   ├── db/              # Database base utilities
│   │   ├── services/        # Business logic services
│   │   │   ├── pdf_processor.py # PDF validation and text extraction
│   │   │   └── text_chunker.py  # Intelligent text chunking logic
│   │   └── main.py          # FastAPI application entry point
│   ├── alembic/             # Database migrations
│   ├── scripts/             # Infrastructure and verification scripts
│   │   ├── start-db.sh      # Start PostgreSQL/pgvector container
│   │   ├── verify-db.sh     # Verify DB and extension status
│   │   └── verify_models.py # Verify SQLAlchemy model definitions
│   ├── init-scripts/        # Database initialization SQL (pgvector)
│   ├── tests/               # Backend tests (pytest)
│   ├── docker-compose.yml   # Docker services (database, pgvector)
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment template
├── docs/                    # Project documentation
│   └── DATABASE_SETUP.md    # Detailed database setup guide
├── README.md                # This file
└── LICENSE                  # Project license
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AI-Lecture-Note-Summarizer
```

### 2. Set Up Python Virtual Environment

The virtual environment should already be configured if you're in the backend directory. Verify it's active:

```bash
cd backend

# Check Python version (should show 3.11.x)
python --version

# Verify virtual environment is active
pyenv version
```

If the virtual environment is not active:

```bash
# Activate the virtual environment
pyenv activate lecture-summarizer-backend

# Or set it locally for this directory
pyenv local lecture-summarizer-backend
```

### 3. Install Dependencies

```bash
# Ensure you are in the backend directory
cd backend

# Ensure pip is up to date
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Download SpaCy English language model (required for text chunking)
python -m spacy download en_core_web_sm
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual configuration
nano .env  # or use your preferred editor
```

**Important**: Update the following variables in `.env`:

- `DATABASE_URL`: Your PostgreSQL connection string
- `SECRET_KEY`: Generate a secure random string (min 32 chars in production)
- `ENVIRONMENT`: Set to `development`, `staging`, or `production`
- `DEBUG`: Set to `False` in production
- `CORS_ORIGINS`: Comma-separated list of allowed origins
- `UPLOAD_DIR`: Local directory for stored PDF files (default: `uploads`)
- `MAX_UPLOAD_SIZE`: Maximum allowed file size in bytes (default: 50MB)

### 5. Set Up PostgreSQL Database

The project uses Docker Compose to manage a PostgreSQL instance with the `pgvector` extension.

```bash
# Start the database using the helper script
./scripts/start-db.sh

# Verify the setup
./scripts/verify-db.sh

# Verify model definitions
PYTHONPATH=. python scripts/verify_models.py
```

For detailed database configuration and manual setup instructions, see [docs/DATABASE_SETUP.md](docs/DATABASE_SETUP.md).

### 6. Apply Database Migrations

The database schema is managed via Alembic. Apply the latest migrations to set up your tables and indexes:

```bash
# Apply migrations
alembic upgrade head
```

This will:

- Create `users`, `documents`, `summaries`, and `note_chunks` tables
- Enable `pgvector` extension
- Create HNSW indexes for fast vector similarity search

## Running the Application

### Development Server

```bash
# Run with auto-reload enabled
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

- **API Root**: <http://localhost:8000>
- **Health Check**: <http://localhost:8000/health>
- **Detailed Health**: <http://localhost:8000/health/detailed>
- **Interactive API docs (Swagger)**: <http://localhost:8000/docs>
- **Alternative API docs (ReDoc)**: <http://localhost:8000/redoc>

### Key API Endpoints (v1)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/documents/upload` | Upload and process a PDF document (multipart/form-data) |

### Monitoring & Health Checks

The application provides built-in health monitoring:

| Endpoint | Purpose | Description |
| :--- | :--- | :--- |
| `/health` | Basic | Checks if API service is running |
| `/health/db` | Database | Verifies active database connectivity |
| `/health/detailed` | Full System | Status of API, DB, and connection pool statistics |

### Request Tracing & Performance

Every request automatically includes:

- `X-Request-ID`: Unique ID for tracing across logs
- `X-Process-Time`: Server-side processing duration in milliseconds
- Structured logging with client IP and request metadata

## Development Workflow

### Virtual Environment Management

```bash
# Activate virtual environment
pyenv activate lecture-summarizer-backend

# Deactivate virtual environment
pyenv deactivate

# List all virtual environments
pyenv virtualenvs
```

### Adding New Dependencies

```bash
# Install new package
pip install package-name

# Update requirements.txt (manually adding is recommended for cleaner file)
echo "package-name  # Description of what this package does" >> requirements.txt
```

### Database Migrations

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

## Testing

The project uses `pytest` for unit and integration testing. Configuration is located in `backend/pyproject.toml`.

For a detailed guide on our testing strategy and philosophy, see [docs/TESTING.md](docs/TESTING.md).

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run integration tests (requires running database)
pytest -m integration

# Run with coverage (if pytest-cov is installed)
pytest --cov=app tests/
```

## Database Schema

For a detailed visual diagram and explanation of the data models, see [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md).

## Troubleshooting

### Database Connection Fails

- **Issue**: `OperationalError: connection to server at "localhost" ... failed`
- **Solution**: Ensure your Docker container is running (`docker ps`). If running from inside another container, ensure you are using the correct network hostname (`host.docker.internal` or service name).

### Migrations Not Applying

- **Issue**: `alembic` command not found or dependency errors.
- **Solution**: Ensure you are in the `backend/` directory and your virtual environment is active (`pyenv activate ...`).

### Tests Failing

- **Issue**: Tests fail with "relation does not exist".
- **Solution**: Your test database might be uninitialized. Run migrations using `alembic upgrade head` before running tests, or check if the test fixture setup is correct.

## Environment Variables Reference

See `backend/.env.example` for a complete list of configurable environment variables.

### Required Variables

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Application secret key for security

### Optional Variables

- `DEBUG`: Enable debug mode (default: True)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins
- `API_V1_PREFIX`: API version 1 prefix (default: /api/v1)

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Write/update tests
4. Ensure all tests pass
5. Submit a pull request

## License

[MIT License](LICENSE)

## Contact

For questions or support, please open an issue in the repository.
