"""
Application configuration management using Pydantic Settings.

This module provides type-safe configuration loading from environment variables
with validation and default values.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, computed_field
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All database configuration is loaded from .env file with validation.
    Provides computed DATABASE_URL property for SQLAlchemy connection.
    """
    
    # ========================================================================
    # Application Metadata
    # ========================================================================
    APP_TITLE: str = Field(
        default="AI Lecture Note Summarizer API",
        description="Application title for API documentation"
    )
    APP_DESCRIPTION: str = Field(
        default="FastAPI backend for AI-powered lecture note summarization",
        description="Application description for API documentation"
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    # ========================================================================
    # Environment Configuration
    # ========================================================================
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment mode: development, staging, or production"
    )
    DEBUG: bool = Field(
        default=False,
        description="Debug mode flag"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # ========================================================================
    # Database Configuration
    # ========================================================================
    POSTGRES_USER: str = Field(..., description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password")
    POSTGRES_DB: str = Field(..., description="PostgreSQL database name")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """
        Construct PostgreSQL database URL from individual components.
        
        Returns:
            str: Complete database connection URL for SQLAlchemy
        """
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # ========================================================================
    # Security Configuration
    # ========================================================================
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production",
        description="Secret key for session management and JWT"
    )
    JWT_SECRET_KEY: str = Field(
        default="your-jwt-secret-key-here",
        description="Secret key for JWT token signing"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )
    
    # ========================================================================
    # CORS Configuration
    # ========================================================================
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins"
    )
    
    @computed_field
    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """
        Parse CORS origins from comma-separated string to list.
        
        In production, this should be restricted to specific domains.
        In development, typically includes localhost with various ports.
        
        Returns:
            List[str]: List of allowed origins
        """
        if self.ENVIRONMENT == "production":
            # In production, parse from env var
            origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
            # Filter out localhost origins in production
            return [o for o in origins if "localhost" not in o and "127.0.0.1" not in o]
        else:
            # In development, allow configured origins
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # ========================================================================
    # API Configuration
    # ========================================================================
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="API version 1 prefix"
    )
    
    # ========================================================================
    # File Upload Configuration
    # ========================================================================
    UPLOAD_DIR: str = Field(
        default="uploads",
        description="Directory for storing uploaded files"
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=50 * 1024 * 1024,  # 50MB in bytes
        description="Maximum file size in bytes"
    )
    ALLOWED_MIME_TYPES: str = Field(
        default="application/pdf",
        description="Comma-separated list of allowed MIME types"
    )
    
    @computed_field
    @property
    def ALLOWED_MIME_TYPES_LIST(self) -> List[str]:
        """
        Parse allowed MIME types from comma-separated string to list.
        
        Returns:
            List[str]: List of allowed MIME types
        """
        return [mime.strip() for mime in self.ALLOWED_MIME_TYPES.split(",")]
    
    # ========================================================================
    # Validators
    # ========================================================================
    
    @field_validator("POSTGRES_PORT")
    @classmethod
    def validate_port(cls, v):
        """Validate PostgreSQL port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is a valid Python logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment is one of the allowed values."""
        valid_environments = ["development", "staging", "production"]
        if v.lower() not in valid_environments:
            raise ValueError(f"ENVIRONMENT must be one of {valid_environments}")
        return v.lower()
    
    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v):
        """Validate JWT algorithm is supported."""
        valid_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v.upper() not in valid_algorithms:
            raise ValueError(f"JWT_ALGORITHM must be one of {valid_algorithms}")
        return v.upper()
    
    @field_validator("SECRET_KEY", "JWT_SECRET_KEY")
    @classmethod
    def validate_secret_keys(cls, v, info):
        """Validate secret keys are not using default values in production."""
        # This validator runs for both SECRET_KEY and JWT_SECRET_KEY
        if "production" in str(info.data.get("ENVIRONMENT", "")).lower():
            if "change" in v.lower() or "your-" in v.lower() or len(v) < 32:
                raise ValueError(
                    f"{info.field_name} must be a strong secret in production "
                    "(min 32 characters, no default values)"
                )
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",  # Ignore extra fields in .env
    }


# Global settings instance
# This is loaded once at application startup
settings = Settings()
