from sqlalchemy import Column, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class SectionSubject(UUIDBaseModel):
    """SectionSubject model for many-to-many relationship between sections and subjects"""

    __tablename__ = "section_subjects"

    # UUID Primary Key
    section_subject_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Assignment Details
    is_active = Column(Boolean, default=True, nullable=False)

    # Foreign Keys
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.section_id"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.subject_id"), nullable=False)
    assigned_staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.staff_id"), nullable=True)  # Optional teacher

    # Relationships
    section = relationship("Section", back_populates="section_subjects")
    subject = relationship("Subject", back_populates="section_subjects")
    assigned_staff = relationship("Staff", foreign_keys=[assigned_staff_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('section_id', 'subject_id', name='unique_section_subject'),
    )

    def __repr__(self):
        return f"<SectionSubject(section_subject_id={self.section_subject_id}, section_id={self.section_id}, subject_id={self.subject_id})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        result = {
            "sectionSubjectId": base_dict["section_subject_id"],
            "sectionId": base_dict["section_id"],
            "subjectId": base_dict["subject_id"],
            "assignedStaffId": base_dict["assigned_staff_id"],
            "isActive": base_dict["is_active"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }
        return result