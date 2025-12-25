"""API v1 router."""

from fastapi import APIRouter
from app.api.v1.endpoints import documents

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(documents.router)
