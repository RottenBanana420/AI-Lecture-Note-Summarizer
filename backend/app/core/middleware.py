"""
Custom middleware for FastAPI application.

This module provides middleware for:
- Request ID generation and tracking
- Request/response logging with timing
- Error logging and handling
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Configure logging
logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID to each request.
    
    The request ID is:
    - Generated as a UUID4
    - Added to request state for access in route handlers
    - Included in response headers for client-side tracing
    - Included in all log messages for request correlation
    
    Usage in route handlers:
        @app.get("/items")
        def get_items(request: Request):
            request_id = request.state.request_id
            logger.info(f"Processing request {request_id}")
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add request ID.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            Response with X-Request-ID header
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store in request state for access in route handlers
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses with timing information.
    
    Logs:
    - Request method, path, and query parameters
    - Response status code
    - Request processing time
    - Request ID for correlation
    - Client IP address
    
    Log format:
        INFO: [REQUEST_ID] METHOD /path?query - STATUS_CODE - DURATION ms - CLIENT_IP
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details with timing.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            Response object
        """
        # Get request ID (set by RequestIDMiddleware)
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Start timer
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            f"[{request_id}] Incoming request: {request.method} {request.url.path} "
            f"from {client_ip}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Log response
        log_message = (
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {process_time:.2f}ms - "
            f"Client: {client_ip}"
        )
        
        # Use different log levels based on status code
        if response.status_code >= 500:
            logger.error(log_message)
        elif response.status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Add processing time to response headers
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        
        return response


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch and log unhandled exceptions.
    
    This middleware:
    - Catches all unhandled exceptions
    - Logs exception details with request context
    - Re-raises the exception for FastAPI's exception handlers
    
    Note: This should be added early in the middleware stack
    to catch exceptions from other middleware.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and catch unhandled exceptions.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            Response object
            
        Raises:
            Exception: Re-raises caught exceptions after logging
        """
        # Get request ID for logging
        request_id = getattr(request.state, "request_id", "unknown")
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log the exception with request context
            logger.error(
                f"[{request_id}] Unhandled exception in {request.method} {request.url.path}: "
                f"{type(e).__name__}: {str(e)}",
                exc_info=True  # Include full traceback
            )
            # Re-raise for FastAPI's exception handlers
            raise
