from sqlalchemy import Column, String, Boolean, JSON, BigInteger, Integer, Text, Date, Time, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid



class College(Base):
    __tablename__ = "colleges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    college_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    short_name = Column(String(10), nullable=False)
    logo_url = Column(Text)
    affiliated_university_name = Column(String(255))
    affiliated_university_short = Column(String(50))
    university_id = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    district = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    total_locations = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))

    cms_users = relationship("CMSUser", back_populates="college")
    departments = relationship("Department", back_populates="college")
    degrees = relationship("Degree", back_populates="college")


class CollegeLocation(Base):
    __tablename__ = "college_locations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    location_name = Column(String(100), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    district = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    is_main_campus = Column(Boolean, default=False)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")


class Degree(Base):
    __tablename__ = "degrees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # B.Tech, M.Tech, MBA
    duration_years = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College", back_populates="degrees")
    branches = relationship("Branch", back_populates="degree")


class Department(Base):
    __tablename__ = "departments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # Computer Science Engineering
    short_name = Column(String(10))  # CSE
    head_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College", back_populates="departments")
    branches = relationship("Branch", back_populates="department")
    cms_users = relationship("CMSUser", back_populates="department")


class Branch(Base):
    __tablename__ = "branches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # Computer Science Engineering, AI/ML
    code = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    department = relationship("Department", back_populates="branches")
    degree = relationship("Degree", back_populates="branches")
    subjects = relationship("Subject", back_populates="branch")
    cms_users = relationship("CMSUser", back_populates="branch")


class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    subject_code = Column(String(20), nullable=False)
    subject_name = Column(String(255), nullable=False)
    semester = Column(Integer)
    credits = Column(Integer, default=0)
    is_core = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    branch = relationship("Branch", back_populates="subjects")



cms_user_role = ENUM(
    'super_admin',
    'department_admin', 
    'lecturer',
    'staff_admin',
    name='cms_user_role',
    create_type=False
)

class CMSUser(Base):
    __tablename__ = "cms_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    role = Column(cms_user_role, nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id"))
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    last_login = Column(BigInteger)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College", back_populates="cms_users")
    department = relationship("Department", back_populates="cms_users")
    branch = relationship("Branch", back_populates="cms_users")
    degree = relationship("Degree")


class CMSSystemModule(Base):
    __tablename__ = "cms_system_modules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_core = Column(Boolean, default=False)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college_modules = relationship("CMSCollegeModule", back_populates="module")
    user_permissions = relationship("CMSUserModulePermission", back_populates="module")


class CMSCollegeModule(Base):
    __tablename__ = "cms_college_modules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey("cms_system_modules.id", ondelete="CASCADE"), nullable=False)
    is_enabled = Column(Boolean, default=True)
    configured_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    module = relationship("CMSSystemModule", back_populates="college_modules")


class CMSUserModulePermission(Base):
    __tablename__ = "cms_user_module_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("cms_users.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey("cms_system_modules.id", ondelete="CASCADE"), nullable=False)
    has_access = Column(Boolean, default=False)
    granted_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    user = relationship("CMSUser")
    module = relationship("CMSSystemModule", back_populates="user_permissions")


class CMSCollegeSetting(Base):
    __tablename__ = "cms_college_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    setting_key = Column(String(100), nullable=False)
    setting_value = Column(Text)
    data_type = Column(String(20), default='string')
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")


class CMSFacultySubjectAssignment(Base):
    __tablename__ = "cms_faculty_subject_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("cms_users.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    academic_year = Column(Integer)
    semester = Column(Integer)
    assigned_date = Column(Date, default=func.current_date())
    is_active = Column(Boolean, default=True)

    user = relationship("CMSUser")
    subject = relationship("Subject")


cms_day_of_week = ENUM(
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    name='cms_day_of_week',
    create_type=False
)

class CMSTimetableSlot(Base):
    __tablename__ = "cms_timetable_slots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"))
    faculty_id = Column(UUID(as_uuid=True), ForeignKey("cms_users.id"))
    semester = Column(Integer)
    day_of_week = Column(cms_day_of_week)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room_number = Column(String(50))
    academic_year = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    branch = relationship("Branch")
    subject = relationship("Subject")
    faculty = relationship("CMSUser")


class CMSAttendanceSession(Base):
    __tablename__ = "cms_attendance_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(UUID(as_uuid=True), ForeignKey("cms_users.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    semester = Column(Integer)
    session_date = Column(Date, nullable=False)
    session_time = Column(Time)
    session_type = Column(String(50), default='regular')
    total_classes = Column(Integer, default=1)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    subject = relationship("Subject")
    faculty = relationship("CMSUser")
    branch = relationship("Branch")


cms_assignment_status = ENUM(
    'draft', 'published', 'closed',
    name='cms_assignment_status',
    create_type=False
)

class CMSAssignment(Base):
    __tablename__ = "cms_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(UUID(as_uuid=True), ForeignKey("cms_users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    assignment_type = Column(String(50), default='homework')
    due_date = Column(BigInteger)
    max_marks = Column(Integer, default=0)
    status = Column(cms_assignment_status, default='draft')
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    subject = relationship("Subject")
    faculty = relationship("CMSUser")


class CMSExamination(Base):
    __tablename__ = "cms_examinations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    exam_name = Column(String(255), nullable=False)
    exam_type = Column(String(50))  # mid_term, final, assignment
    academic_year = Column(Integer)
    semester = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")


cms_event_type = ENUM(
    'academic', 'cultural', 'sports', 'placement', 'seminar', 'workshop',
    name='cms_event_type',
    create_type=False
)

class CMSEvent(Base):
    __tablename__ = "cms_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    event_type = Column(cms_event_type)
    start_datetime = Column(BigInteger)
    end_datetime = Column(BigInteger)
    location = Column(String(255))
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("cms_users.id"))
    max_participants = Column(Integer)
    registration_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    organizer = relationship("CMSUser")


class CMSCompany(Base):
    __tablename__ = "cms_companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    website = Column(String(255))
    industry = Column(String(100))
    location = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))


class CMSPlacementDrive(Base):
    __tablename__ = "cms_placement_drives"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("cms_companies.id", ondelete="CASCADE"), nullable=False)
    position_title = Column(String(255), nullable=False)
    job_description = Column(Text)
    eligibility_criteria = Column(Text)
    package_offered = Column(String(100))
    drive_date = Column(Date)
    application_deadline = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    company = relationship("CMSCompany")


cms_notification_type = ENUM(
    'info', 'warning', 'success', 'error',
    name='cms_notification_type',
    create_type=False
)

cms_notification_target = ENUM(
    'all', 'students', 'faculty', 'department', 'branch',
    name='cms_notification_target',
    create_type=False
)

class CMSNotification(Base):
    __tablename__ = "cms_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(cms_notification_type, default='info')
    target_audience = Column(cms_notification_target, default='all')
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("cms_users.id"))
    is_active = Column(Boolean, default=True)
    expires_at = Column(BigInteger)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    department = relationship("Department")
    branch = relationship("Branch")
    creator = relationship("CMSUser")


cms_document_status = ENUM(
    'pending', 'processing', 'ready', 'delivered', 'rejected',
    name='cms_document_status',
    create_type=False
)

class CMSDocumentRequest(Base):
    __tablename__ = "cms_document_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), nullable=False)  # References student app
    document_type = Column(String(100), nullable=False)
    purpose = Column(String(255))
    status = Column(cms_document_status, default='pending')
    requested_date = Column(Date, default=func.current_date())
    expected_delivery = Column(Date)
    processed_by = Column(UUID(as_uuid=True), ForeignKey("cms_users.id"))
    remarks = Column(Text)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    processor = relationship("CMSUser")



