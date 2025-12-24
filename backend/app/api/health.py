"""
Health check endpoints for monitoring application status.

Provides endpoints to check:
- Basic application health
- Database connectivity
- Detailed system information
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db, get_pool_status, check_database_connection
from app.core.config import settings

# Create router for health check endpoints
router = APIRouter(tags=["Health"])


@router.get("/health", summary="Basic health check")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        dict: Basic health status
        
    Response:
        {
            "status": "healthy",
            "timestamp": "2024-12-24T14:30:00.000000",
            "environment": "development",
            "version": "1.0.0"
        }
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
    }


@router.get("/health/db", summary="Database connectivity check")
async def health_check_db(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Check database connectivity.
    
    Args:
        db: Database session from dependency injection
        
    Returns:
        dict: Database health status
        
    Raises:
        HTTPException: If database connection fails
        
    Response:
        {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2024-12-24T14:30:00.000000"
        }
    """
    try:
        # Execute simple query to verify connection
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )


@router.get("/health/detailed", summary="Detailed health check")
async def health_check_detailed(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check with system information.
    
    Includes:
    - Application status
    - Database connectivity
    - Connection pool statistics
    - Environment information
    
    Args:
        db: Database session from dependency injection
        
    Returns:
        dict: Detailed health status
        
    Response:
        {
            "status": "healthy",
            "timestamp": "2024-12-24T14:30:00.000000",
            "application": {
                "name": "AI Lecture Note Summarizer API",
                "version": "1.0.0",
                "environment": "development",
                "debug": true
            },
            "database": {
                "status": "connected",
                "pool": {
                    "size": 5,
                    "checked_out": 1,
                    "overflow": 0,
                    "total": 5
                }
            }
        }
    """
    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Get connection pool statistics
    pool_stats = get_pool_status()
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "application": {
            "name": settings.APP_TITLE,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
        },
        "database": {
            "status": db_status,
            "pool": pool_stats,
        },
    }
