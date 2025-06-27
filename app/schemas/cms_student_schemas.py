"""
CMS Student Management Schemas
Pydantic schemas for student search, approval, and management by college staff
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.utils import CamelCaseModel


# ==================== STUDENT SEARCH SCHEMAS ====================

class StudentSearchFilters(BaseModel):
    """Applied search filters for reference"""
    collegeName: str = Field(..., description="College name")
    termName: Optional[str] = Field(None, description="Term name if filtered")
    graduationName: Optional[str] = Field(None, description="Graduation name if filtered")
    degreeName: Optional[str] = Field(None, description="Degree name if filtered")
    branchName: Optional[str] = Field(None, description="Branch name if filtered")
    sectionName: Optional[str] = Field(None, description="Section name if filtered")
    approved: bool = Field(..., description="Approval filter applied")


class StudentSearchResult(BaseModel):
    """Individual student in search results"""
    studentId: str = Field(..., description="Student UUID")
    fullName: str = Field(..., description="Student full name")
    email: str = Field(..., description="Student email")
    rollNumber: Optional[str] = Field(None, description="Student roll number")
    admissionNumber: Optional[str] = Field(None, description="Student admission number")
    approvalStatus: str = Field(..., description="Approval status: pending, approved, rejected")
    approvedAt: Optional[datetime] = Field(None, description="Approval timestamp")
    approvedByStaffName: Optional[str] = Field(None, description="Staff who approved")
    rejectionReason: Optional[str] = Field(None, description="Rejection reason if rejected")
    registrationCompletedAt: Optional[datetime] = Field(None, description="Registration completion time")
    
    # Academic details
    sectionName: Optional[str] = Field(None, description="Section name")
    sectionCode: Optional[str] = Field(None, description="Section code")
    branchName: Optional[str] = Field(None, description="Branch name")
    branchCode: Optional[str] = Field(None, description="Branch code")
    degreeName: Optional[str] = Field(None, description="Degree name")
    graduationName: Optional[str] = Field(None, description="Graduation name")
    termName: Optional[str] = Field(None, description="Term name")
    
    # Activity tracking
    lastLoginAt: Optional[datetime] = Field(None, description="Last login timestamp")
    loginCount: int = Field(0, description="Total login count")
    isActive: bool = Field(True, description="Account active status")
    
    # Timestamps
    createdAt: datetime = Field(..., description="Account creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")


class StudentSearchResponse(BaseModel):
    """Student search results with pagination"""
    students: List[StudentSearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of students matching criteria")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    appliedFilters: StudentSearchFilters = Field(..., description="Applied search filters")


# ==================== STUDENT APPROVAL SCHEMAS ====================

class ApproveStudentRequest(CamelCaseModel):
    """Request to approve a student"""
    approval_reason: Optional[str] = Field(None, max_length=500, description="Optional approval reason/note")


class RejectStudentRequest(CamelCaseModel):
    """Request to reject a student"""
    rejection_reason: str = Field(..., min_length=5, max_length=500, description="Required rejection reason")


class StudentApprovalResponse(CamelCaseModel):
    """Response for student approval/rejection actions"""
    success: bool = True
    message: str = Field(..., description="Action result message")
    student_id: str = Field(..., description="Student UUID")
    student_name: str = Field(..., description="Student full name")
    roll_number: Optional[str] = Field(None, description="Student roll number")
    approval_status: str = Field(..., description="New approval status")
    approved_by_staff_name: str = Field(..., description="Staff member who performed the action")
    action_timestamp: datetime = Field(..., description="When the action was performed")


# ==================== STUDENT DETAILS SCHEMAS ====================

class StudentDetailResponse(BaseModel):
    """Detailed student information for CMS staff"""
    # Basic information
    studentId: str = Field(..., description="Student UUID")
    fullName: str = Field(..., description="Student full name")
    email: str = Field(..., description="Student email")
    rollNumber: Optional[str] = Field(None, description="Student roll number")
    admissionNumber: Optional[str] = Field(None, description="Student admission number")
    
    # Account status
    isActive: bool = Field(..., description="Account active status")
    isVerified: bool = Field(..., description="Email verification status")
    registrationCompleted: bool = Field(..., description="Registration completion status")
    
    # Approval workflow
    approvalStatus: str = Field(..., description="Approval status")
    approvedAt: Optional[datetime] = Field(None, description="Approval timestamp")
    approvedByStaffName: Optional[str] = Field(None, description="Staff who approved")
    rejectionReason: Optional[str] = Field(None, description="Rejection reason")
    
    # Academic assignment
    collegeName: str = Field(..., description="College name")
    sectionName: Optional[str] = Field(None, description="Section name")
    sectionCode: Optional[str] = Field(None, description="Section code")
    branchName: Optional[str] = Field(None, description="Branch name")
    degreeName: Optional[str] = Field(None, description="Degree name")
    graduationName: Optional[str] = Field(None, description="Graduation name")
    termName: Optional[str] = Field(None, description="Term name")
    
    # Activity tracking
    lastLoginAt: Optional[datetime] = Field(None, description="Last login timestamp")
    loginCount: int = Field(0, description="Total login count")
    emailVerifiedAt: Optional[datetime] = Field(None, description="Email verification timestamp")
    
    # Registration details
    registrationDetails: Dict[str, Any] = Field(default_factory=dict, description="Registration step details")
    
    # Timestamps
    createdAt: datetime = Field(..., description="Account creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")


# ==================== BULK OPERATIONS SCHEMAS ====================

class BulkApprovalRequest(CamelCaseModel):
    """Bulk approve multiple students"""
    student_ids: List[str] = Field(..., min_items=1, max_items=100, description="List of student UUIDs to approve")
    approval_reason: Optional[str] = Field(None, max_length=500, description="Optional reason for bulk approval")


class BulkApprovalResponse(CamelCaseModel):
    """Response for bulk approval operation"""
    success: bool = True
    message: str = Field(..., description="Bulk operation result")
    total_requested: int = Field(..., description="Total students requested for approval")
    successful_approvals: int = Field(..., description="Number of successful approvals")
    failed_approvals: int = Field(..., description="Number of failed approvals")
    approved_students: List[str] = Field(..., description="List of successfully approved student names")
    failed_students: List[Dict[str, str]] = Field(..., description="List of failed approvals with reasons")
    approved_by_staff_name: str = Field(..., description="Staff member who performed bulk approval")
    action_timestamp: datetime = Field(..., description="When the bulk action was performed")


# ==================== STATISTICS SCHEMAS ====================

class StudentStatistics(BaseModel):
    """Student statistics for dashboard"""
    totalStudents: int = Field(..., description="Total students in college")
    pendingApprovals: int = Field(..., description="Students pending approval")
    approvedStudents: int = Field(..., description="Approved students")
    rejectedStudents: int = Field(..., description="Rejected students")
    activeStudents: int = Field(..., description="Active students (logged in recently)")
    recentRegistrations: int = Field(..., description="Registrations in last 7 days")
    
    # Breakdown by academic levels
    byGraduation: Dict[str, int] = Field(default_factory=dict, description="Students by graduation level")
    byDegree: Dict[str, int] = Field(default_factory=dict, description="Students by degree")
    byBranch: Dict[str, int] = Field(default_factory=dict, description="Students by branch")
    bySection: Dict[str, int] = Field(default_factory=dict, description="Students by section")


class StudentStatisticsResponse(BaseModel):
    """Response for student statistics"""
    success: bool = True
    message: str = "Student statistics retrieved successfully"
    collegeName: str = Field(..., description="College name")
    statistics: StudentStatistics = Field(..., description="Detailed statistics")
    generatedAt: datetime = Field(..., description="When statistics were generated")


# ==================== ERROR SCHEMAS ====================

class StudentManagementError(BaseModel):
    """Student management error response"""
    statusCode: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Error message")
    success: bool = False
    timestamp: datetime = Field(..., description="Error timestamp")
    studentId: Optional[str] = Field(None, description="Student ID if applicable")
    action: Optional[str] = Field(None, description="Action that failed")