"""Base service class with common functionality.

This module provides a base service class that includes:
- Database session management
- Common CRUD operations
- Error handling
- Logging
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService:
    """Base service class with common CRUD operations."""

    def __init__(self, model: Type[ModelType]):
        """Initialize the service with a model.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model
        self.logger = logging.getLogger(self.__class__.__name__)

    def get(self, db: Session, id: UUID) -> Optional[ModelType]:
        """Get a single record by ID.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Model instance or None
        """
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting {self.model.__name__} with id {id}: {e}")
            raise

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        """Get multiple records with pagination and filtering.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field: value filters

        Returns:
            List of model instances
        """
        try:
            query = db.query(self.model)

            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)

            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting {self.model.__name__} records: {e}")
            raise

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record.

        Args:
            db: Database session
            obj_in: Pydantic model with creation data

        Returns:
            Created model instance
        """
        try:
            obj_data = obj_in.model_dump()

            # Hash password if present
            if "password" in obj_data:
                obj_data["password_hash"] = get_password_hash(obj_data.pop("password"))

            db_obj = self.model(**obj_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            self.logger.info(f"Created {self.model.__name__} with id {db_obj.id}")
            return db_obj

        except IntegrityError as e:
            db.rollback()
            self.logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise ValueError("Record already exists or violates constraints")
        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Error creating {self.model.__name__}: {e}")
            raise

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType,
    ) -> ModelType:
        """Update an existing record.

        Args:
            db: Database session
            db_obj: Existing model instance
            obj_in: Pydantic model with update data

        Returns:
            Updated model instance
        """
        try:
            obj_data = obj_in.model_dump(exclude_unset=True)

            # Hash password if present
            if "password" in obj_data:
                obj_data["password_hash"] = get_password_hash(obj_data.pop("password"))

            for field, value in obj_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            db.commit()
            db.refresh(db_obj)

            self.logger.info(f"Updated {self.model.__name__} with id {db_obj.id}")
            return db_obj

        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Error updating {self.model.__name__}: {e}")
            raise

    def remove(self, db: Session, *, id: UUID) -> ModelType:
        """Delete a record by ID.

        Args:
            db: Database session
            id: Record ID

        Returns:
            Deleted model instance
        """
        try:
            obj = db.query(self.model).get(id)
            if obj:
                db.delete(obj)
                db.commit()
                self.logger.info(f"Deleted {self.model.__name__} with id {id}")
                return obj
            return None

        except SQLAlchemyError as e:
            db.rollback()
            self.logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise

    def exists(self, db: Session, *, id: UUID) -> bool:
        """Check if a record exists.

        Args:
            db: Database session
            id: Record ID

        Returns:
            True if record exists, False otherwise
        """
        try:
            return db.query(self.model).filter(self.model.id == id).first() is not None
        except SQLAlchemyError as e:
            self.logger.error(f"Error checking existence of {self.model.__name__}: {e}")
            raise

    def count(self, db: Session, *, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filtering.

        Args:
            db: Database session
            filters: Dictionary of field: value filters

        Returns:
            Number of matching records
        """
        try:
            query = db.query(self.model)

            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)

            return query.count()
        except SQLAlchemyError as e:
            self.logger.error(f"Error counting {self.model.__name__} records: {e}")
            raise
