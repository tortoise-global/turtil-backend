from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class Section(UUIDBaseModel):
    """Section model for class divisions - Level 4B in academic tree"""

    __tablename__ = "sections"

    # UUID Primary Key
    section_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Section Details
    section_name = Column(String(100), nullable=False)  # "Section A", "Section B"
    section_code = Column(String(10), nullable=False)  # "A", "B", "C"
    description = Column(Text, nullable=True)
    
    # Capacity Management
    student_capacity = Column(Integer, nullable=False, default=60)
    current_strength = Column(Integer, nullable=False, default=0)  # For future student assignments
    sequence_order = Column(Integer, nullable=False, default=1)  # For UI ordering

    # Foreign Keys
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id"), nullable=False)
    class_teacher_id = Column(UUID(as_uuid=True), ForeignKey("staff.staff_id"), nullable=True)  # Optional

    # Relationships
    branch = relationship("Branch", back_populates="sections")
    class_teacher = relationship("Staff", foreign_keys=[class_teacher_id])
    section_subjects = relationship("SectionSubject", back_populates="section", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('branch_id', 'section_code', name='unique_branch_section_code'),
        CheckConstraint('student_capacity >= 1 AND student_capacity <= 200', name='check_student_capacity'),
        CheckConstraint('current_strength >= 0', name='check_current_strength'),
        CheckConstraint('current_strength <= student_capacity', name='check_strength_within_capacity'),
    )

    def __repr__(self):
        return f"<Section(section_id={self.section_id}, section_name={self.section_name})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        result = {
            "sectionId": base_dict["section_id"],
            "sectionName": base_dict["section_name"],
            "sectionCode": base_dict["section_code"],
            "description": base_dict["description"],
            "studentCapacity": base_dict["student_capacity"],
            "currentStrength": base_dict["current_strength"],
            "sequenceOrder": base_dict["sequence_order"],
            "branchId": base_dict["branch_id"],
            "classTeacherId": base_dict["class_teacher_id"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }
        return result