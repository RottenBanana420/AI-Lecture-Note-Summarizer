# AI Lecture Note Summarizer

A FastAPI-based backend application for the AI Lecture Note Summarizer project. This service provides RESTful APIs for processing and summarizing lecture notes using AI/ML models.

## Features

- **FastAPI Framework**: Modern, fast (high-performance) web framework for building APIs
- **PostgreSQL Database**: Robust relational database with SQLAlchemy ORM
- **pgvector Integration**: Vector similarity search for semantic retrieval of lecture note chunks
- **Database Migrations**: Alembic for managing database schema changes
- **Environment Configuration**: Secure configuration management with python-dotenv and pydantic-settings
- **Isolated Environment**: Python 3.11 virtual environment using pyenv-virtualenv

## Core Data Models

The application implements a robust data model to manage the summarization lifecycle:

- **User**: Authentication and profile management (username, email, hashed password).
- **Document**: Metadata for uploaded lecture notes (title, file path, processing status).
- **Summary**: AI-generated summaries (extractive or abstractive) with processing metadata.
- **NoteChunk**: Text segments with high-dimensional vector embeddings (1536-D) for semantic search.

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
│   │   ├── api/             # API v1 endpoints
│   │   ├── core/            # Config, security, database setup
│   │   ├── db/              # Database base and session manager
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic models (DTOs)
│   │   └── main.py          # FastAPI application entry point
│   ├── alembic/             # Database migrations
│   ├── scripts/             # Infrastructure and verification scripts
│   │   ├── start-db.sh      # Start PostgreSQL/pgvector container
│   │   ├── verify-db.sh     # Verify DB and extension status
│   │   └── verify_models.py # Verify SQLAlchemy model definitions
│   ├── init-scripts/        # Database initialization SQL (pgvector)
│   ├── tests/               # Backend tests
│   ├── docker-compose.yml   # Docker services
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
# Ensure pip is up to date
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
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
- `SECRET_KEY`: Generate a secure random string
- `DEBUG`: Set to `False` in production

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

### 6. Initialize Database Migrations (When Ready)

```bash
# Initialize Alembic (run this once)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

## Running the Application

### Development Server

```bash
# Run with auto-reload enabled
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

- **API**: <http://localhost:8000>
- **Interactive API docs (Swagger)**: <http://localhost:8000/docs>
- **Alternative API docs (ReDoc)**: <http://localhost:8000/redoc>

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

```bash
# Run tests (when test suite is implemented)
pytest

# Run with coverage
pytest --cov=app tests/
```

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
