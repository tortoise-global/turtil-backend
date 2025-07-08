from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class Branch(UUIDBaseModel):
    """Branch model for specializations (CSE, ME, etc.) - Level 3 in academic tree"""

    __tablename__ = "branches"

    # UUID Primary Key
    branch_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Branch Details
    branch_name = Column(String(255), nullable=False)  # "Computer Science Engineering"
    branch_code = Column(String(20), nullable=False)  # "CSE", "ME", "ECE"
    short_name = Column(String(100), nullable=False)  # "Computer Science"
    description = Column(Text, nullable=True)
    sequence_order = Column(Integer, nullable=False, default=1)  # For UI ordering

    # Foreign Keys
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.degree_id"), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.department_id"), nullable=False)

    # Relationships
    degree = relationship("Degree", back_populates="branches")
    department = relationship("Department")  # Link to existing Department model
    subjects = relationship("Subject", back_populates="branch", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="branch", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('degree_id', 'branch_code', name='unique_degree_branch_code'),
    )

    def __repr__(self):
        return f"<Branch(branch_id={self.branch_id}, branch_name={self.branch_name})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        result = {
            "branchId": base_dict["branch_id"],
            "branchName": base_dict["branch_name"],
            "branchCode": base_dict["branch_code"],
            "shortName": base_dict["short_name"],
            "description": base_dict["description"],
            "sequenceOrder": base_dict["sequence_order"],
            "degreeId": base_dict["degree_id"],
            "departmentId": base_dict["department_id"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }
        return result