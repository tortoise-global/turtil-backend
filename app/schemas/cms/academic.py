from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from enum import Enum


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
    name: str = Field(..., description="Batch name (e.g., 2024-CSE)")
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
    name: str = Field(..., description="Section name (A, B, C)")
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
    name: str = Field(..., description="Subject name")
    code: str = Field(..., description="Subject code (CS101, IT201)")
    credits: Optional[int] = Field(3, description="Credit hours")
    semester: int = Field(..., description="Semester number")
    subject_type: Optional[SubjectType] = Field(SubjectType.THEORY, description="Subject type")
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
    day_of_week: TimetableDay = Field(..., description="Day of the week")
    start_time: str = Field(..., description="Start time (HH:MM)")
    end_time: str = Field(..., description="End time (HH:MM)")
    room_number: Optional[str] = Field(None, description="Room number")
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
    teacher_id: UUID = Field(..., description="Teacher UUID")
    department_id: UUID = Field(..., description="Additional department UUID")
    subject_ids: List[UUID] = Field(..., description="List of subject UUIDs")


class TeacherAssignmentResponse(BaseModel):
    teacher_id: UUID
    primary_department_id: Optional[UUID]
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
    total_batches: int
    total_sections: int
    total_subjects: int
    active_timetable_entries: int
    teachers_with_cross_dept_assignments: int

    model_config = ConfigDict(from_attributes=True)