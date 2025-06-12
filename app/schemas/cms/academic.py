from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Enums
class TimetableDay(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"


class SubjectType(str, Enum):
    THEORY = "theory"
    LAB = "lab"
    PROJECT = "project"


# Batch Schemas
class BatchBase(BaseModel):
    """
    Batch model for Indian academic system

    ## Examples:

    ### Engineering Batch:
    ```json
    {
        "name": "BTech-CSE-2024",
        "year": 2024,
        "semester": 1,
        "start_date": 1706764200,
        "end_date": 1722550800,
        "is_active": true
    }
    ```

    ### Medical Batch:
    ```json
    {
        "name": "MBBS-2024-Batch1",
        "year": 2024,
        "semester": 1,
        "start_date": 1706764200,
        "end_date": 1875142800,
        "is_active": true
    }
    ```

    ### Arts Batch (Hindi naming):
    ```json
    {
        "name": "कला संकाय-2024 (BA-Arts-2024)",
        "year": 2024,
        "semester": 1,
        "start_date": 1706764200,
        "end_date": 1801459200,
        "is_active": true
    }
    ```
    """

    name: str = Field(
        ..., description="Batch name (e.g., BTech-CSE-2024, MBBS-2024-Batch1)"
    )
    year: int = Field(..., description="Academic year")
    semester: int = Field(..., description="Current semester")
    start_date: Optional[int] = Field(None, description="Start date timestamp")
    end_date: Optional[int] = Field(None, description="End date timestamp")
    is_active: Optional[bool] = Field(True, description="Batch status")


class BatchCreate(BatchBase):
    department_id: UUID = Field(..., description="Department UUID")
    branch_id: UUID = Field(..., description="Branch UUID")
    degree_id: UUID = Field(..., description="Degree UUID")


class BatchUpdate(BaseModel):
    name: Optional[str] = None
    semester: Optional[int] = None
    start_date: Optional[int] = None
    end_date: Optional[int] = None
    is_active: Optional[bool] = None


class BatchResponse(BatchBase):
    id: UUID
    college_id: UUID
    department_id: UUID
    branch_id: UUID
    degree_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# Section Schemas
class SectionBase(BaseModel):
    """
    Section model for Indian academic system

    ## Examples:

    ### Engineering Section:
    ```json
    {
        "name": "CSE-A",
        "capacity": 60,
        "current_strength": 58,
        "class_teacher_id": "teacher-dr-rajesh-kumar",
        "is_active": true
    }
    ```

    ### Medical Section:
    ```json
    {
        "name": "MBBS-Group-1",
        "capacity": 100,
        "current_strength": 95,
        "class_teacher_id": "teacher-dr-priya-sharma",
        "is_active": true
    }
    ```

    ### Arts Section (Hindi naming):
    ```json
    {
        "name": "हिंदी-अ (Hindi-A)",
        "capacity": 50,
        "current_strength": 45,
        "class_teacher_id": "teacher-prof-kavita-singh",
        "is_active": true
    }
    ```
    """

    name: str = Field(..., description="Section name (CSE-A, MBBS-Group-1, Hindi-A)")
    capacity: Optional[int] = Field(60, description="Section capacity")
    current_strength: Optional[int] = Field(0, description="Current student count")
    class_teacher_id: Optional[UUID] = Field(None, description="Class teacher UUID")
    is_active: Optional[bool] = Field(True, description="Section status")


class SectionCreate(SectionBase):
    batch_id: UUID = Field(..., description="Batch UUID")


class SectionUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    current_strength: Optional[int] = None
    class_teacher_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class SectionResponse(SectionBase):
    id: UUID
    batch_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# Subject Schemas
class SubjectBase(BaseModel):
    """
    Subject model for Indian academic system

    ## Examples:

    ### Engineering Subject:
    ```json
    {
        "name": "डेटा स्ट्रक्चर और एल्गोरिदम (Data Structures and Algorithms)",
        "code": "CSE301",
        "credits": 4,
        "semester": 3,
        "subject_type": "theory",
        "description": "Comprehensive study of data structures, algorithms and their applications",
        "is_active": true
    }
    ```

    ### Medical Subject:
    ```json
    {
        "name": "शरीर विज्ञान (Human Physiology)",
        "code": "MED102",
        "credits": 6,
        "semester": 2,
        "subject_type": "theory",
        "description": "Study of normal functions of human body systems",
        "is_active": true
    }
    ```

    ### Laboratory Subject:
    ```json
    {
        "name": "कंप्यूटर प्रोग्रामिंग लैब (Computer Programming Lab)",
        "code": "CSE191",
        "credits": 2,
        "semester": 1,
        "subject_type": "lab",
        "description": "Hands-on programming experience in C/C++ and Python",
        "is_active": true
    }
    ```

    ### Commerce Subject:
    ```json
    {
        "name": "व्यावसायिक गणित (Business Mathematics)",
        "code": "COM101",
        "credits": 3,
        "semester": 1,
        "subject_type": "theory",
        "description": "Mathematical concepts and their application in business scenarios",
        "is_active": true
    }
    ```
    """

    name: str = Field(
        ..., description="Subject name (supports Hindi/regional languages)"
    )
    code: str = Field(..., description="Subject code (CSE301, MED102, COM101)")
    credits: Optional[int] = Field(3, description="Credit hours")
    semester: int = Field(..., description="Semester number")
    subject_type: Optional[SubjectType] = Field(
        SubjectType.THEORY, description="Subject type"
    )
    description: Optional[str] = Field(None, description="Subject description")
    is_active: Optional[bool] = Field(True, description="Subject status")


class SubjectCreate(SubjectBase):
    department_id: UUID = Field(..., description="Department UUID")


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    credits: Optional[int] = None
    semester: Optional[int] = None
    subject_type: Optional[SubjectType] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SubjectResponse(SubjectBase):
    id: UUID
    college_id: UUID
    department_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# Timetable Schemas
class TimetableBase(BaseModel):
    """
    Timetable model for Indian academic system

    ## Examples:

    ### Engineering Timetable:
    ```json
    {
        "day_of_week": "monday",
        "start_time": "09:00",
        "end_time": "10:00",
        "room_number": "CS-101",
        "is_active": true
    }
    ```

    ### Medical Timetable:
    ```json
    {
        "day_of_week": "tuesday",
        "start_time": "10:00",
        "end_time": "12:00",
        "room_number": "Anatomy-Hall-1",
        "is_active": true
    }
    ```

    ### Laboratory Schedule:
    ```json
    {
        "day_of_week": "wednesday",
        "start_time": "14:00",
        "end_time": "17:00",
        "room_number": "Computer-Lab-2",
        "is_active": true
    }
    ```

    ### Evening Classes (Common in Indian Colleges):
    ```json
    {
        "day_of_week": "friday",
        "start_time": "16:00",
        "end_time": "18:00",
        "room_number": "Evening-Block-201",
        "is_active": true
    }
    ```
    """

    day_of_week: TimetableDay = Field(..., description="Day of the week")
    start_time: str = Field(..., description="Start time (HH:MM) - 24-hour format")
    end_time: str = Field(..., description="End time (HH:MM) - 24-hour format")
    room_number: Optional[str] = Field(
        None, description="Room number (supports Hindi/regional naming)"
    )
    is_active: Optional[bool] = Field(True, description="Timetable entry status")


class TimetableCreate(TimetableBase):
    section_id: UUID = Field(..., description="Section UUID")
    subject_id: UUID = Field(..., description="Subject UUID")
    teacher_id: UUID = Field(..., description="Teacher UUID")


class TimetableUpdate(BaseModel):
    day_of_week: Optional[TimetableDay] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    room_number: Optional[str] = None
    teacher_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class TimetableResponse(TimetableBase):
    id: UUID
    college_id: UUID
    section_id: UUID
    subject_id: UUID
    teacher_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# Cross-Department Teaching Schemas
class CrossDepartmentAssignment(BaseModel):
    """
    Cross-department teaching assignment for Indian academic system

    ## Examples:

    ### Mathematics Teacher Teaching Across Departments:
    ```json
    {
        "teacher_id": "teacher-dr-suresh-sharma",
        "department_id": "dept-computer-science",
        "subject_ids": [
            "subject-discrete-mathematics",
            "subject-statistics-for-cs"
        ]
    }
    ```

    ### English Teacher for Technical Communication:
    ```json
    {
        "teacher_id": "teacher-prof-kavita-nair",
        "department_id": "dept-mechanical-engineering",
        "subject_ids": [
            "subject-technical-english",
            "subject-communication-skills"
        ]
    }
    ```

    ### Guest Faculty Assignment:
    ```json
    {
        "teacher_id": "teacher-ca-priya-singh",
        "department_id": "dept-management",
        "subject_ids": [
            "subject-financial-accounting",
            "subject-cost-accounting",
            "subject-taxation"
        ]
    }
    ```
    """

    teacher_id: UUID = Field(..., description="Teacher UUID")
    department_id: UUID = Field(..., description="Additional department UUID")
    subject_ids: List[UUID] = Field(..., description="List of subject UUIDs")


class TeacherAssignmentResponse(BaseModel):
    """
    Teacher assignment response with Indian context

    ## Example Response:
    ```json
    {
        "teacher_id": "teacher-dr-suresh-sharma",
        "teacher_full_name": "Prof. (Dr.) Suresh Chandra Sharma",
        "primary_department_id": "dept-mathematics",
        "primary_department_name": "गणित विभाग (Mathematics Department)",
        "managed_departments": [
            "dept-mathematics",
            "dept-computer-science",
            "dept-physics"
        ],
        "teaching_subjects": [
            {
                "id": "subject-calculus",
                "name": "कैलकुलस (Calculus)",
                "code": "MATH101",
                "department_id": "dept-mathematics",
                "department_name": "गणित विभाग (Mathematics Department)"
            },
            {
                "id": "subject-discrete-mathematics",
                "name": "असतत गणित (Discrete Mathematics)",
                "code": "CS201",
                "department_id": "dept-computer-science",
                "department_name": "कंप्यूटर विज्ञान विभाग (Computer Science Department)"
            }
        ]
    }
    ```
    """

    teacher_id: UUID
    teacher_full_name: Optional[str] = Field(
        None, description="Teacher's full name with designation"
    )
    primary_department_id: Optional[UUID]
    primary_department_name: Optional[str] = Field(
        None, description="Primary department name (supports regional languages)"
    )
    managed_departments: List[str]
    teaching_subjects: List[dict]

    model_config = ConfigDict(from_attributes=True)


# Academic Hierarchy Schemas
class AcademicHierarchy(BaseModel):
    college_id: UUID
    departments: List[dict]
    total_batches: int
    total_sections: int
    total_subjects: int

    model_config = ConfigDict(from_attributes=True)


# Bulk Operations
class BulkBatchCreate(BaseModel):
    batches: List[BatchCreate] = Field(..., description="List of batches to create")


class BulkSectionCreate(BaseModel):
    sections: List[SectionCreate] = Field(..., description="List of sections to create")


class BulkSubjectCreate(BaseModel):
    subjects: List[SubjectCreate] = Field(..., description="List of subjects to create")


# Academic Statistics
class AcademicStatistics(BaseModel):
    """
    Academic statistics for Indian college management system

    ## Example Response:
    ```json
    {
        "total_batches": 45,
        "total_sections": 120,
        "total_subjects": 280,
        "active_timetable_entries": 1850,
        "teachers_with_cross_dept_assignments": 25,
        "departments": {
            "engineering": {
                "batches": 20,
                "sections": 60,
                "subjects": 150
            },
            "medical": {
                "batches": 8,
                "sections": 15,
                "subjects": 80
            },
            "arts_science": {
                "batches": 12,
                "sections": 30,
                "subjects": 35
            },
            "commerce": {
                "batches": 5,
                "sections": 15,
                "subjects": 15
            }
        },
        "language_breakdown": {
            "hindi": 45,
            "english": 235,
            "regional": 15
        }
    }
    ```
    """

    total_batches: int
    total_sections: int
    total_subjects: int
    active_timetable_entries: int
    teachers_with_cross_dept_assignments: int
    departments: Optional[dict] = Field(None, description="Department-wise breakdown")
    language_breakdown: Optional[dict] = Field(
        None, description="Subjects by language of instruction"
    )

    model_config = ConfigDict(from_attributes=True)
