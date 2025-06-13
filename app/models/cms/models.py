"""CMS database models.

This module contains SQLAlchemy ORM models for the College Management System including:
- College and user management models
- Academic structure models (departments, branches, degrees)
- Course and subject models
- Batch and section models
- Permission and role management models
- System module and configuration models
"""

import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


# Core models needed for user management and authentication
class College(Base):
    __tablename__ = "colleges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    college_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    short_name = Column(String(10), nullable=False)
    logo_url = Column(Text)
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    is_active = Column(Boolean, default=True)
    # Setting to control college visibility for student signup
    allow_student_signup = Column(Boolean, default=False)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )
    updated_at = Column(
        BigInteger,
        nullable=True,
        onupdate=func.extract("epoch", func.now()).cast(Integer),
    )

    cms_users = relationship("CMSUser", back_populates="college")
    departments = relationship("Department", back_populates="college")
    degrees = relationship("Degree", back_populates="college")
    college_modules = relationship("CMSCollegeModule", back_populates="college")
    college_settings = relationship("CMSCollegeSetting", back_populates="college")


class Degree(Base):
    __tablename__ = "degrees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)  # B.Tech, M.Tech, MBA
    duration_years = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    college = relationship("College", back_populates="degrees")
    branches = relationship("Branch", back_populates="degree")


class Department(Base):
    __tablename__ = "departments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)  # Computer Science Engineering
    short_name = Column(String(10))  # CSE
    head_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    college = relationship("College", back_populates="departments")
    branches = relationship("Branch", back_populates="department")
    cms_users = relationship("CMSUser", back_populates="department")


class Branch(Base):
    __tablename__ = "branches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    degree_id = Column(
        UUID(as_uuid=True), ForeignKey("degrees.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)  # Computer Science Engineering, AI/ML
    code = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    department = relationship("Department", back_populates="branches")
    degree = relationship("Degree", back_populates="branches")
    cms_users = relationship("CMSUser", back_populates="branch")


# User roles enum
cms_user_role = ENUM(
    "principal", "admin", "head", "staff", name="cms_user_role", create_type=False
)


class CMSUser(Base):
    __tablename__ = "cms_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=True,
    )
    username = Column(String(100), unique=True, nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20))
    role = Column(cms_user_role, nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id"))
    # Hierarchy management fields
    created_by = Column(UUID(as_uuid=True), ForeignKey("cms_users.id"))
    managed_departments = Column(JSON, default=list)  # For cross-department access
    teaching_subjects = Column(
        JSON, default=list
    )  # Subject IDs for cross-department teaching
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    profile_completed = Column(Boolean, default=False)
    last_login = Column(BigInteger)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )
    updated_at = Column(
        BigInteger,
        nullable=True,
        onupdate=func.extract("epoch", func.now()).cast(Integer),
    )

    college = relationship("College", back_populates="cms_users")
    department = relationship("Department", back_populates="cms_users")
    branch = relationship("Branch", back_populates="cms_users")
    degree = relationship("Degree")
    creator = relationship("CMSUser", remote_side=[id], back_populates="created_users")
    created_users = relationship("CMSUser", back_populates="creator")


# Module management for role-based access control
class CMSSystemModule(Base):
    __tablename__ = "cms_system_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_core = Column(Boolean, default=False)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    college_modules = relationship("CMSCollegeModule", back_populates="module")
    user_permissions = relationship("CMSUserModulePermission", back_populates="module")
    role_access = relationship("CMSRoleModuleAccess", back_populates="module")


class CMSCollegeModule(Base):
    __tablename__ = "cms_college_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    module_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_system_modules.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_enabled = Column(Boolean, default=True)
    configured_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    college = relationship("College", back_populates="college_modules")
    module = relationship("CMSSystemModule", back_populates="college_modules")


# Enhanced permission actions enum
cms_permission_action = ENUM(
    "read",
    "write",
    "delete",
    "manage",
    "export",
    "import",
    name="cms_permission_action",
    create_type=False,
)

# Access scope enum for department-level permissions
cms_access_scope = ENUM(
    "all",
    "college",
    "department",
    "branch",
    "self",
    name="cms_access_scope",
    create_type=False,
)


class CMSUserModulePermission(Base):
    __tablename__ = "cms_user_module_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    module_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_system_modules.id", ondelete="CASCADE"),
        nullable=False,
    )
    has_access = Column(Boolean, default=False)
    # Action-level permissions
    allowed_actions = Column(
        JSON, default=list
    )  # List of allowed actions ['read', 'write', etc.]
    # Scope-based access control
    access_scope = Column(cms_access_scope, default="self")
    # Department/branch restrictions
    restricted_departments = Column(JSON, default=list)  # List of department UUIDs
    restricted_branches = Column(JSON, default=list)  # List of branch UUIDs
    granted_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )
    updated_at = Column(
        BigInteger,
        nullable=True,
        onupdate=func.extract("epoch", func.now()).cast(Integer),
    )

    user = relationship("CMSUser")
    module = relationship("CMSSystemModule", back_populates="user_permissions")


class CMSRoleModuleAccess(Base):
    """Defines default module access patterns for each role"""

    __tablename__ = "cms_role_module_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(cms_user_role, nullable=False)
    module_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_system_modules.id", ondelete="CASCADE"),
        nullable=False,
    )
    default_access = Column(Boolean, default=False)
    default_actions = Column(
        JSON, default=list
    )  # Default actions for this role-module combination
    default_scope = Column(cms_access_scope, default="self")
    is_visible_in_role_creation = Column(
        Boolean, default=True
    )  # Whether shown when creating sub-accounts
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    module = relationship("CMSSystemModule", back_populates="role_access")


class CMSCollegeSetting(Base):
    __tablename__ = "cms_college_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    setting_key = Column(String(100), nullable=False)
    setting_value = Column(Text)
    data_type = Column(String(20), default="string")
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )
    updated_at = Column(
        BigInteger,
        nullable=True,
        onupdate=func.extract("epoch", func.now()).cast(Integer),
    )

    college = relationship("College", back_populates="college_settings")


# Academic Structure Models
class Batch(Base):
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
    )
    degree_id = Column(
        UUID(as_uuid=True), ForeignKey("degrees.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)  # 2024-CSE, 2023-IT
    year = Column(Integer, nullable=False)  # Academic year
    semester = Column(Integer, nullable=False)  # Current semester
    start_date = Column(BigInteger)
    end_date = Column(BigInteger)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    college = relationship("College")
    department = relationship("Department")
    branch = relationship("Branch")
    degree = relationship("Degree")
    sections = relationship("Section", back_populates="batch")


class Section(Base):
    __tablename__ = "sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(10), nullable=False)  # A, B, C
    capacity = Column(Integer, default=60)
    current_strength = Column(Integer, default=0)
    class_teacher_id = Column(UUID(as_uuid=True), ForeignKey("cms_users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    batch = relationship("Batch", back_populates="sections")
    class_teacher = relationship("CMSUser")
    timetable_entries = relationship("Timetable", back_populates="section")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id = Column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    code = Column(String(20), nullable=False)  # CS101, IT201
    credits = Column(Integer, default=3)
    semester = Column(Integer, nullable=False)
    subject_type = Column(String(20), default="theory")  # theory, lab, project
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    college = relationship("College")
    department = relationship("Department")
    timetable_entries = relationship("Timetable", back_populates="subject")


# Enum for timetable days
timetable_day = ENUM(
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    name="timetable_day",
    create_type=False,
)


class Timetable(Base):
    __tablename__ = "timetables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week = Column(timetable_day, nullable=False)
    start_time = Column(String(10), nullable=False)  # 09:00
    end_time = Column(String(10), nullable=False)  # 10:00
    room_number = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )

    college = relationship("College")
    section = relationship("Section", back_populates="timetable_entries")
    subject = relationship("Subject", back_populates="timetable_entries")
    teacher = relationship("CMSUser")
