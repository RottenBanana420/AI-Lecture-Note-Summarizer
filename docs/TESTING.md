# Testing Strategy and Guide

The AI Lecture Note Summarizer uses `pytest` for a comprehensive testing strategy that covers both unit logic and database integrations.

## Testing Philosophy

1. **Isolation**: Tests should not depend on each other. We use transaction rolling back in our database fixtures to ensure a clean state for every test.
2. **Coverage**: We aim for high code coverage (100% target for core logic).
3. **Speed**: Unit tests should be fast. Integration tests that touch the database are separated but optimized using connection pooling.
4. **Safety**: Tests running against a live database (even in Docker) must never affect production data. The configuration ensures tests run in a separate environment context.

## Test Categories

### Unit Tests

Located in `tests/test_crud/` (mostly) and `tests/test_models/`.
These test individual components, functions, and models. While some use the DB session, we treat them as "units" of CRUD functionality.

### Integration Tests

Located in `tests/integration/`.
These test scenarios involving multiple components, complex queries, or full workflows (e.g., verifying that deleting a document cascades to chunks and summaries properly).

## Running Tests

### Prerequisites

- Python virtual environment activated.
- Database container running (`./scripts/start-db.sh`).
- Environment variables configured (usually loaded from `.env` automatically by pytest-dotenv).

### Commands

**Run all tests:**

```bash
pytest
```

**Run with verbose output:**

```bash
pytest -v
```

**Run specific test file:**

```bash
pytest tests/test_crud/test_document.py
```

**Run specific test function:**

```bash
pytest tests/test_crud/test_document.py::TestDocumentCRUD::test_create_document
```

**Run with Code Coverage:**

```bash
# Requires pytest-cov
pytest --cov=app tests/
```

## Test Fixtures

Our `conftest.py` provides several powerful fixtures:

- **`db_session`**: A SQLAlchemy session that is rolled back after each test. Any changes made during the test are not committed to the database, ensuring isolation.
- **`client`**: A FastAPI TestClient for testing API endpoints (future use).
- **`user_in_db`**: A pre-created user for tests requiring an owner.

## Adding New Tests

1. **Identify the Scope**: Is it a detailed model test or a workflow integration?
2. **Create File**: Add a new file `test_<feature>.py` in the appropriate folder.
3. **Write Test Class**: Group related tests in a class (e.g., `class TestNewFeature:`).
4. **Use Fixtures**: Inject `db_session` to access the database.

### Example

```python
def test_create_new_entity(db_session):
    # Arrange
    data = {"name": "Test Entity"}
    
    # Act
    obj = create_entity(db_session, data)
    
    # Assert
    assert obj.id is not None
    assert obj.name == "Test Entity"
```
