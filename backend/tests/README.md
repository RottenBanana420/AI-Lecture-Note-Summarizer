# Testing Guide

This guide explains how to run tests, write new tests, and understand the testing infrastructure.

## Quick Start

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run in parallel
pytest -n auto
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── utils/
│   └── database.py          # Database utilities
├── unit/                    # Unit tests (fast, no DB)
│   ├── test_config.py
│   └── ...
└── integration/             # Integration tests (with DB)
    ├── test_sample.py
    └── ...
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Types

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# Database tests
pytest -m database

# API tests
pytest -m api

# Exclude slow tests
pytest -m "not slow"
```

### Run Specific Files or Tests

```bash
# Single file
pytest tests/unit/test_config.py

# Single test class
pytest tests/unit/test_config.py::TestSettingsValidation

# Single test function
pytest tests/unit/test_config.py::TestSettingsValidation::test_valid_configuration

# Pattern matching
pytest -k "user"  # Run tests with "user" in name
```

### Parallel Execution

```bash
# Use all CPU cores
pytest -n auto

# Use specific number of workers
pytest -n 4

# Parallel with coverage (requires pytest-cov)
pytest -n auto --cov=app
```

### Verbose Output

```bash
# Verbose mode
pytest -v

# Very verbose (show test docstrings)
pytest -vv

# Show local variables on failure
pytest -l

# Show print statements
pytest -s
```

## Coverage Reporting

### Generate Coverage Reports

```bash
# Terminal report with missing lines
pytest --cov=app --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=app --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=app --cov-report=xml

# Multiple formats
pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml
```

### Coverage Configuration

Coverage settings are in `pyproject.toml`:

- **Source**: `app/` directory
- **Omit**: Tests, migrations, cache
- **Branch coverage**: Enabled
- **Minimum coverage**: Not enforced (configure with `--cov-fail-under=N`)

## Writing Tests

### Unit Tests

Unit tests are fast and don't require external dependencies:

```python
import pytest
from app.core.config import Settings

@pytest.mark.unit
def test_configuration():
    """Test configuration validation."""
    settings = Settings(
        POSTGRES_USER="user",
        POSTGRES_PASSWORD="pass",
        POSTGRES_DB="db"
    )
    assert settings.POSTGRES_PORT == 5432
```

### Integration Tests with Database

Integration tests use fixtures for database access:

```python
import pytest
from sqlalchemy.orm import Session
from app.models import User

@pytest.mark.integration
@pytest.mark.database
def test_create_user(db_session: Session):
    """Test creating a user in database."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hash"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    assert user.id is not None
    # Changes are automatically rolled back after test
```

### Using Fixtures

Common fixtures available in `conftest.py`:

```python
def test_with_sample_data(sample_user, sample_document, db_session):
    """Test using pre-created sample data."""
    assert sample_user.id is not None
    assert sample_document.user_id == sample_user.id
```

Available fixtures:

- `db_session` - Database session with automatic rollback
- `client` - FastAPI TestClient
- `sample_user` - Pre-created test user
- `sample_document` - Pre-created test document
- `sample_user_inactive` - Inactive user for auth tests
- `multiple_users` - List of test users

### API Endpoint Tests

Test API endpoints using the `client` fixture:

```python
@pytest.mark.integration
@pytest.mark.api
def test_api_endpoint(client):
    """Test API endpoint."""
    response = client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "username": "test"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
```

## Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit          # Fast, no external dependencies
@pytest.mark.integration   # Requires database
@pytest.mark.database      # Database operations
@pytest.mark.api           # API endpoint tests
@pytest.mark.slow          # Long-running tests
```

## Test Database

### Configuration

Tests use a separate PostgreSQL database:

- **Name**: `{POSTGRES_DB}_test` (e.g., `lecture_summarizer_test`)
- **Auto-created**: Database is created automatically if it doesn't exist
- **Isolation**: Each test runs in a transaction that's rolled back

### Manual Database Management

```python
from tests.utils.database import (
    create_test_database,
    drop_test_database,
    get_test_db_url
)

# Create test database
create_test_database()

# Get test database URL
url = get_test_db_url()

# Drop test database (careful!)
drop_test_database(force=True)
```

## Debugging Tests

### Show Test Output

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l --tb=long

# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb
```

### Run Specific Failed Tests

```bash
# Rerun only failed tests from last run
pytest --lf

# Run failed tests first, then others
pytest --ff
```

### Show Slowest Tests

```bash
# Show 10 slowest tests
pytest --durations=10

# Show all test durations
pytest --durations=0
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run tests
  run: |
    cd backend
    pytest --cov=app --cov-report=xml --cov-report=term-missing -n auto

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./backend/coverage.xml
```

### GitLab CI Example

```yaml
test:
  script:
    - cd backend
    - pip install -r requirements.txt
    - pytest --cov=app --cov-report=xml -n auto
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: backend/coverage.xml
```

## Best Practices

1. **Keep tests isolated**: Each test should be independent
2. **Use fixtures**: Reuse setup code via fixtures
3. **Test one thing**: Each test should verify one behavior
4. **Descriptive names**: Use clear test function names
5. **Use markers**: Categorize tests for selective execution
6. **Fast unit tests**: Keep unit tests fast (no DB, no network)
7. **Parallel execution**: Run tests in parallel for speed
8. **Coverage goals**: Aim for high coverage, but focus on critical paths
9. **Clean assertions**: Use clear, simple assertions
10. **Document tests**: Add docstrings explaining what's being tested

## Troubleshooting

### Database Connection Errors

If you see database connection errors:

1. Check that PostgreSQL is running
2. Verify `.env` file has correct credentials
3. Ensure test database exists (it should auto-create)
4. Check that user has CREATE DATABASE privileges

### Import Errors

If you see import errors:

1. Ensure you're in the `backend/` directory
2. Check that all dependencies are installed: `pip install -r requirements.txt`
3. Verify Python path includes the project root

### Parallel Execution Issues

If parallel tests fail:

1. Ensure tests are isolated (no shared state)
2. Check for database connection pool limits
3. Try reducing workers: `pytest -n 2`

### Coverage Not Working

If coverage reports are empty:

1. Check that source path is correct in `pyproject.toml`
2. Ensure you're running from `backend/` directory
3. Verify pytest-cov is installed: `pip install pytest-cov`

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
