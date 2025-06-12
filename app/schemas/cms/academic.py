from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, time
from enum import Enum
from decimal import Decimal


# CMS TIMETABLE SCHEMAS

class CMSDayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class CMSTimetableSlotBase(BaseModel):
    semester: Optional[int] = Field(None, description="Semester number")
    day_of_week: CMSDayOfWeek = Field(..., description="Day of the week")
    start_time: time = Field(..., description="Start time")
    end_time: time = Field(..., description="End time")
    room_number: Optional[str] = Field(None, description="Room number")
    academic_year: Optional[int] = Field(None, description="Academic year")
    is_active: Optional[bool] = Field(True, description="Slot status")


class CMSTimetableSlotCreate(CMSTimetableSlotBase):
    college_id: UUID = Field(..., description="College UUID")
    branch_id: Optional[UUID] = Field(None, description="Branch UUID")
    subject_id: Optional[UUID] = Field(None, description="Subject UUID")
    faculty_id: Optional[UUID] = Field(None, description="Faculty UUID")


class CMSTimetableSlotUpdate(BaseModel):
    branch_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    faculty_id: Optional[UUID] = None
    semester: Optional[int] = None
    day_of_week: Optional[CMSDayOfWeek] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    room_number: Optional[str] = None
    academic_year: Optional[int] = None
    is_active: Optional[bool] = None


class CMSTimetableSlotResponse(CMSTimetableSlotBase):
    id: UUID
    college_id: UUID
    branch_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    faculty_id: Optional[UUID] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# CMS ATTENDANCE SCHEMAS

class CMSAttendanceSessionBase(BaseModel):
    semester: Optional[int] = Field(None, description="Semester number")
    session_date: date = Field(..., description="Session date")
    session_time: Optional[time] = Field(None, description="Session time")
    session_type: Optional[str] = Field("regular", description="Session type")
    total_classes: Optional[int] = Field(1, description="Total classes in session")


class CMSAttendanceSessionCreate(CMSAttendanceSessionBase):
    college_id: UUID = Field(..., description="College UUID")
    subject_id: UUID = Field(..., description="Subject UUID")
    faculty_id: UUID = Field(..., description="Faculty UUID")
    branch_id: Optional[UUID] = Field(None, description="Branch UUID")


class CMSAttendanceSessionUpdate(BaseModel):
    branch_id: Optional[UUID] = None
    semester: Optional[int] = None
    session_date: Optional[date] = None
    session_time: Optional[time] = None
    session_type: Optional[str] = None
    total_classes: Optional[int] = None


class CMSAttendanceSessionResponse(CMSAttendanceSessionBase):
    id: UUID
    college_id: UUID
    subject_id: UUID
    faculty_id: UUID
    branch_id: Optional[UUID] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# CMS ASSIGNMENT SCHEMAS

class CMSAssignmentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class CMSAssignmentBase(BaseModel):
    title: str = Field(..., description="Assignment title")
    description: Optional[str] = Field(None, description="Assignment description")
    assignment_type: Optional[str] = Field("homework", description="Assignment type")
    due_date: Optional[int] = Field(None, description="Due date as timestamp")
    max_marks: Optional[int] = Field(0, description="Maximum marks")
    status: Optional[CMSAssignmentStatus] = Field(CMSAssignmentStatus.DRAFT, description="Assignment status")


class CMSAssignmentCreate(CMSAssignmentBase):
    college_id: UUID = Field(..., description="College UUID")
    subject_id: UUID = Field(..., description="Subject UUID")
    faculty_id: UUID = Field(..., description="Faculty UUID")


class CMSAssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignment_type: Optional[str] = None
    due_date: Optional[int] = None
    max_marks: Optional[int] = None
    status: Optional[CMSAssignmentStatus] = None


class CMSAssignmentResponse(CMSAssignmentBase):
    id: UUID
    college_id: UUID
    subject_id: UUID
    faculty_id: UUID
    created_at: int
    updated_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# CMS EXAMINATION SCHEMAS

class CMSExaminationBase(BaseModel):
    exam_name: str = Field(..., description="Examination name")
    exam_type: Optional[str] = Field(None, description="Examination type")
    academic_year: Optional[int] = Field(None, description="Academic year")
    semester: Optional[int] = Field(None, description="Semester")
    start_date: Optional[date] = Field(None, description="Start date")
    end_date: Optional[date] = Field(None, description="End date")
    is_active: Optional[bool] = Field(True, description="Examination status")


class CMSExaminationCreate(CMSExaminationBase):
    college_id: UUID = Field(..., description="College UUID")


class CMSExaminationUpdate(BaseModel):
    exam_name: Optional[str] = None
    exam_type: Optional[str] = None
    academic_year: Optional[int] = None
    semester: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class CMSExaminationResponse(CMSExaminationBase):
    id: UUID
    college_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# CMS EVENT SCHEMAS

class CMSEventType(str, Enum):
    ACADEMIC = "academic"
    CULTURAL = "cultural"
    SPORTS = "sports"
    PLACEMENT = "placement"
    SEMINAR = "seminar"
    WORKSHOP = "workshop"


class CMSEventBase(BaseModel):
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    event_type: Optional[CMSEventType] = Field(None, description="Event type")
    start_datetime: Optional[int] = Field(None, description="Start datetime as timestamp")
    end_datetime: Optional[int] = Field(None, description="End datetime as timestamp")
    location: Optional[str] = Field(None, description="Event location")
    max_participants: Optional[int] = Field(None, description="Maximum participants")
    registration_required: Optional[bool] = Field(False, description="Registration required")
    is_active: Optional[bool] = Field(True, description="Event status")


class CMSEventCreate(CMSEventBase):
    college_id: UUID = Field(..., description="College UUID")
    organizer_id: Optional[UUID] = Field(None, description="Organizer UUID")


class CMSEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[CMSEventType] = None
    start_datetime: Optional[int] = None
    end_datetime: Optional[int] = None
    location: Optional[str] = None
    organizer_id: Optional[UUID] = None
    max_participants: Optional[int] = None
    registration_required: Optional[bool] = None
    is_active: Optional[bool] = None


class CMSEventResponse(CMSEventBase):
    id: UUID
    college_id: UUID
    organizer_id: Optional[UUID] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# CMS PLACEMENT SCHEMAS

class CMSCompanyBase(BaseModel):
    name: str = Field(..., description="Company name")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[str] = Field(None, description="Company website")
    industry: Optional[str] = Field(None, description="Industry")
    location: Optional[str] = Field(None, description="Company location")
    is_active: Optional[bool] = Field(True, description="Company status")


class CMSCompanyCreate(CMSCompanyBase):
    pass


class CMSCompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class CMSCompanyResponse(CMSCompanyBase):
    id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class CMSPlacementDriveBase(BaseModel):
    position_title: str = Field(..., description="Position title")
    job_description: Optional[str] = Field(None, description="Job description")
    eligibility_criteria: Optional[str] = Field(None, description="Eligibility criteria")
    package_offered: Optional[str] = Field(None, description="Package offered")
    drive_date: Optional[date] = Field(None, description="Drive date")
    application_deadline: Optional[date] = Field(None, description="Application deadline")
    is_active: Optional[bool] = Field(True, description="Drive status")


class CMSPlacementDriveCreate(CMSPlacementDriveBase):
    college_id: UUID = Field(..., description="College UUID")
    company_id: UUID = Field(..., description="Company UUID")


class CMSPlacementDriveUpdate(BaseModel):
    company_id: Optional[UUID] = None
    position_title: Optional[str] = None
    job_description: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    package_offered: Optional[str] = None
    drive_date: Optional[date] = None
    application_deadline: Optional[date] = None
    is_active: Optional[bool] = None


class CMSPlacementDriveResponse(CMSPlacementDriveBase):
    id: UUID
    college_id: UUID
    company_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# CMS NOTIFICATION SCHEMAS

class CMSNotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    SUCCESS = "success"
    ERROR = "error"


class CMSNotificationTarget(str, Enum):
    ALL = "all"
    STUDENTS = "students"
    FACULTY = "faculty"
    DEPARTMENT = "department"
    BRANCH = "branch"


class CMSNotificationBase(BaseModel):
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    notification_type: Optional[CMSNotificationType] = Field(CMSNotificationType.INFO, description="Notification type")
    target_audience: Optional[CMSNotificationTarget] = Field(CMSNotificationTarget.ALL, description="Target audience")
    department_id: Optional[UUID] = Field(None, description="Department UUID for targeted notifications")
    branch_id: Optional[UUID] = Field(None, description="Branch UUID for targeted notifications")
    is_active: Optional[bool] = Field(True, description="Notification status")
    expires_at: Optional[int] = Field(None, description="Expiration timestamp")


class CMSNotificationCreate(CMSNotificationBase):
    college_id: UUID = Field(..., description="College UUID")
    created_by: UUID = Field(..., description="Creator UUID")


class CMSNotificationUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    notification_type: Optional[CMSNotificationType] = None
    target_audience: Optional[CMSNotificationTarget] = None
    department_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    expires_at: Optional[int] = None


class CMSNotificationResponse(CMSNotificationBase):
    id: UUID
    college_id: UUID
    created_by: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# CMS DOCUMENT REQUEST SCHEMAS

class CMSDocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    DELIVERED = "delivered"
    REJECTED = "rejected"


class CMSDocumentRequestBase(BaseModel):
    document_type: str = Field(..., description="Document type")
    purpose: Optional[str] = Field(None, description="Purpose of request")
    status: Optional[CMSDocumentStatus] = Field(CMSDocumentStatus.PENDING, description="Request status")
    requested_date: Optional[date] = Field(None, description="Request date")
    expected_delivery: Optional[date] = Field(None, description="Expected delivery date")
    remarks: Optional[str] = Field(None, description="Remarks")


class CMSDocumentRequestCreate(CMSDocumentRequestBase):
    college_id: UUID = Field(..., description="College UUID")
    student_id: UUID = Field(..., description="Student UUID")


class CMSDocumentRequestUpdate(BaseModel):
    status: Optional[CMSDocumentStatus] = None
    expected_delivery: Optional[date] = None
    processed_by: Optional[UUID] = None
    remarks: Optional[str] = None


class CMSDocumentRequestResponse(CMSDocumentRequestBase):
    id: UUID
    college_id: UUID
    student_id: UUID
    processed_by: Optional[UUID] = None
    created_at: int
    updated_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# COMPLEX RESPONSE MODELS

class TimetableWeekView(BaseModel):
    """Weekly timetable view"""
    branch_id: UUID
    semester: int
    academic_year: int
    schedule: Dict[str, List[CMSTimetableSlotResponse]] = Field(
        ..., description="Schedule organized by day of week"
    )

    model_config = ConfigDict(from_attributes=True)


class AttendanceReport(BaseModel):
    """Attendance report"""
    subject_id: UUID
    total_sessions: int
    students_present: Dict[str, int] = Field(..., description="Student attendance count")
    attendance_percentage: Dict[str, float] = Field(..., description="Student attendance percentage")

    model_config = ConfigDict(from_attributes=True)


class AssignmentSubmissionSummary(BaseModel):
    """Assignment submission summary"""
    assignment_id: UUID
    total_students: int
    submitted: int
    pending: int
    submission_rate: float
    average_marks: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PlacementStatistics(BaseModel):
    """Placement statistics"""
    total_drives: int
    active_drives: int
    total_applications: int
    total_selections: int
    placement_rate: float
    companies_participated: int

    model_config = ConfigDict(from_attributes=True)


# BULK OPERATION SCHEMAS

class BulkTimetableCreate(BaseModel):
    slots: List[CMSTimetableSlotCreate] = Field(..., description="List of timetable slots")
    academic_year: int = Field(..., description="Academic year")
    semester: int = Field(..., description="Semester")


class BulkAttendanceRecord(BaseModel):
    session_id: UUID = Field(..., description="Session UUID")
    student_attendances: List[Dict[str, Any]] = Field(
        ..., description="List of student attendance records"
    )


class BulkNotificationSend(BaseModel):
    notification_id: UUID = Field(..., description="Notification UUID")
    target_users: List[UUID] = Field(..., description="Target user UUIDs")
    send_email: Optional[bool] = Field(False, description="Send email notification")
    send_sms: Optional[bool] = Field(False, description="Send SMS notification")