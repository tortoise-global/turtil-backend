from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel
import uuid


class Department(BaseModel):
    """Department model for CMS system"""

    __tablename__ = "departments"

    # Use UUID for better security (separate from primary key)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # Department Details
    name = Column(String(255), nullable=False)  # "Computer Science Department"
    code = Column(String(50), nullable=False)  # "CSE"
    description = Column(Text, nullable=True)

    # Foreign Keys
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    hod_staff_id = Column(
        Integer, ForeignKey("staff.id"), nullable=True
    )  # Head of Department

    # Relationships (will be defined after creating other models)
    # college = relationship("College", back_populates="departments")
    # hod = relationship("Staff", foreign_keys=[hod_staff_id])
    # staff_members = relationship("Staff", back_populates="department")

    def __repr__(self):
        return f"<Department(id={self.id}, name={self.name}, college_id={self.college_id})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert to dictionary with camelCase for API responses.
        """
        base_dict = super().to_dict()
        result = {
            "id": base_dict["id"],
            "uuid": str(self.uuid),
            "name": base_dict["name"],
            "code": base_dict["code"],
            "description": base_dict["description"],
            "collegeId": base_dict["college_id"],
            "hodStaffId": base_dict["hod_staff_id"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }

        return result
