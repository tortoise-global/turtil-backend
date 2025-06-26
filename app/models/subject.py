from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class Subject(UUIDBaseModel):
    """Subject model for course subjects - Level 4A in academic tree"""

    __tablename__ = "subjects"

    # UUID Primary Key
    subject_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Subject Details
    subject_name = Column(String(255), nullable=False)  # "Data Structures and Algorithms"
    subject_code = Column(String(20), nullable=False)  # "CS201", "MATH101"
    short_name = Column(String(100), nullable=False)  # "DSA", "Math-I"
    description = Column(Text, nullable=True)
    
    # Academic Details
    credits = Column(Integer, nullable=False, default=3)  # 3, 4, 2
    subject_type = Column(String(20), nullable=False, default="theory")  # "theory", "practical", "project", "elective"
    sequence_order = Column(Integer, nullable=False, default=1)  # For UI ordering

    # Foreign Keys
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.branch_id"), nullable=False)

    # Relationships
    branch = relationship("Branch", back_populates="subjects")
    section_subjects = relationship("SectionSubject", back_populates="subject", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('branch_id', 'subject_code', name='unique_branch_subject_code'),
        CheckConstraint('credits >= 1 AND credits <= 8', name='check_credits_range'),
        CheckConstraint("subject_type IN ('theory', 'practical', 'project', 'elective')", name='check_subject_type'),
    )

    def __repr__(self):
        return f"<Subject(subject_id={self.subject_id}, subject_name={self.subject_name})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        result = {
            "subjectId": base_dict["subject_id"],
            "subjectName": base_dict["subject_name"],
            "subjectCode": base_dict["subject_code"],
            "shortName": base_dict["short_name"],
            "description": base_dict["description"],
            "credits": base_dict["credits"],
            "subjectType": base_dict["subject_type"],
            "sequenceOrder": base_dict["sequence_order"],
            "branchId": base_dict["branch_id"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }
        return result