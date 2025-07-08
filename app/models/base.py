from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from app.database import Base
from datetime import datetime, timezone
import uuid


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

    @declared_attr
    def created_at(cls):
        return Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
        )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""

    @declared_attr
    def is_deleted(cls):
        return Column(Boolean, default=False, nullable=False)

    @declared_attr
    def deleted_at(cls):
        return Column(DateTime(timezone=True), nullable=True)

    def soft_delete(self):
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)


class UUIDBaseModel(Base, TimestampMixin):
    """
    Base model class with UUID primary keys and descriptive naming.
    Clean implementation without legacy integer IDs.
    """

    __abstract__ = True

    def to_dict(self) -> dict:
        """Convert model instance to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                # Convert datetime to ISO format
                result[column.name] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                # Convert UUID to string
                result[column.name] = str(value)
            else:
                result[column.name] = value
        return result

    def update_from_dict(self, data: dict) -> None:
        """Update model instance from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def get_column_names(cls) -> list:
        """Get list of column names for this model"""
        return [column.name for column in cls.__table__.columns]

    def __repr__(self) -> str:
        """String representation of the model"""
        class_name = self.__class__.__name__
        # Get the primary key field name (should be descriptive like staff_id, college_id)
        primary_key_column = None
        for column in self.__table__.columns:
            if column.primary_key:
                primary_key_column = column.name
                break
        
        if primary_key_column:
            primary_key_value = getattr(self, primary_key_column, None)
            return f"<{class_name}({primary_key_column}={primary_key_value})>"
        else:
            return f"<{class_name}()>"


class UUIDSoftDeleteModel(UUIDBaseModel, SoftDeleteMixin):
    """Base model with UUID primary keys and soft delete functionality"""

    __abstract__ = True


# Legacy BaseModel - DEPRECATED, use UUIDBaseModel for new models
class BaseModel(Base, TimestampMixin):
    """
    DEPRECATED: Legacy base model with integer primary keys.
    Use UUIDBaseModel for all new models.
    """

    __abstract__ = True

    # This will be removed in the migration
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    def to_dict(self) -> dict:
        """Convert model instance to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    def update_from_dict(self, data: dict) -> None:
        """Update model instance from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def get_column_names(cls) -> list:
        """Get list of column names for this model"""
        return [column.name for column in cls.__table__.columns]

    def __repr__(self) -> str:
        """String representation of the model"""
        class_name = self.__class__.__name__
        primary_key = getattr(self, "id", None)
        return f"<{class_name}(id={primary_key})>"


class SoftDeleteBaseModel(BaseModel, SoftDeleteMixin):
    """DEPRECATED: Legacy base model with soft delete functionality"""

    __abstract__ = True