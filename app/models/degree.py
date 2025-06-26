from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class Degree(UUIDBaseModel):
    """Degree model for degree programs (B.Tech, M.Tech, etc.) - Level 2 in academic tree"""

    __tablename__ = "degrees"

    # UUID Primary Key
    degree_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Degree Details
    degree_name = Column(String(255), nullable=False)  # "Bachelor of Technology"
    degree_code = Column(String(20), nullable=False)  # "BTECH", "MTECH", "MBA"
    short_name = Column(String(50), nullable=False)  # "B.Tech", "M.Tech", "MBA"
    description = Column(Text, nullable=True)
    sequence_order = Column(Integer, nullable=False, default=1)  # For UI ordering

    # Foreign Keys
    graduation_id = Column(UUID(as_uuid=True), ForeignKey("graduations.graduation_id"), nullable=False)

    # Relationships
    graduation = relationship("Graduation", back_populates="degrees")
    branches = relationship("Branch", back_populates="degree", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('graduation_id', 'degree_code', name='unique_graduation_degree_code'),
    )

    def __repr__(self):
        return f"<Degree(degree_id={self.degree_id}, degree_name={self.degree_name})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        result = {
            "degreeId": base_dict["degree_id"],
            "degreeName": base_dict["degree_name"],
            "degreeCode": base_dict["degree_code"],
            "shortName": base_dict["short_name"],
            "description": base_dict["description"],
            "sequenceOrder": base_dict["sequence_order"],
            "graduationId": base_dict["graduation_id"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }
        return result