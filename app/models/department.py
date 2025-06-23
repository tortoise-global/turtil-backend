from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class Department(UUIDBaseModel):
    """Department model with UUID primary key for CMS system"""

    __tablename__ = "departments"

    # UUID Primary Key - descriptive and intuitive
    department_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Department Details
    name = Column(String(255), nullable=False)  # "Computer Science Department"
    code = Column(String(50), nullable=False)  # "CSE"
    description = Column(Text, nullable=True)

    # Foreign Keys using UUIDs
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.college_id"), nullable=False)
    head_staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.staff_id"), nullable=True)  # Head of Department

    # Relationships
    college = relationship("College", back_populates="departments")
    head = relationship("Staff", foreign_keys=[head_staff_id], post_update=True)
    staff_members = relationship("Staff", back_populates="department", foreign_keys="Staff.department_id")

    def __repr__(self):
        return f"<Department(department_id={self.department_id}, name={self.name}, college_id={self.college_id})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert to dictionary with camelCase for API responses.
        """
        base_dict = super().to_dict()
        result = {
            "departmentId": base_dict["department_id"],
            "name": base_dict["name"],
            "code": base_dict["code"],
            "description": base_dict["description"],
            "collegeId": base_dict["college_id"],
            "headStaffId": base_dict["head_staff_id"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }

        return result