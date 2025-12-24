"""
Unit tests for configuration module.

These tests verify configuration loading, validation, and computed properties
without requiring external dependencies like databases.
"""

import pytest
from pydantic import ValidationError
from app.core.config import Settings


@pytest.mark.unit
class TestSettingsValidation:
    """Test configuration validation."""
    
    def test_valid_configuration(self):
        """Test that valid configuration loads successfully."""
        settings = Settings(
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_DB="testdb",
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432
        )
        
        assert settings.POSTGRES_USER == "testuser"
        assert settings.POSTGRES_DB == "testdb"
        assert settings.POSTGRES_PORT == 5432
    
    def test_database_url_construction(self):
        """Test DATABASE_URL computed field."""
        settings = Settings(
            POSTGRES_USER="myuser",
            POSTGRES_PASSWORD="mypass",
            POSTGRES_DB="mydb",
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432
        )
        
        expected_url = "postgresql://myuser:mypass@localhost:5432/mydb"
        assert settings.DATABASE_URL == expected_url
    
    def test_invalid_port_validation(self):
        """Test that invalid port numbers are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                POSTGRES_PORT=99999  # Invalid port
            )
        
        assert "Port must be between 1 and 65535" in str(exc_info.value)
    
    def test_invalid_log_level(self):
        """Test that invalid log levels are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                LOG_LEVEL="INVALID"
            )
        
        assert "LOG_LEVEL must be one of" in str(exc_info.value)
    
    def test_invalid_environment(self):
        """Test that invalid environments are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                ENVIRONMENT="invalid_env"
            )
        
        assert "ENVIRONMENT must be one of" in str(exc_info.value)
    
    def test_cors_origins_parsing(self):
        """Test CORS origins are parsed correctly."""
        settings = Settings(
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db",
            CORS_ORIGINS="http://localhost:3000,http://localhost:5173",
            ENVIRONMENT="development"
        )
        
        assert len(settings.CORS_ORIGINS_LIST) == 2
        assert "http://localhost:3000" in settings.CORS_ORIGINS_LIST
        assert "http://localhost:5173" in settings.CORS_ORIGINS_LIST
    
    def test_cors_origins_production_filtering(self):
        """Test that localhost origins are filtered in production."""
        settings = Settings(
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db",
            CORS_ORIGINS="http://localhost:3000,https://example.com",
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,  # Valid production secret
            JWT_SECRET_KEY="b" * 32  # Valid production secret
        )
        
        # Localhost should be filtered out in production
        assert "http://localhost:3000" not in settings.CORS_ORIGINS_LIST
        assert "https://example.com" in settings.CORS_ORIGINS_LIST
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = Settings(
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db"
        )
        
        assert settings.POSTGRES_HOST == "localhost"
        assert settings.POSTGRES_PORT == 5432
        assert settings.ENVIRONMENT == "development"
        # DEBUG default is False, but can be overridden by .env
        assert settings.LOG_LEVEL == "INFO"


@pytest.mark.unit
class TestJWTConfiguration:
    """Test JWT-related configuration."""
    
    def test_jwt_algorithm_validation(self):
        """Test that valid JWT algorithms are accepted."""
        for algorithm in ["HS256", "HS384", "HS512", "RS256"]:
            settings = Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                JWT_ALGORITHM=algorithm
            )
            assert settings.JWT_ALGORITHM == algorithm
    
    def test_invalid_jwt_algorithm(self):
        """Test that invalid JWT algorithms are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                JWT_ALGORITHM="INVALID"
            )
        
        assert "JWT_ALGORITHM must be one of" in str(exc_info.value)
    
    def test_token_expiration_defaults(self):
        """Test default token expiration times."""
        settings = Settings(
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db"
        )
        
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
