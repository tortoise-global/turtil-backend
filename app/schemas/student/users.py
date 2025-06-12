from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentUserRole(str, Enum):
    STUDENT = "student"


class StudentUserBase(BaseModel):
    username: str = Field(..., description="Unique username")
    email: EmailStr = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    phone: Optional[str] = Field(None, description="Phone number")
    role: Optional[StudentUserRole] = Field(
        StudentUserRole.STUDENT, description="User role"
    )
    student_id: str = Field(..., description="Student ID/enrollment number")
    roll_number: Optional[str] = Field(None, description="Roll number")
    admission_number: Optional[str] = Field(None, description="Admission number")
    department_id: Optional[UUID] = Field(None, description="Department UUID")
    branch_id: Optional[UUID] = Field(None, description="Branch UUID")
    degree_id: Optional[UUID] = Field(None, description="Degree UUID")
    batch_year: Optional[int] = Field(None, description="Batch year")
    current_semester: Optional[int] = Field(None, description="Current semester")
    admission_date: Optional[date] = Field(None, description="Admission date")
    graduation_date: Optional[date] = Field(
        None, description="Expected graduation date"
    )
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
    guardian_name: Optional[str] = Field(None, description="Guardian name")
    guardian_phone: Optional[str] = Field(None, description="Guardian phone")
    emergency_contact: Optional[str] = Field(None, description="Emergency contact")
    blood_group: Optional[str] = Field(None, description="Blood group")
    date_of_birth: Optional[date] = Field(None, description="Date of birth")
    gender: Optional[str] = Field(None, description="Gender")
    address: Optional[str] = Field(None, description="Address")
    is_active: Optional[bool] = Field(True, description="User status")
    email_verified: Optional[bool] = Field(
        False, description="Email verification status"
    )


class StudentUserCreate(StudentUserBase):
    college_id: UUID = Field(..., description="College UUID")
    password: str = Field(..., min_length=8, description="User password")


class StudentUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    roll_number: Optional[str] = None
    admission_number: Optional[str] = None
    department_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    degree_id: Optional[UUID] = None
    batch_year: Optional[int] = None
    current_semester: Optional[int] = None
    admission_date: Optional[date] = None
    graduation_date: Optional[date] = None
    profile_image_url: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    blood_group: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None
    email_verified: Optional[bool] = None


class StudentUserResponse(StudentUserBase):
    id: UUID
    college_id: UUID
    last_login: Optional[int] = None
    created_at: int
    updated_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class StudentUserLogin(BaseModel):
    username_or_email: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class StudentUserToken(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    user_id: UUID = Field(..., description="User UUID")
    student_id: str = Field(..., description="Student ID")
    college_id: UUID = Field(..., description="College UUID")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class StudentPasswordChange(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class StudentPasswordReset(BaseModel):
    email: EmailStr = Field(..., description="Email address")


class StudentPasswordResetConfirm(BaseModel):
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")


# STUDENT ATTENDANCE SCHEMAS


class StudentAttendanceBase(BaseModel):
    is_present: bool = Field(..., description="Attendance status")
    marked_at: Optional[int] = Field(None, description="Marked timestamp")


class StudentAttendanceCreate(StudentAttendanceBase):
    session_id: UUID = Field(..., description="Session UUID")
    student_id: UUID = Field(..., description="Student UUID")
    marked_by: Optional[UUID] = Field(None, description="Marked by faculty UUID")


class StudentAttendanceUpdate(BaseModel):
    is_present: Optional[bool] = None


class StudentAttendanceResponse(StudentAttendanceBase):
    id: UUID
    session_id: UUID
    student_id: UUID
    marked_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


# STUDENT ASSIGNMENT SUBMISSION SCHEMAS


class StudentAssignmentSubmissionBase(BaseModel):
    submission_text: Optional[str] = Field(None, description="Submission text")
    file_urls: Optional[List[str]] = Field(None, description="Submitted file URLs")
    submitted_at: Optional[int] = Field(None, description="Submission timestamp")
    marks_awarded: Optional[int] = Field(None, description="Marks awarded")
    feedback: Optional[str] = Field(None, description="Faculty feedback")
    graded_at: Optional[int] = Field(None, description="Grading timestamp")


class StudentAssignmentSubmissionCreate(StudentAssignmentSubmissionBase):
    assignment_id: UUID = Field(..., description="Assignment UUID")
    student_id: UUID = Field(..., description="Student UUID")


class StudentAssignmentSubmissionUpdate(BaseModel):
    submission_text: Optional[str] = None
    file_urls: Optional[List[str]] = None


class StudentAssignmentSubmissionResponse(StudentAssignmentSubmissionBase):
    id: UUID
    assignment_id: UUID
    student_id: UUID
    graded_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


# STUDENT RESULT SCHEMAS


class StudentResultBase(BaseModel):
    marks_obtained: Optional[Decimal] = Field(None, description="Marks obtained")
    max_marks: Optional[Decimal] = Field(None, description="Maximum marks")
    grade: Optional[str] = Field(None, description="Grade")
    is_pass: Optional[bool] = Field(None, description="Pass status")
    remarks: Optional[str] = Field(None, description="Remarks")


class StudentResultCreate(StudentResultBase):
    examination_id: UUID = Field(..., description="Examination UUID")
    student_id: UUID = Field(..., description="Student UUID")
    subject_id: UUID = Field(..., description="Subject UUID")


class StudentResultUpdate(BaseModel):
    marks_obtained: Optional[Decimal] = None
    max_marks: Optional[Decimal] = None
    grade: Optional[str] = None
    is_pass: Optional[bool] = None
    remarks: Optional[str] = None


class StudentResultResponse(StudentResultBase):
    id: UUID
    examination_id: UUID
    student_id: UUID
    subject_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# STUDENT PLACEMENT SCHEMAS


class StudentPlacementStatus(str, Enum):
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    SELECTED = "selected"
    REJECTED = "rejected"


class StudentPlacementBase(BaseModel):
    application_date: Optional[date] = Field(None, description="Application date")
    status: Optional[StudentPlacementStatus] = Field(
        StudentPlacementStatus.APPLIED, description="Application status"
    )
    interview_date: Optional[date] = Field(None, description="Interview date")
    feedback: Optional[str] = Field(None, description="Feedback")


class StudentPlacementCreate(StudentPlacementBase):
    student_id: UUID = Field(..., description="Student UUID")
    placement_drive_id: UUID = Field(..., description="Placement drive UUID")


class StudentPlacementUpdate(BaseModel):
    status: Optional[StudentPlacementStatus] = None
    interview_date: Optional[date] = None
    feedback: Optional[str] = None


class StudentPlacementResponse(StudentPlacementBase):
    id: UUID
    student_id: UUID
    placement_drive_id: UUID
    updated_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# STUDENT NOTIFICATION SCHEMAS


class StudentNotificationBase(BaseModel):
    is_read: bool = Field(False, description="Read status")
    read_at: Optional[int] = Field(None, description="Read timestamp")


class StudentNotificationCreate(StudentNotificationBase):
    notification_id: UUID = Field(..., description="Notification UUID")
    student_id: UUID = Field(..., description="Student UUID")


class StudentNotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[int] = None


class StudentNotificationResponse(StudentNotificationBase):
    id: UUID
    notification_id: UUID
    student_id: UUID

    model_config = ConfigDict(from_attributes=True)


# STUDENT EVENT REGISTRATION SCHEMAS


class StudentEventAttendanceStatus(str, Enum):
    REGISTERED = "registered"
    ATTENDED = "attended"
    ABSENT = "absent"


class StudentEventRegistrationBase(BaseModel):
    registration_date: Optional[date] = Field(None, description="Registration date")
    attendance_status: Optional[StudentEventAttendanceStatus] = Field(
        StudentEventAttendanceStatus.REGISTERED, description="Attendance status"
    )
    remarks: Optional[str] = Field(None, description="Remarks")


class StudentEventRegistrationCreate(StudentEventRegistrationBase):
    event_id: UUID = Field(..., description="Event UUID")
    student_id: UUID = Field(..., description="Student UUID")


class StudentEventRegistrationUpdate(BaseModel):
    attendance_status: Optional[StudentEventAttendanceStatus] = None
    remarks: Optional[str] = None


class StudentEventRegistrationResponse(StudentEventRegistrationBase):
    id: UUID
    event_id: UUID
    student_id: UUID

    model_config = ConfigDict(from_attributes=True)


# STUDENT TIMETABLE PREFERENCE SCHEMAS


class StudentTimetablePreferenceBase(BaseModel):
    is_bookmarked: bool = Field(False, description="Bookmark status")
    notes: Optional[str] = Field(None, description="Personal notes")


class StudentTimetablePreferenceCreate(StudentTimetablePreferenceBase):
    student_id: UUID = Field(..., description="Student UUID")
    timetable_slot_id: UUID = Field(..., description="Timetable slot UUID")


class StudentTimetablePreferenceUpdate(BaseModel):
    is_bookmarked: Optional[bool] = None
    notes: Optional[str] = None


class StudentTimetablePreferenceResponse(StudentTimetablePreferenceBase):
    id: UUID
    student_id: UUID
    timetable_slot_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# STUDENT DASHBOARD SCHEMAS


class StudentDashboardBase(BaseModel):
    total_attendance_percentage: Optional[Decimal] = Field(
        None, description="Overall attendance percentage"
    )
    pending_assignments: Optional[int] = Field(
        0, description="Number of pending assignments"
    )
    upcoming_events: Optional[int] = Field(0, description="Number of upcoming events")
    unread_notifications: Optional[int] = Field(
        0, description="Number of unread notifications"
    )
    current_semester_gpa: Optional[Decimal] = Field(
        None, description="Current semester GPA"
    )


class StudentDashboardCreate(StudentDashboardBase):
    student_id: UUID = Field(..., description="Student UUID")


class StudentDashboardResponse(StudentDashboardBase):
    id: UUID
    student_id: UUID
    last_updated: int

    model_config = ConfigDict(from_attributes=True)


# COMPLEX RESPONSE MODELS


class StudentAttendanceSummary(BaseModel):
    """Student attendance summary"""

    student_id: UUID
    subject_wise_attendance: Dict[str, Dict[str, Any]] = Field(
        ..., description="Subject-wise attendance data"
    )
    overall_percentage: float
    semester_percentage: float

    model_config = ConfigDict(from_attributes=True)


class StudentAcademicProfile(BaseModel):
    """Complete student academic profile"""

    student: StudentUserResponse
    current_semester_subjects: List[Dict[str, Any]] = []
    attendance_summary: StudentAttendanceSummary
    recent_results: List[StudentResultResponse] = []
    pending_assignments: List[Dict[str, Any]] = []
    placement_status: Optional[StudentPlacementResponse] = None

    model_config = ConfigDict(from_attributes=True)


class StudentResultCard(BaseModel):
    """Student result card for a semester"""

    student_id: UUID
    examination_id: UUID
    semester: int
    academic_year: int
    subjects: List[StudentResultResponse] = []
    total_marks: Decimal
    percentage: Decimal
    gpa: Optional[Decimal] = None
    grade: str
    is_pass: bool

    model_config = ConfigDict(from_attributes=True)


class StudentTimetableView(BaseModel):
    """Student's weekly timetable view"""

    student_id: UUID
    semester: int
    academic_year: int
    schedule: Dict[str, List[Dict[str, Any]]] = Field(
        ..., description="Weekly schedule organized by day"
    )
    bookmarked_slots: List[UUID] = Field(
        ..., description="Bookmarked timetable slot UUIDs"
    )

    model_config = ConfigDict(from_attributes=True)


# ANALYTICS AND STATISTICS SCHEMAS


class StudentPerformanceAnalytics(BaseModel):
    """Student performance analytics"""

    student_id: UUID
    semester_wise_performance: Dict[int, Dict[str, Any]] = Field(
        ..., description="Performance data by semester"
    )
    subject_wise_performance: Dict[str, Dict[str, Any]] = Field(
        ..., description="Performance data by subject"
    )
    attendance_trends: Dict[str, Any] = Field(..., description="Attendance trend data")
    assignment_submission_rate: float
    overall_grade_trend: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class StudentPlacementProfile(BaseModel):
    """Student placement profile"""

    student_id: UUID
    cgpa: Optional[Decimal] = None
    skills: List[str] = []
    certifications: List[str] = []
    internships: List[Dict[str, Any]] = []
    projects: List[Dict[str, Any]] = []
    placement_applications: List[StudentPlacementResponse] = []
    interview_history: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


# MOBILE APP SPECIFIC SCHEMAS


class MobileStudentProfile(BaseModel):
    """Optimized student profile for mobile app"""

    basic_info: Dict[str, Any] = Field(..., description="Basic student information")
    academic_summary: Dict[str, Any] = Field(..., description="Academic summary")
    quick_stats: Dict[str, Any] = Field(..., description="Quick statistics")
    recent_activities: List[Dict[str, Any]] = Field(
        ..., description="Recent activities"
    )

    model_config = ConfigDict(from_attributes=True)


class MobileNotificationPayload(BaseModel):
    """Mobile push notification payload"""

    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Dict[str, Any] = Field(..., description="Additional data")
    priority: str = Field("normal", description="Notification priority")
    badge_count: Optional[int] = Field(None, description="Badge count")

    model_config = ConfigDict(from_attributes=True)
