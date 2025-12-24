"""
Base CRUD repository class with common database operations.

This module provides a generic base class for CRUD operations that can be
extended by model-specific repository classes.
"""

from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select, func

from app.db.base import Base
from app.crud.exceptions import (
    RecordNotFoundError,
    DuplicateRecordError,
    DatabaseOperationError,
)

# Configure logging
logger = logging.getLogger(__name__)

# Generic type variable for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """
    Base class for CRUD operations.
    
    This class provides common database operations that can be inherited
    by model-specific repository classes.
    
    Type Parameters:
        ModelType: The SQLAlchemy model class this repository manages
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize CRUD object with model class.
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
        self.model_name = model.__name__
    
    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """
        Get a single record by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Model instance if found, None otherwise
            
        Raises:
            DatabaseOperationError: If database operation fails
        """
        try:
            logger.debug(f"Getting {self.model_name} with id={id}")
            result = db.execute(
                select(self.model).where(self.model.id == id)
            )
            obj = result.scalar_one_or_none()
            
            if obj:
                logger.debug(f"Found {self.model_name} with id={id}")
            else:
                logger.debug(f"{self.model_name} with id={id} not found")
            
            return obj
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_name} with id={id}: {e}")
            raise DatabaseOperationError("get", self.model_name, e)
    
    def get_or_404(self, db: Session, id: int) -> ModelType:
        """
        Get a single record by ID or raise RecordNotFoundError.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Model instance
            
        Raises:
            RecordNotFoundError: If record not found
            DatabaseOperationError: If database operation fails
        """
        obj = self.get(db, id)
        if obj is None:
            logger.warning(f"{self.model_name} with id={id} not found")
            raise RecordNotFoundError(self.model_name, id)
        return obj
    
    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50
    ) -> List[ModelType]:
        """
        Get multiple records with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            
        Returns:
            List of model instances
            
        Raises:
            DatabaseOperationError: If database operation fails
        """
        try:
            logger.debug(
                f"Getting {self.model_name} records with skip={skip}, limit={limit}"
            )
            result = db.execute(
                select(self.model).offset(skip).limit(limit)
            )
            objects = result.scalars().all()
            logger.debug(f"Found {len(objects)} {self.model_name} records")
            return list(objects)
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_name} records: {e}")
            raise DatabaseOperationError("get_multi", self.model_name, e)
    
    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Dictionary of field values
            
        Returns:
            Created model instance
            
        Raises:
            DuplicateRecordError: If unique constraint is violated
            DatabaseOperationError: If database operation fails
        """
        try:
            logger.debug(f"Creating {self.model_name} with data: {obj_in}")
            db_obj = self.model(**obj_in)
            db.add(db_obj)
            db.flush()  # Flush to get the ID without committing
            db.refresh(db_obj)
            logger.info(f"Created {self.model_name} with id={db_obj.id}")
            return db_obj
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Integrity error creating {self.model_name}: {e}")
            # Try to extract field name from error message
            error_msg = str(e.orig)
            if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
                # Extract field name if possible
                field = "unknown"
                if hasattr(e.orig, 'diag') and hasattr(e.orig.diag, 'constraint_name'):
                    field = e.orig.diag.constraint_name
                raise DuplicateRecordError(self.model_name, field, "value")
            raise DatabaseOperationError("create", self.model_name, e)
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating {self.model_name}: {e}")
            raise DatabaseOperationError("create", self.model_name, e)
    
    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """
        Update an existing record.
        
        Args:
            db: Database session
            db_obj: Existing model instance to update
            obj_in: Dictionary of fields to update
            
        Returns:
            Updated model instance
            
        Raises:
            DatabaseOperationError: If database operation fails
        """
        try:
            logger.debug(
                f"Updating {self.model_name} id={db_obj.id} with data: {obj_in}"
            )
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            db.add(db_obj)
            db.flush()
            db.refresh(db_obj)
            logger.info(f"Updated {self.model_name} with id={db_obj.id}")
            return db_obj
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error updating {self.model_name} id={db_obj.id}: {e}")
            raise DatabaseOperationError("update", self.model_name, e)
    
    def delete(self, db: Session, *, id: int) -> ModelType:
        """
        Delete a record by ID.
        
        Args:
            db: Database session
            id: Record ID to delete
            
        Returns:
            Deleted model instance
            
        Raises:
            RecordNotFoundError: If record not found
            DatabaseOperationError: If database operation fails
        """
        try:
            logger.debug(f"Deleting {self.model_name} with id={id}")
            obj = self.get_or_404(db, id)
            db.delete(obj)
            db.flush()
            logger.info(f"Deleted {self.model_name} with id={id}")
            return obj
        except RecordNotFoundError:
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error deleting {self.model_name} id={id}: {e}")
            raise DatabaseOperationError("delete", self.model_name, e)
    
    def count(self, db: Session) -> int:
        """
        Count total number of records.
        
        Args:
            db: Database session
            
        Returns:
            Total count of records
            
        Raises:
            DatabaseOperationError: If database operation fails
        """
        try:
            logger.debug(f"Counting {self.model_name} records")
            result = db.execute(select(func.count()).select_from(self.model))
            count = result.scalar()
            logger.debug(f"Total {self.model_name} count: {count}")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model_name} records: {e}")
            raise DatabaseOperationError("count", self.model_name, e)
