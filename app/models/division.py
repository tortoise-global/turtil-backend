from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class Division(UUIDBaseModel):
    """Division model for organizing departments within a college"""

    __tablename__ = "divisions"

    # UUID Primary Key - descriptive and intuitive
    division_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Division Details
    name = Column(String(255), nullable=False)  # "Engineering", "Management", "Arts"
    code = Column(String(50), nullable=False)   # "ENG", "MGMT", "ARTS"
    description = Column(Text, nullable=True)

    # Foreign Keys using UUIDs
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.college_id"), nullable=False)

    # Relationships
    college = relationship("College", back_populates="divisions")
    departments = relationship("Department", back_populates="division", cascade="all, delete-orphan")
    staff_members = relationship("Staff", back_populates="division", foreign_keys="Staff.division_id")

    def __repr__(self):
        return f"<Division(division_id={self.division_id}, name={self.name}, college_id={self.college_id})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert to dictionary with camelCase for API responses.
        """
        base_dict = super().to_dict()
        result = {
            "divisionId": base_dict["division_id"],
            "name": base_dict["name"],
            "code": base_dict["code"],
            "description": base_dict["description"],
            "collegeId": base_dict["college_id"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }

        return result