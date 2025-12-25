# Changelog

All notable changes to the AI Lecture Note Summarizer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (2025-12-25)

#### Documentation

- **API_USAGE.md**: Comprehensive API endpoint documentation with detailed request/response examples, error handling, and usage patterns
- **PDF_PROCESSING.md**: In-depth guide to the PDF processing pipeline including validation, text extraction, preprocessing, and performance benchmarks
- **PERFORMANCE.md**: Performance benchmarks, optimization strategies, and scalability testing results
- **TROUBLESHOOTING.md**: Common issues and solutions for database, API, PDF processing, and deployment scenarios
- Performance test suite (`backend/tests/performance/`) for benchmarking PDF processing pipeline

#### Configuration

- Updated `.gitignore` to exclude:
  - `uploads/` directory (user-uploaded files)
  - `backend/uploads/` directory
  - Performance test results (`backend/tests/performance/results/`)
  - Benchmark JSON files (`*.benchmark.json`)
- Updated `backend/.env.example` with correct file upload configuration:
  - `UPLOAD_DIR` variable (default: `uploads`)
  - `MAX_UPLOAD_SIZE` set to 50MB (52428800 bytes)
  - `ALLOWED_MIME_TYPES` for PDF validation

#### Documentation Updates

- Updated `README.md` with:
  - New documentation section linking to all guides
  - Updated project structure showing all documentation files
  - References to comprehensive guides for developers

### Changed

#### Environment Configuration

- File upload configuration now properly documented with:
  - Explicit MIME type validation (application/pdf)
  - Clear size limits (50MB default)
  - Upload directory configuration

### Fixed

- Aligned `.env.example` with actual application configuration in `config.py`
- Ensured all documentation files are tracked in version control

## Previous Releases

### [1.0.0] - 2025-12-24

#### Added

- Document upload API endpoint (`POST /api/v1/documents/upload`)
- PDF processing service with validation and text extraction
- Intelligent text chunking using SpaCy
- Comprehensive test suite with 100% coverage
- Database migrations for all models
- Health check endpoints
- Request tracing and logging middleware

#### Core Features

- FastAPI backend with PostgreSQL and pgvector
- User, Document, Summary, and NoteChunk models
- CRUD repository pattern
- Global exception handling
- Connection pooling and session management

---

## Notes

### Documentation Structure

The project now includes comprehensive documentation in the `docs/` directory:

- API usage and examples
- PDF processing pipeline details
- Performance benchmarks and optimization
- Testing strategy and guide
- Database setup and schema
- Troubleshooting common issues

### Configuration Management

All environment variables are documented in `backend/.env.example` with:

- Clear descriptions
- Default values
- Security recommendations
- Production considerations
