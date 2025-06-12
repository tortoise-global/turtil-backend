from sqlalchemy import Column, String, Boolean, JSON, BigInteger, Integer, Text, Date, Time, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

from app.models.cms.models import (
    College, Department, Branch, Degree, Subject, CMSUser
)



student_user_role = ENUM(
    'student',
    name='student_user_role',
    create_type=False
)

class StudentUser(Base):
    __tablename__ = "student_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    role = Column(student_user_role, default='student')
    student_id = Column(String(50), unique=True, nullable=False)
    roll_number = Column(String(50))
    admission_number = Column(String(50))
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id"))
    batch_year = Column(Integer)
    current_semester = Column(Integer)
    admission_date = Column(Date)
    graduation_date = Column(Date)
    profile_image_url = Column(Text)
    guardian_name = Column(String(255))
    guardian_phone = Column(String(20))
    emergency_contact = Column(String(20))
    blood_group = Column(String(5))
    date_of_birth = Column(Date)
    gender = Column(String(10))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    last_login = Column(BigInteger)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))

    college = relationship("College")
    department = relationship("Department")
    branch = relationship("Branch") 
    degree = relationship("Degree")
    # attendance_records = relationship("StudentAttendance", back_populates="student")
    # assignment_submissions = relationship("StudentAssignmentSubmission", back_populates="student")
    # results = relationship("StudentResult", back_populates="student")
    # placements = relationship("StudentPlacement", back_populates="student")
    # notifications = relationship("StudentNotification", back_populates="student")
    # event_registrations = relationship("StudentEventRegistration", back_populates="student")
    # timetable_preferences = relationship("StudentTimetablePreference", back_populates="student")


# class StudentAttendance(Base):
#     __tablename__ = "student_attendance"
    
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     session_id = Column(UUID(as_uuid=True), ForeignKey("cms_attendance_sessions.id", ondelete="CASCADE"), nullable=False)
#     student_id = Column(UUID(as_uuid=True), ForeignKey("student_users.id", ondelete="CASCADE"), nullable=False)
#     is_present = Column(Boolean, nullable=False)
#     marked_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
#     marked_by = Column(UUID(as_uuid=True), ForeignKey("cms_users.id"))

#     session = relationship("CMSAttendanceSession")
#     student = relationship("StudentUser", back_populates="attendance_records")
#     marker = relationship("CMSUser")


# class StudentAssignmentSubmission(Base):
    __tablename__ = "student_assignment_submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("cms_assignments.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student_users.id", ondelete="CASCADE"), nullable=False)
    submission_text = Column(Text)
    file_urls = Column(JSON)  # Array of file URLs
    submitted_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    marks_awarded = Column(Integer)
    feedback = Column(Text)
    graded_by = Column(UUID(as_uuid=True), ForeignKey("cms_users.id"))
    graded_at = Column(BigInteger)

    assignment = relationship("CMSAssignment")
    student = relationship("StudentUser", back_populates="assignment_submissions")
    grader = relationship("CMSUser")


class StudentResult(Base):
    __tablename__ = "student_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    examination_id = Column(UUID(as_uuid=True), ForeignKey("cms_examinations.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student_users.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    marks_obtained = Column(DECIMAL(5, 2))
    max_marks = Column(DECIMAL(5, 2))
    grade = Column(String(5))
    is_pass = Column(Boolean)
    remarks = Column(Text)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    examination = relationship("CMSExamination")
    student = relationship("StudentUser", back_populates="results")
    subject = relationship("Subject")


class StudentPlacement(Base):
    __tablename__ = "student_placements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student_users.id", ondelete="CASCADE"), nullable=False)
    placement_drive_id = Column(UUID(as_uuid=True), ForeignKey("cms_placement_drives.id", ondelete="CASCADE"), nullable=False)
    application_date = Column(Date, default=func.current_date())
    status = Column(String(50), default='applied')  # applied, shortlisted, selected, rejected
    interview_date = Column(Date)
    feedback = Column(Text)
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))

    student = relationship("StudentUser", back_populates="placements")
    placement_drive = relationship("CMSPlacementDrive")


class StudentNotification(Base):
    __tablename__ = "student_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), ForeignKey("cms_notifications.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student_users.id", ondelete="CASCADE"), nullable=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(BigInteger)

    notification = relationship("CMSNotification")
    student = relationship("StudentUser", back_populates="notifications")


class StudentEventRegistration(Base):
    __tablename__ = "student_event_registrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("cms_events.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student_users.id", ondelete="CASCADE"), nullable=False)
    registration_date = Column(Date, default=func.current_date())
    attendance_status = Column(String(20), default='registered')  # registered, attended, absent
    remarks = Column(Text)

    event = relationship("CMSEvent")
    student = relationship("StudentUser", back_populates="event_registrations")


class StudentTimetablePreference(Base):
    __tablename__ = "student_timetable_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student_users.id", ondelete="CASCADE"), nullable=False)
    timetable_slot_id = Column(UUID(as_uuid=True), ForeignKey("cms_timetable_slots.id", ondelete="CASCADE"), nullable=False)
    is_bookmarked = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    student = relationship("StudentUser", back_populates="timetable_preferences")
    timetable_slot = relationship("CMSTimetableSlot")


# =============================================
# STUDENT APP VIEWS AND UTILITIES
# =============================================

class StudentDashboard(Base):
    """
    View-like model for student dashboard data aggregation
    This can be used for efficient queries combining multiple tables
    """
    __tablename__ = "student_dashboard_view"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("student_users.id"), nullable=False)
    total_attendance_percentage = Column(DECIMAL(5, 2))
    pending_assignments = Column(Integer, default=0)
    upcoming_events = Column(Integer, default=0)
    unread_notifications = Column(Integer, default=0)
    current_semester_gpa = Column(DECIMAL(4, 2))
    last_updated = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))

    student = relationship("StudentUser")


# =============================================
# STUDENT APP SPECIFIC FUNCTIONS
# =============================================

def get_student_by_student_id(db, student_id: str, college_id: str = None):
    """
    Get student by their student ID (enrollment number)
    """
    query = db.query(StudentUser).filter(StudentUser.student_id == student_id)
    if college_id:
        query = query.filter(StudentUser.college_id == college_id)
    return query.first()


def get_student_attendance_summary(db, student_id: str, subject_id: str = None):
    """
    Get attendance summary for a student
    """
    from sqlalchemy import and_, func as sql_func
    
    query = db.query(
        sql_func.count(StudentAttendance.id).label('total_sessions'),
        sql_func.sum(StudentAttendance.is_present.cast(Integer)).label('present_sessions')
    ).join(StudentUser).filter(StudentUser.id == student_id)
    
    if subject_id:
        query = query.join(CMSAttendanceSession).filter(
            CMSAttendanceSession.subject_id == subject_id
        )
    
    return query.first()


def get_student_pending_assignments(db, student_id: str):
    """
    Get pending assignments for a student
    """
    from sqlalchemy import and_, or_
    
    # Get assignments that are published and either not submitted or past due
    current_time = func.extract('epoch', func.now()).cast(Integer)
    
    submitted_assignment_ids = db.query(StudentAssignmentSubmission.assignment_id).filter(
        StudentAssignmentSubmission.student_id == student_id
    ).subquery()
    
    return db.query(CMSAssignment).filter(
        and_(
            CMSAssignment.status == 'published',
            or_(
                CMSAssignment.due_date >= current_time,
                CMSAssignment.due_date.is_(None)
            ),
            ~CMSAssignment.id.in_(submitted_assignment_ids)
        )
    ).all()


def get_student_current_semester_results(db, student_id: str):
    """
    Get current semester results for a student
    """
    student = db.query(StudentUser).filter(StudentUser.id == student_id).first()
    if not student:
        return []
    
    return db.query(StudentResult).join(CMSExamination).filter(
        and_(
            StudentResult.student_id == student_id,
            CMSExamination.semester == student.current_semester
        )
    ).all()