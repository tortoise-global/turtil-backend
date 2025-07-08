from sqlalchemy import Column, String, Integer, Boolean, Date, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class Term(UUIDBaseModel):
    """Term model for academic programs - Root of the academic tree"""

    __tablename__ = "terms"

    # UUID Primary Key
    term_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Term Details
    batch_year = Column(Integer, nullable=False, index=True)  # 2025, 2026, 2027
    current_year = Column(Integer, nullable=False, index=True)  # 1, 2, 3, 4
    current_semester = Column(Integer, nullable=False, index=True)  # 1, 2
    
    # Auto-generated fields
    term_name = Column(String(255), nullable=False)  # "Batch 2025 - Year 1 - Semester 1"
    term_code = Column(String(50), nullable=False, index=True)  # "2025-Y1-S1"
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_ongoing = Column(Boolean, default=False, nullable=False)  # Has attached resources
    
    # Timeline
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Foreign Keys
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.college_id"), nullable=False)

    # Relationships
    college = relationship("College", back_populates="terms")
    graduations = relationship("Graduation", back_populates="term", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        UniqueConstraint('college_id', 'batch_year', 'current_year', 'current_semester', 
                        name='unique_college_term'),
        CheckConstraint('current_year >= 1 AND current_year <= 4', name='check_current_year'),
        CheckConstraint('current_semester >= 1 AND current_semester <= 2', name='check_current_semester'),
        CheckConstraint('batch_year >= 2020 AND batch_year <= 2050', name='check_batch_year'),
        CheckConstraint('end_date > start_date', name='check_date_order'),
    )

    def __repr__(self):
        return f"<Term(term_id={self.term_id}, term_name={self.term_name})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        result = {
            "termId": base_dict["term_id"],
            "batchYear": base_dict["batch_year"],
            "currentYear": base_dict["current_year"],
            "currentSemester": base_dict["current_semester"],
            "termName": base_dict["term_name"],
            "termCode": base_dict["term_code"],
            "isActive": base_dict["is_active"],
            "isOngoing": base_dict["is_ongoing"],
            "startDate": base_dict["start_date"],
            "endDate": base_dict["end_date"],
            "collegeId": base_dict["college_id"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }
        return result

    def generate_term_metadata(self):
        """Generate term_name and term_code automatically"""
        self.term_name = f"Batch {self.batch_year} - Year {self.current_year} - Semester {self.current_semester}"
        self.term_code = f"{self.batch_year}-Y{self.current_year}-S{self.current_semester}"