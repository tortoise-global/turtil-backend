from sqlalchemy import Column, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class CMSStaffPermission(UUIDBaseModel):
    """CMS Staff Permission model with UUID primary key for module-based access control"""

    __tablename__ = "cms_staff_permissions"

    # UUID Primary Key - descriptive and intuitive
    permission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Keys using UUIDs
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.staff_id"), nullable=False)

    # Permission Details
    module = Column(String(50), nullable=False)  # One of the 12 core modules
    read_access = Column(Boolean, default=False, nullable=False)
    write_access = Column(Boolean, default=False, nullable=False)
    scope = Column(String(50), default="college", nullable=False)  # 'college', 'department', 'section'

    # Relationships
    staff = relationship("Staff")

    # Ensure unique permission per staff per module
    __table_args__ = (
        UniqueConstraint("staff_id", "module", name="unique_staff_module_permission"),
    )

    def __repr__(self):
        return f"<CMSStaffPermission(permission_id={self.permission_id}, staff_id={self.staff_id}, module={self.module}, read={self.read_access}, write={self.write_access})>"

    def to_dict(self) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        return {
            "permissionId": base_dict["permission_id"],
            "staffId": base_dict["staff_id"],
            "module": base_dict["module"],
            "readAccess": base_dict["read_access"],
            "writeAccess": base_dict["write_access"],
            "scope": base_dict["scope"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }


# CMS Module Constants
class CMSModules:
    """CMS Module constants"""

    PROGRAMS_STRUCTURE = "programs_structure"
    STUDENTS = "students"
    LISTS = "lists"
    ALERTS = "alerts"
    TIMETABLE = "timetable"
    ATTENDANCE = "attendance"
    RESULTS = "results"
    ASSIGNMENTS = "assignments"
    ACADEMIC_CALENDAR = "academic_calendar"
    DOCUMENT_REQUEST = "document_request"
    EVENTS = "events"
    PLACEMENTS = "placements"

    ALL_MODULES = [
        PROGRAMS_STRUCTURE,
        STUDENTS,
        LISTS,
        ALERTS,
        TIMETABLE,
        ATTENDANCE,
        RESULTS,
        ASSIGNMENTS,
        ACADEMIC_CALENDAR,
        DOCUMENT_REQUEST,
        EVENTS,
        PLACEMENTS,
    ]

    # Modules that are always accessible (no permission check)
    ALWAYS_ACCESSIBLE = [PROGRAMS_STRUCTURE]


# CMS Role Constants
class CMSRoles:
    """CMS Role constants"""

    PRINCIPAL = "principal"
    ADMIN = "admin"
    HOD = "hod"
    STAFF = "staff"

    ALL_ROLES = [PRINCIPAL, ADMIN, HOD, STAFF]

    # Roles that can manage staff
    STAFF_MANAGEMENT_ROLES = [PRINCIPAL, ADMIN]

    # Roles that have full access
    FULL_ACCESS_ROLES = [PRINCIPAL, ADMIN]