from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class Graduation(UUIDBaseModel):
    """Graduation model for graduation levels (UG, PG, etc.) - Level 1 in academic tree"""

    __tablename__ = "graduations"

    # UUID Primary Key
    graduation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Graduation Details
    graduation_name = Column(String(255), nullable=False)  # "Undergraduate", "Postgraduate"
    graduation_code = Column(String(20), nullable=False)  # "UG", "PG", "DIP"
    description = Column(Text, nullable=True)
    sequence_order = Column(Integer, nullable=False, default=1)  # For UI ordering

    # Foreign Keys
    term_id = Column(UUID(as_uuid=True), ForeignKey("terms.term_id"), nullable=False)

    # Relationships
    term = relationship("Term", back_populates="graduations")
    degrees = relationship("Degree", back_populates="graduation", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('term_id', 'graduation_code', name='unique_term_graduation_code'),
    )

    def __repr__(self):
        return f"<Graduation(graduation_id={self.graduation_id}, graduation_name={self.graduation_name})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        result = {
            "graduationId": base_dict["graduation_id"],
            "graduationName": base_dict["graduation_name"],
            "graduationCode": base_dict["graduation_code"],
            "description": base_dict["description"],
            "sequenceOrder": base_dict["sequence_order"],
            "termId": base_dict["term_id"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }
        return result