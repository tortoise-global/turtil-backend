from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date
from app.core.utils import CamelCaseModel


# ============================================================================
# TERM SCHEMAS
# ============================================================================

class CreateTermRequest(CamelCaseModel):
    """Request schema for creating a new term"""
    
    batch_year: int = Field(..., ge=2020, le=2050, description="Graduation year (2025, 2026, etc.)")
    current_year: int = Field(..., ge=1, le=4, description="Academic year (1, 2, 3, 4)")
    current_semester: int = Field(..., ge=1, le=2, description="Semester (1, 2)")
    start_date: date = Field(..., description="Term start date")
    end_date: date = Field(..., description="Term end date")
    
    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v, values):
        if hasattr(values, 'data') and 'start_date' in values.data:
            if v <= values.data['start_date']:
                raise ValueError('End date must be after start date')
        return v


class UpdateTermRequest(CamelCaseModel):
    """Request schema for updating a term"""
    
    start_date: Optional[date] = Field(None, description="Term start date")
    end_date: Optional[date] = Field(None, description="Term end date")
    is_active: Optional[bool] = Field(None, description="Is term active")


class TermResponse(CamelCaseModel):
    """Response schema for term data"""
    
    term_id: str
    batch_year: int
    current_year: int
    current_semester: int
    term_name: str
    term_code: str
    is_active: bool
    is_ongoing: bool
    start_date: date
    end_date: date
    college_id: str
    created_at: str
    updated_at: str


class TermWithStatsResponse(TermResponse):
    """Response schema for term with resource counts"""
    
    resource_counts: dict = Field(default_factory=dict)


class TermActionResponse(CamelCaseModel):
    """Response schema for term actions (create, update, delete)"""
    
    success: bool
    message: str
    term_id: Optional[str] = None
    deleted_counts: Optional[dict] = None


# ============================================================================
# GRADUATION SCHEMAS
# ============================================================================

class CreateGraduationRequest(CamelCaseModel):
    """Request schema for creating a new graduation level"""
    
    graduation_name: str = Field(..., min_length=2, max_length=255, description="Graduation level name")
    graduation_code: str = Field(..., min_length=2, max_length=20, description="Graduation code (UG, PG, etc.)")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    sequence_order: int = Field(1, ge=1, le=99, description="Display order")
    term_id: str = Field(..., description="Parent term ID")
    
    @field_validator("graduation_code")
    @classmethod
    def graduation_code_uppercase(cls, v):
        return v.upper()


class UpdateGraduationRequest(CamelCaseModel):
    """Request schema for updating a graduation level"""
    
    graduation_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    sequence_order: Optional[int] = Field(None, ge=1, le=99)


class GraduationResponse(CamelCaseModel):
    """Response schema for graduation data"""
    
    graduation_id: str
    graduation_name: str
    graduation_code: str
    description: Optional[str]
    sequence_order: int
    term_id: str
    created_at: str
    updated_at: str


class GraduationWithStatsResponse(GraduationResponse):
    """Response schema for graduation with resource counts"""
    
    term_name: str
    resource_counts: dict = Field(default_factory=dict)


class GraduationActionResponse(CamelCaseModel):
    """Response schema for graduation actions"""
    
    success: bool
    message: str
    graduation_id: Optional[str] = None
    deleted_counts: Optional[dict] = None


# ============================================================================
# DEGREE SCHEMAS
# ============================================================================

class CreateDegreeRequest(CamelCaseModel):
    """Request schema for creating a new degree"""
    
    degree_name: str = Field(..., min_length=5, max_length=255, description="Degree name")
    degree_code: str = Field(..., min_length=2, max_length=20, description="Degree code (BTECH, MTECH, etc.)")
    short_name: str = Field(..., min_length=2, max_length=50, description="Short name (B.Tech, M.Tech, etc.)")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    sequence_order: int = Field(1, ge=1, le=99, description="Display order")
    graduation_id: str = Field(..., description="Parent graduation ID")
    
    @field_validator("degree_code")
    @classmethod
    def degree_code_uppercase(cls, v):
        return v.upper()


class UpdateDegreeRequest(CamelCaseModel):
    """Request schema for updating a degree"""
    
    degree_name: Optional[str] = Field(None, min_length=5, max_length=255)
    short_name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    sequence_order: Optional[int] = Field(None, ge=1, le=99)


class DegreeResponse(CamelCaseModel):
    """Response schema for degree data"""
    
    degree_id: str
    degree_name: str
    degree_code: str
    short_name: str
    description: Optional[str]
    sequence_order: int
    graduation_id: str
    created_at: str
    updated_at: str


class DegreeWithStatsResponse(DegreeResponse):
    """Response schema for degree with resource counts"""
    
    graduation_name: str
    resource_counts: dict = Field(default_factory=dict)


class DegreeActionResponse(CamelCaseModel):
    """Response schema for degree actions"""
    
    success: bool
    message: str
    degree_id: Optional[str] = None
    deleted_counts: Optional[dict] = None


# ============================================================================
# BRANCH SCHEMAS
# ============================================================================

class CreateBranchRequest(CamelCaseModel):
    """Request schema for creating a new branch"""
    
    branch_name: str = Field(..., min_length=5, max_length=255, description="Branch name")
    branch_code: str = Field(..., min_length=2, max_length=20, description="Branch code (CSE, ME, etc.)")
    short_name: str = Field(..., min_length=2, max_length=100, description="Short name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    sequence_order: int = Field(1, ge=1, le=99, description="Display order")
    degree_id: str = Field(..., description="Parent degree ID")
    department_id: str = Field(..., description="Associated department ID")
    
    @field_validator("branch_code")
    @classmethod
    def branch_code_uppercase(cls, v):
        return v.upper()


class UpdateBranchRequest(CamelCaseModel):
    """Request schema for updating a branch"""
    
    branch_name: Optional[str] = Field(None, min_length=5, max_length=255)
    short_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    sequence_order: Optional[int] = Field(None, ge=1, le=99)
    department_id: Optional[str] = Field(None, description="Associated department ID")


class BranchResponse(CamelCaseModel):
    """Response schema for branch data"""
    
    branch_id: str
    branch_name: str
    branch_code: str
    short_name: str
    description: Optional[str]
    sequence_order: int
    degree_id: str
    department_id: str
    created_at: str
    updated_at: str


class BranchWithStatsResponse(BranchResponse):
    """Response schema for branch with resource counts"""
    
    degree_name: str
    department_name: str
    resource_counts: dict = Field(default_factory=dict)


class BranchActionResponse(CamelCaseModel):
    """Response schema for branch actions"""
    
    success: bool
    message: str
    branch_id: Optional[str] = None
    deleted_counts: Optional[dict] = None


# ============================================================================
# SUBJECT SCHEMAS
# ============================================================================

class CreateSubjectRequest(CamelCaseModel):
    """Request schema for creating a new subject"""
    
    subject_name: str = Field(..., min_length=3, max_length=255, description="Subject name")
    subject_code: str = Field(..., min_length=3, max_length=20, description="Subject code")
    short_name: str = Field(..., min_length=2, max_length=100, description="Short name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    credits: int = Field(3, ge=1, le=8, description="Credit points")
    subject_type: str = Field("theory", description="Subject type")
    sequence_order: int = Field(1, ge=1, le=999, description="Display order")
    branch_id: str = Field(..., description="Parent branch ID")
    
    @field_validator("subject_code")
    @classmethod
    def subject_code_uppercase(cls, v):
        return v.upper()
    
    @field_validator("subject_type")
    @classmethod
    def validate_subject_type(cls, v):
        allowed_types = ["theory", "practical", "project", "elective"]
        if v not in allowed_types:
            raise ValueError(f"Subject type must be one of: {', '.join(allowed_types)}")
        return v


class CreateSubjectBulkRequest(CamelCaseModel):
    """Request schema for bulk creating subjects"""
    
    branch_id: str = Field(..., description="Parent branch ID")
    subjects: List[CreateSubjectRequest] = Field(..., min_items=1, max_items=50)


class UpdateSubjectRequest(CamelCaseModel):
    """Request schema for updating a subject"""
    
    subject_name: Optional[str] = Field(None, min_length=3, max_length=255)
    short_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    credits: Optional[int] = Field(None, ge=1, le=8)
    subject_type: Optional[str] = Field(None)
    sequence_order: Optional[int] = Field(None, ge=1, le=999)
    
    @field_validator("subject_type")
    @classmethod
    def validate_subject_type(cls, v):
        if v is not None:
            allowed_types = ["theory", "practical", "project", "elective"]
            if v not in allowed_types:
                raise ValueError(f"Subject type must be one of: {', '.join(allowed_types)}")
        return v


class SubjectResponse(CamelCaseModel):
    """Response schema for subject data"""
    
    subject_id: str
    subject_name: str
    subject_code: str
    short_name: str
    description: Optional[str]
    credits: int
    subject_type: str
    sequence_order: int
    branch_id: str
    created_at: str
    updated_at: str


class SubjectWithBranchResponse(SubjectResponse):
    """Response schema for subject with branch info"""
    
    branch_name: str


class SubjectActionResponse(CamelCaseModel):
    """Response schema for subject actions"""
    
    success: bool
    message: str
    subject_id: Optional[str] = None
    subjects: Optional[List[dict]] = None
    created_count: Optional[int] = None


# ============================================================================
# SECTION SCHEMAS
# ============================================================================

class CreateSectionRequest(CamelCaseModel):
    """Request schema for creating a new section"""
    
    section_name: str = Field(..., min_length=2, max_length=100, description="Section name")
    section_code: str = Field(..., min_length=1, max_length=10, description="Section code")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    student_capacity: int = Field(60, ge=1, le=200, description="Student capacity")
    sequence_order: int = Field(1, ge=1, le=99, description="Display order")
    branch_id: str = Field(..., description="Parent branch ID")
    class_teacher_id: Optional[str] = Field(None, description="Class teacher staff ID")
    
    @field_validator("section_code")
    @classmethod
    def section_code_uppercase(cls, v):
        return v.upper()


class UpdateSectionRequest(CamelCaseModel):
    """Request schema for updating a section"""
    
    section_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    student_capacity: Optional[int] = Field(None, ge=1, le=200)
    sequence_order: Optional[int] = Field(None, ge=1, le=99)
    class_teacher_id: Optional[str] = Field(None, description="Class teacher staff ID")


class SectionResponse(CamelCaseModel):
    """Response schema for section data"""
    
    section_id: str
    section_name: str
    section_code: str
    description: Optional[str]
    student_capacity: int
    current_strength: int
    sequence_order: int
    branch_id: str
    class_teacher_id: Optional[str]
    created_at: str
    updated_at: str


class SectionWithDetailsResponse(SectionResponse):
    """Response schema for section with additional details"""
    
    branch_name: str
    class_teacher_name: Optional[str]
    assigned_subjects_count: int = 0


class SectionActionResponse(CamelCaseModel):
    """Response schema for section actions"""
    
    success: bool
    message: str
    section_id: Optional[str] = None


# ============================================================================
# SECTION-SUBJECT ASSIGNMENT SCHEMAS
# ============================================================================

class SubjectAssignment(CamelCaseModel):
    """Schema for individual subject assignment"""
    
    subject_id: str = Field(..., description="Subject ID")
    assigned_staff_id: Optional[str] = Field(None, description="Assigned teacher staff ID")


class AssignSubjectsRequest(CamelCaseModel):
    """Request schema for assigning subjects to section"""
    
    section_id: str = Field(..., description="Section ID")
    assignments: List[SubjectAssignment] = Field(..., min_items=1, max_items=20)


class AssignTeacherRequest(CamelCaseModel):
    """Request schema for assigning teacher to section-subject"""
    
    assigned_staff_id: str = Field(..., description="Staff ID to assign")


class SectionSubjectResponse(CamelCaseModel):
    """Response schema for section-subject data"""
    
    section_subject_id: str
    section_id: str
    section_name: str
    subject_id: str
    subject_name: str
    subject_code: str
    assigned_staff_id: Optional[str]
    assigned_staff_name: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str


class AssignmentActionResponse(CamelCaseModel):
    """Response schema for assignment actions"""
    
    success: bool
    message: str
    section_name: Optional[str] = None
    assigned_count: Optional[int] = None
    assignments: Optional[List[dict]] = None
    section_subject_id: Optional[str] = None
    subject_name: Optional[str] = None
    old_teacher: Optional[str] = None
    new_teacher: Optional[str] = None


# ============================================================================
# TREE NAVIGATION SCHEMAS
# ============================================================================

class TreeBranchInfo(CamelCaseModel):
    """Branch info for tree navigation"""
    
    branch_id: str
    branch_name: str
    branch_code: str
    department_name: str
    subject_count: int
    section_count: int


class TreeDegreeInfo(CamelCaseModel):
    """Degree info for tree navigation"""
    
    degree_id: str
    degree_name: str
    degree_code: str
    branches: List[TreeBranchInfo]


class TreeGraduationInfo(CamelCaseModel):
    """Graduation info for tree navigation"""
    
    graduation_id: str
    graduation_name: str
    graduation_code: str
    degrees: List[TreeDegreeInfo]


class TreeStructureResponse(CamelCaseModel):
    """Response schema for complete tree structure"""
    
    term: dict
    graduations: List[TreeGraduationInfo]


class CompleteBranchResponse(CamelCaseModel):
    """Response schema for branch with all subjects and sections"""
    
    branch: dict
    subjects: List[SubjectResponse]
    sections: List[dict]