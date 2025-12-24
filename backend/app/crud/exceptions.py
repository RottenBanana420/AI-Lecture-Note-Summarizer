"""
Custom exceptions for CRUD operations.

This module defines custom exceptions that provide better error handling
and more specific error messages for database operations.
"""


class CRUDException(Exception):
    """Base exception for all CRUD operations."""
    pass


class RecordNotFoundError(CRUDException):
    """Raised when a requested record is not found in the database."""
    
    def __init__(self, model_name: str, identifier: any):
        self.model_name = model_name
        self.identifier = identifier
        super().__init__(f"{model_name} with identifier {identifier} not found")


class DuplicateRecordError(CRUDException):
    """Raised when attempting to create a record that violates unique constraints."""
    
    def __init__(self, model_name: str, field: str, value: any):
        self.model_name = model_name
        self.field = field
        self.value = value
        super().__init__(
            f"{model_name} with {field}='{value}' already exists"
        )


class DatabaseOperationError(CRUDException):
    """Raised when a database operation fails."""
    
    def __init__(self, operation: str, model_name: str, original_error: Exception):
        self.operation = operation
        self.model_name = model_name
        self.original_error = original_error
        super().__init__(
            f"Failed to {operation} {model_name}: {str(original_error)}"
        )


class TransactionError(CRUDException):
    """Raised when a transaction fails."""
    
    def __init__(self, message: str, original_error: Exception = None):
        self.original_error = original_error
        super().__init__(message)


class ValidationError(CRUDException):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation error for {field}: {message}")
