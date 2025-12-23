# AI Lecture Note Summarizer

A FastAPI-based backend application for the AI Lecture Note Summarizer project. This service provides RESTful APIs for processing and summarizing lecture notes using AI/ML models.

## Features

- **FastAPI Framework**: Modern, fast (high-performance) web framework for building APIs
- **PostgreSQL Database**: Robust relational database with SQLAlchemy ORM
- **Database Migrations**: Alembic for managing database schema changes
- **Environment Configuration**: Secure configuration management with python-dotenv
- **Isolated Environment**: Python 3.11 virtual environment using pyenv-virtualenv

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
│   ├── alembic/             # Database migrations
│   ├── scripts/             # Infrastructure helper scripts
│   ├── init-scripts/        # Database initialization SQL
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
# Check Python version (should show 3.11.14)
python --version

# Check which Python is being used (should point to pyenv)
which python

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
./backend/scripts/start-db.sh

# Verify the setup
./backend/scripts/verify-db.sh
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

### Production Server

```bash
# Run with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Development Workflow

### Virtual Environment Management

```bash
# Activate virtual environment
pyenv activate lecture-summarizer-backend

# Deactivate virtual environment
pyenv deactivate

# List all virtual environments
pyenv virtualenvs

# Verify isolation
pip list  # Should only show installed project dependencies
```

### Adding New Dependencies

```bash
# Install new package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt

# Or manually add to requirements.txt (recommended for cleaner file)
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

# Run specific test file
pytest tests/test_example.py
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

## Environment Variables Reference

See `.env.example` for a complete list of configurable environment variables.

### Required Variables

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Application secret key for security

### Optional Variables

- `DEBUG`: Enable debug mode (default: True)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins
- `API_V1_PREFIX`: API version 1 prefix (default: /api/v1)

## Troubleshooting

### Virtual Environment Issues

```bash
# If virtual environment is not activating
pyenv virtualenv 3.11.14 lecture-summarizer-backend
pyenv local lecture-summarizer-backend

# If Python version is incorrect
pyenv install 3.11.14
pyenv virtualenv 3.11.14 lecture-summarizer-backend
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
brew services list | grep postgresql

# Test database connection
psql -U your_username -d lecture_summarizer

# Check DATABASE_URL format
# postgresql://username:password@host:port/database_name
```

### Dependency Issues

```bash
# Clear pip cache
pip cache purge

# Reinstall all dependencies
pip install --force-reinstall -r requirements.txt
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Write/update tests
4. Ensure all tests pass
5. Submit a pull request

## License

[Add your license information here]

## Contact

[Add contact information or links to documentation]
