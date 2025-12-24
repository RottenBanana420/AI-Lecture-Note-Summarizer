"""
FastAPI Application Entry Point.

This module initializes and configures the FastAPI application with:
- Lifespan events for startup/shutdown
- CORS middleware
- Custom middleware for logging and request tracking
- Global exception handlers
- API documentation configuration
- Health check endpoints
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import engine, check_database_connection, log_pool_status
from app.core.middleware import (
    RequestIDMiddleware,
    LoggingMiddleware,
    ErrorLoggingMiddleware,
)
from app.api.health import router as health_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Events
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events:
    - Startup: Verify database connectivity and log configuration
    - Shutdown: Close database connections and cleanup resources
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control to the application
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("=" * 80)
    logger.info("Starting AI Lecture Note Summarizer API")
    logger.info("=" * 80)
    
    # Log application configuration
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info(f"API Version: {settings.APP_VERSION}")
    logger.info(f"API Prefix: {settings.API_V1_PREFIX}")
    
    # Log CORS configuration
    logger.info(f"CORS Origins: {settings.CORS_ORIGINS_LIST}")
    
    # Verify database connectivity
    logger.info("Verifying database connectivity...")
    if check_database_connection():
        logger.info("✓ Database connection successful")
        log_pool_status()
    else:
        logger.error("✗ Database connection failed!")
        logger.error("Application may not function correctly")
    
    logger.info("=" * 80)
    logger.info("Application startup complete")
    logger.info("=" * 80)
    
    # Yield control to the application
    yield
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("=" * 80)
    logger.info("Shutting down AI Lecture Note Summarizer API")
    logger.info("=" * 80)
    
    # Log final connection pool status
    logger.info("Final connection pool status:")
    log_pool_status()
    
    # Dispose of database engine and close all connections
    logger.info("Closing database connections...")
    engine.dispose()
    logger.info("✓ Database connections closed")
    
    logger.info("=" * 80)
    logger.info("Application shutdown complete")
    logger.info("=" * 80)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=settings.DEBUG,
)


# ============================================================================
# Middleware Configuration
# ============================================================================

# 1. CORS Middleware (must be first to handle preflight requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["X-Request-ID", "X-Process-Time"],  # Expose custom headers
)

# 2. GZip Compression Middleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Only compress responses larger than 1KB
)

# 3. Error Logging Middleware (catch exceptions early)
app.add_middleware(ErrorLoggingMiddleware)

# 4. Request ID Middleware (add request ID to all requests)
app.add_middleware(RequestIDMiddleware)

# 5. Logging Middleware (log all requests/responses)
app.add_middleware(LoggingMiddleware)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Handle SQLAlchemy database errors.
    
    Args:
        request: The request that caused the error
        exc: The SQLAlchemy exception
        
    Returns:
        JSONResponse with error details
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"[{request_id}] Database error in {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database error",
            "message": "An error occurred while processing your request",
            "request_id": request_id,
        },
    )


@app.exception_handler(ValueError)
async def value_error_exception_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    """
    Handle validation errors.
    
    Args:
        request: The request that caused the error
        exc: The ValueError exception
        
    Returns:
        JSONResponse with error details
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        f"[{request_id}] Validation error in {request.method} {request.url.path}: {str(exc)}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation error",
            "message": str(exc),
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Catch-all handler for unhandled exceptions.
    
    Args:
        request: The request that caused the error
        exc: The exception
        
    Returns:
        JSONResponse with error details
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"[{request_id}] Unhandled exception in {request.method} {request.url.path}: "
        f"{type(exc).__name__}: {str(exc)}",
        exc_info=True,
    )
    
    # In production, don't expose internal error details
    if settings.ENVIRONMENT == "production":
        message = "An internal error occurred"
    else:
        message = f"{type(exc).__name__}: {str(exc)}"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": message,
            "request_id": request_id,
        },
    )


# ============================================================================
# API Routes
# ============================================================================

# Include health check endpoints (no prefix, available at root)
app.include_router(health_router)

# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict:
    """
    Root endpoint with API information.
    
    Returns:
        dict: API information and available endpoints
    """
    return {
        "name": settings.APP_TITLE,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


# Future API v1 routes will be added here
# Example:
# from app.api.v1 import api_router as api_v1_router
# app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
