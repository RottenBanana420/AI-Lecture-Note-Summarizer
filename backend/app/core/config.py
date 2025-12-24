"""
Application configuration management using Pydantic Settings.

This module provides type-safe configuration loading from environment variables
with validation and default values.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All database configuration is loaded from .env file with validation.
    Provides computed DATABASE_URL property for SQLAlchemy connection.
    """
    
    # Database Configuration
    POSTGRES_USER: str = Field(..., description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password")
    POSTGRES_DB: str = Field(..., description="PostgreSQL database name")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    
    # Application Settings
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # API Configuration
    API_V1_PREFIX: str = Field(default="/api/v1", description="API version 1 prefix")
    
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
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",  # Ignore extra fields in .env
    }


# Global settings instance
# This is loaded once at application startup
settings = Settings()
