"""
Student Registration Schemas
Pydantic schemas for student academic registration flow
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==================== COLLEGE SELECTION SCHEMAS ====================

class CollegeOption(BaseModel):
    """College selection option"""
    collegeId: str = Field(..., description="College UUID")
    name: str = Field(..., description="College name")
    shortName: str = Field(..., description="College short name")
    city: str = Field(..., description="College city")
    state: str = Field(..., description="College state")
    logoUrl: Optional[str] = Field(None, description="College logo URL")

class CollegeListResponse(BaseModel):
    """List of available colleges"""
    colleges: List[CollegeOption] = Field(..., description="Available colleges")
    total: int = Field(..., description="Total number of colleges")

class SelectCollegeRequest(BaseModel):
    """Select college request"""
    collegeId: str = Field(..., description="Selected college UUID")

class SelectCollegeResponse(BaseModel):
    """Select college response"""
    success: bool = True
    message: str = "College selected successfully"
    nextStep: str = "term_selection"
    selectedCollege: CollegeOption


# ==================== TERM SELECTION SCHEMAS ====================

class TermOption(BaseModel):
    """Term selection option"""
    termId: str = Field(..., description="Term UUID")
    name: str = Field(..., description="Term name")
    startDate: datetime = Field(..., description="Term start date")
    endDate: datetime = Field(..., description="Term end date")
    isActive: bool = Field(..., description="Term active status")

class TermListResponse(BaseModel):
    """List of available terms for selected college"""
    terms: List[TermOption] = Field(..., description="Available terms")
    total: int = Field(..., description="Total number of terms")
    collegeId: str = Field(..., description="Selected college ID")

class SelectTermRequest(BaseModel):
    """Select term request"""
    termId: str = Field(..., description="Selected term UUID")

class SelectTermResponse(BaseModel):
    """Select term response"""
    success: bool = True
    message: str = "Term selected successfully"
    nextStep: str = "graduation_selection"
    selectedTerm: TermOption


# ==================== GRADUATION SELECTION SCHEMAS ====================

class GraduationOption(BaseModel):
    """Graduation level selection option"""
    graduationId: str = Field(..., description="Graduation UUID")
    name: str = Field(..., description="Graduation name")
    code: str = Field(..., description="Graduation code")

class GraduationListResponse(BaseModel):
    """List of available graduation levels"""
    graduations: List[GraduationOption] = Field(..., description="Available graduation levels")
    total: int = Field(..., description="Total number of graduations")
    collegeId: str = Field(..., description="Selected college ID")

class SelectGraduationRequest(BaseModel):
    """Select graduation request"""
    graduationId: str = Field(..., description="Selected graduation UUID")

class SelectGraduationResponse(BaseModel):
    """Select graduation response"""
    success: bool = True
    message: str = "Graduation level selected successfully"
    nextStep: str = "degree_selection"
    selectedGraduation: GraduationOption


# ==================== DEGREE SELECTION SCHEMAS ====================

class DegreeOption(BaseModel):
    """Degree selection option"""
    degreeId: str = Field(..., description="Degree UUID")
    name: str = Field(..., description="Degree name")
    code: str = Field(..., description="Degree code")
    durationYears: int = Field(..., description="Degree duration in years")

class DegreeListResponse(BaseModel):
    """List of available degrees for selected graduation"""
    degrees: List[DegreeOption] = Field(..., description="Available degrees")
    total: int = Field(..., description="Total number of degrees")
    graduationId: str = Field(..., description="Selected graduation ID")

class SelectDegreeRequest(BaseModel):
    """Select degree request"""
    degreeId: str = Field(..., description="Selected degree UUID")

class SelectDegreeResponse(BaseModel):
    """Select degree response"""
    success: bool = True
    message: str = "Degree selected successfully"
    nextStep: str = "branch_selection"
    selectedDegree: DegreeOption


# ==================== BRANCH SELECTION SCHEMAS ====================

class BranchOption(BaseModel):
    """Branch selection option"""
    branchId: str = Field(..., description="Branch UUID")
    name: str = Field(..., description="Branch name")
    code: str = Field(..., description="Branch code")

class BranchListResponse(BaseModel):
    """List of available branches for selected degree"""
    branches: List[BranchOption] = Field(..., description="Available branches")
    total: int = Field(..., description="Total number of branches")
    degreeId: str = Field(..., description="Selected degree ID")

class SelectBranchRequest(BaseModel):
    """Select branch request"""
    branchId: str = Field(..., description="Selected branch UUID")

class SelectBranchResponse(BaseModel):
    """Select branch response"""
    success: bool = True
    message: str = "Branch selected successfully"
    nextStep: str = "section_selection"
    selectedBranch: BranchOption


# ==================== SECTION SELECTION SCHEMAS ====================

class SectionOption(BaseModel):
    """Section selection option"""
    sectionId: str = Field(..., description="Section UUID")
    sectionName: str = Field(..., description="Section name")
    sectionCode: str = Field(..., description="Section code")
    studentCapacity: int = Field(..., description="Section capacity")
    currentStrength: int = Field(..., description="Current enrolled students")
    availableSlots: int = Field(..., description="Available slots")
    classTeacher: Optional[str] = Field(None, description="Class teacher name")

class SectionStatusOption(BaseModel):
    """Simplified section option for registration status (no capacity/teacher details)"""
    sectionId: str = Field(..., description="Section UUID")
    sectionName: str = Field(..., description="Section name")
    sectionCode: str = Field(..., description="Section code")

class SectionListResponse(BaseModel):
    """List of available sections for selected branch"""
    sections: List[SectionOption] = Field(..., description="Available sections")
    total: int = Field(..., description="Total number of sections")
    branchId: str = Field(..., description="Selected branch ID")

class SelectSectionRequest(BaseModel):
    """Select section request - Final selection"""
    sectionId: str = Field(..., description="Selected section UUID")

class SelectSectionResponse(BaseModel):
    """Select section response - Registration complete"""
    success: bool = True
    message: str = "Registration completed successfully! Welcome to your academic program."
    nextStep: str = "completed"
    selectedSection: SectionOption
    studentProfile: Dict[str, Any] = Field(..., description="Updated student profile")
    admissionNumber: Optional[str] = Field(None, description="Generated admission number")


# ==================== USER DETAILS STEP SCHEMAS ====================

class UserDetailsRequest(BaseModel):
    """User details request - Final step with personal information"""
    fullName: str = Field(..., min_length=2, max_length=200, description="Student full name")
    gender: str = Field(..., description="Student gender")
    rollNumber: str = Field(..., min_length=1, max_length=50, description="Student roll number")
    email: Optional[str] = Field(None, description="Student email (optional)")
    
    @validator('fullName')
    def validate_full_name(cls, v):
        if not v.strip():
            raise ValueError('Full name cannot be empty')
        return ' '.join(v.strip().split())
    
    @validator('gender')
    def validate_gender(cls, v):
        allowed_genders = ['male', 'female', 'other']
        if v.lower() not in allowed_genders:
            raise ValueError(f'Gender must be one of: {", ".join(allowed_genders)}')
        return v.lower()
    
    @validator('rollNumber')
    def validate_roll_number(cls, v):
        if not v.strip():
            raise ValueError('Roll number cannot be empty')
        return v.strip().upper()

class UserDetailsResponse(BaseModel):
    """User details response - Registration completed"""
    success: bool = True
    message: str = "Registration completed successfully. Waiting for college approval."
    nextStep: str = "approval_pending"
    studentProfile: Dict[str, Any] = Field(..., description="Complete student profile")
    admissionNumber: str = Field(..., description="Generated admission number")


# ==================== REGISTRATION STATUS SCHEMAS ====================

class RegistrationStepDetails(BaseModel):
    """Details for each registration step"""
    college: Optional[CollegeOption] = None
    rollNumber: Optional[str] = None
    term: Optional[TermOption] = None
    graduation: Optional[GraduationOption] = None
    degree: Optional[DegreeOption] = None
    branch: Optional[BranchOption] = None
    section: Optional[SectionStatusOption] = None

class RegistrationStatusResponse(BaseModel):
    """Current registration status and progress"""
    currentStep: str = Field(..., description="Current step in registration")
    progressPercentage: int = Field(..., ge=0, le=100, description="Progress percentage")
    registrationCompleted: bool = Field(..., description="Registration completion status")
    approvalStatus: str = Field(..., description="Approval status: pending, approved, rejected")
    canAccessApp: bool = Field(..., description="Can access main app features")
    stepDetails: RegistrationStepDetails = Field(..., description="Details of completed steps")
    nextAction: str = Field(..., description="What the student should do next")
    updatedAt: datetime = Field(..., description="Last update timestamp")

class ResetRegistrationRequest(BaseModel):
    """Reset registration request"""
    confirmReset: bool = Field(..., description="Confirmation to reset registration")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for reset")

class ResetRegistrationResponse(BaseModel):
    """Reset registration response"""
    success: bool = True
    message: str = "Registration reset successfully. You can start the process again."
    currentStep: str = "college_selection"
    progressPercentage: int = 0


# ==================== COMMON SCHEMAS ====================

class RegistrationErrorResponse(BaseModel):
    """Registration flow error response"""
    statusCode: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Error message")
    success: bool = False
    timestamp: float = Field(..., description="Error timestamp")
    currentStep: Optional[str] = Field(None, description="Current registration step")
    
class RegistrationValidationError(BaseModel):
    """Registration validation error details"""
    field: str = Field(..., description="Field with validation error")
    message: str = Field(..., description="Validation error message")
    currentValue: Optional[str] = Field(None, description="Current invalid value")

class DetailedRegistrationErrorResponse(BaseModel):
    """Detailed registration error with validation details"""
    statusCode: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Main error message")
    success: bool = False
    timestamp: float = Field(..., description="Error timestamp")
    validationErrors: List[RegistrationValidationError] = Field(..., description="Validation error details")


# ==================== SUMMARY SCHEMAS ====================

class RegistrationSummary(BaseModel):
    """Complete registration summary"""
    student: Dict[str, Any] = Field(..., description="Student profile")
    college: CollegeOption = Field(..., description="Selected college")
    term: TermOption = Field(..., description="Selected term")
    graduation: GraduationOption = Field(..., description="Selected graduation")
    degree: DegreeOption = Field(..., description="Selected degree")
    branch: BranchOption = Field(..., description="Selected branch")
    section: SectionOption = Field(..., description="Selected section")
    completedAt: datetime = Field(..., description="Registration completion timestamp")
    admissionNumber: str = Field(..., description="Student admission number")

class RegistrationSummaryResponse(BaseModel):
    """Registration summary response"""
    success: bool = True
    message: str = "Registration summary retrieved successfully"
    summary: RegistrationSummary