from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, UniqueConstraint
from app.models.base import BaseModel


class CMSStaffPermission(BaseModel):
    """CMS Staff Permission model for module-based access control"""

    __tablename__ = "cms_staff_permissions"

    # Foreign Keys
    cms_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)

    # Permission Details
    module = Column(String(50), nullable=False)  # One of the 12 core modules
    read_access = Column(Boolean, default=False, nullable=False)
    write_access = Column(Boolean, default=False, nullable=False)
    scope = Column(
        String(50), default="college", nullable=False
    )  # 'college', 'department', 'section'

    # Ensure unique permission per staff per module
    __table_args__ = (
        UniqueConstraint("cms_staff_id", "module", name="unique_staff_module_permission"),
    )

    def __repr__(self):
        return f"<CMSStaffPermission(cms_staff_id={self.cms_staff_id}, module={self.module}, read={self.read_access}, write={self.write_access})>"

    def to_dict(self) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        return {
            "id": base_dict["id"],
            "cmsStaffId": base_dict["cms_staff_id"],
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
    COLLEGE_ADMIN = "college_admin"
    HOD = "hod"
    STAFF = "staff"

    ALL_ROLES = [PRINCIPAL, COLLEGE_ADMIN, HOD, STAFF]

    # Roles that can manage staff
    STAFF_MANAGEMENT_ROLES = [PRINCIPAL, COLLEGE_ADMIN]

    # Roles that have full access
    FULL_ACCESS_ROLES = [PRINCIPAL, COLLEGE_ADMIN]
