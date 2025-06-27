"""
CMS Student Management API
Search, approval, and management endpoints for college staff
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List
import uuid
import logging

from app.database import get_db
from app.models.staff import Staff
from app.models.student import Student
from app.models.college import College
from app.models.term import Term
from app.models.graduation import Graduation
from app.models.degree import Degree
from app.models.branch import Branch
from app.models.section import Section
from app.schemas.cms_student_schemas import (
    StudentSearchResponse, StudentSearchResult, StudentSearchFilters,
    ApproveStudentRequest, RejectStudentRequest, StudentApprovalResponse,
    StudentDetailResponse
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/students", tags=["CMS Student Management"])
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


@router.get("/search", response_model=StudentSearchResponse, dependencies=[Depends(security)])
async def search_students(
    college_id: Optional[str] = Query(None, description="Filter by college ID"),
    term_id: Optional[str] = Query(None, description="Filter by term ID"),
    graduation_id: Optional[str] = Query(None, description="Filter by graduation ID"),
    degree_id: Optional[str] = Query(None, description="Filter by degree ID"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    section_id: Optional[str] = Query(None, description="Filter by section ID"),
    roll_number: Optional[str] = Query(None, description="Search by roll number"),
    approved: Optional[bool] = Query(True, description="Filter by approval status (default: approved only)"),
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Search students with hierarchical filtering.
    Default behavior: Returns only approved students unless approved=false.
    """
    try:
        # Use current staff's college if college_id not provided
        target_college_id = college_id or str(current_staff.college_id)
        
        # Verify staff has access to requested college
        if college_id and college_id != str(current_staff.college_id):
            # Only principals and college admins can search across colleges (future feature)
            if current_staff.cms_role not in ["principal"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only search students in your own college"
                )
        
        # Get college info for response
        college_result = await db.execute(
            select(College).where(College.college_id == target_college_id)
        )
        college = college_result.scalar_one_or_none()
        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College not found"
            )
        
        # Build hierarchical query with joins
        query = (
            select(
                Student,
                Section.section_name,
                Section.section_code,
                Branch.branch_name,
                Branch.branch_code,
                Degree.degree_name,
                Graduation.graduation_name,
                Term.term_name,
                Staff.full_name.label("approved_by_staff_name")
            )
            .outerjoin(Section, Student.section_id == Section.section_id)
            .outerjoin(Branch, Section.branch_id == Branch.branch_id)
            .outerjoin(Degree, Branch.degree_id == Degree.degree_id)
            .outerjoin(Graduation, Degree.graduation_id == Graduation.graduation_id)
            .outerjoin(Term, Graduation.term_id == Term.term_id)
            .outerjoin(Staff, Student.approved_by_staff_id == Staff.staff_id)
            .where(Student.college_id == target_college_id)
        )
        
        # Apply approval filter
        if approved is True:
            query = query.where(Student.approval_status == "approved")
        elif approved is False:
            query = query.where(Student.approval_status.in_(["pending", "rejected"]))
        
        # Apply hierarchical filters
        if term_id:
            query = query.where(Term.term_id == term_id)
        if graduation_id:
            query = query.where(Graduation.graduation_id == graduation_id)
        if degree_id:
            query = query.where(Degree.degree_id == degree_id)
        if branch_id:
            query = query.where(Branch.branch_id == branch_id)
        if section_id:
            query = query.where(Section.section_id == section_id)
        
        # Apply roll number search (exact match or partial)
        if roll_number:
            roll_number = roll_number.strip()
            query = query.where(Student.roll_number.ilike(f"%{roll_number}%"))
        
        # Order by approval status (pending first), then by name
        query = query.order_by(
            Student.approval_status.desc(),  # pending > approved > rejected
            Student.full_name
        )
        
        # Get additional filter names for response
        filter_names = {}
        if term_id:
            term_result = await db.execute(select(Term.term_name).where(Term.term_id == term_id))
            filter_names["termName"] = term_result.scalar()
        if graduation_id:
            grad_result = await db.execute(select(Graduation.graduation_name).where(Graduation.graduation_id == graduation_id))
            filter_names["graduationName"] = grad_result.scalar()
        if degree_id:
            degree_result = await db.execute(select(Degree.degree_name).where(Degree.degree_id == degree_id))
            filter_names["degreeName"] = degree_result.scalar()
        if branch_id:
            branch_result = await db.execute(select(Branch.branch_name).where(Branch.branch_id == branch_id))
            filter_names["branchName"] = branch_result.scalar()
        if section_id:
            section_result = await db.execute(select(Section.section_name).where(Section.section_id == section_id))
            filter_names["sectionName"] = section_result.scalar()
        
        # Execute paginated query
        paginated_result = await sqlalchemy_paginate(db, query)
        
        # Build response
        student_results = []
        for row in paginated_result.items:
            student = row[0]  # Student object
            section_name = row[1]
            section_code = row[2]
            branch_name = row[3]
            branch_code = row[4]
            degree_name = row[5]
            graduation_name = row[6]
            term_name = row[7]
            approved_by_staff_name = row[8]
            
            # Parse registration completion timestamp
            registration_completed_at = None
            if student.registration_details and student.registration_details.get("completed_at"):
                try:
                    from datetime import datetime
                    registration_completed_at = datetime.fromisoformat(
                        student.registration_details["completed_at"].replace("Z", "+00:00")
                    )
                except (ValueError, KeyError):
                    pass
            
            student_results.append(StudentSearchResult(
                studentId=str(student.student_id),
                fullName=student.full_name,
                email=student.email,
                rollNumber=student.roll_number,
                admissionNumber=student.admission_number,
                approvalStatus=student.approval_status,
                approvedAt=student.approved_at,
                approvedByStaffName=approved_by_staff_name,
                rejectionReason=student.rejection_reason,
                registrationCompletedAt=registration_completed_at,
                sectionName=section_name,
                sectionCode=section_code,
                branchName=branch_name,
                branchCode=branch_code,
                degreeName=degree_name,
                graduationName=graduation_name,
                termName=term_name,
                lastLoginAt=student.last_login_at,
                loginCount=student.login_count,
                isActive=student.is_active,
                createdAt=student.created_at,
                updatedAt=student.updated_at
            ))
        
        # Build applied filters
        applied_filters = StudentSearchFilters(
            collegeName=college.name,
            termName=filter_names.get("termName"),
            graduationName=filter_names.get("graduationName"),
            degreeName=filter_names.get("degreeName"),
            branchName=filter_names.get("branchName"),
            sectionName=filter_names.get("sectionName"),
            approved=approved if approved is not None else True
        )
        
        return StudentSearchResponse(
            students=student_results,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
            appliedFilters=applied_filters
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching students: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching students"
        )


@router.get("/{student_id}", response_model=StudentDetailResponse, dependencies=[Depends(security)])
async def get_student_details(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get detailed information about a specific student"""
    try:
        # Get student with all related data
        result = await db.execute(
            select(Student)
            .options(
                selectinload(Student.college),
                selectinload(Student.section),
                selectinload(Student.approved_by_staff)
            )
            .where(Student.student_id == student_id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Verify staff has access to this student's college
        if student.college_id != current_staff.college_id:
            if current_staff.cms_role not in ["principal"]:  # Future: cross-college access
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view students from your college"
                )
        
        # Get academic hierarchy details
        academic_details = {}
        if student.section_id:
            academic_result = await db.execute(
                select(
                    Section.section_name,
                    Section.section_code,
                    Branch.branch_name,
                    Degree.degree_name,
                    Graduation.graduation_name,
                    Term.term_name
                )
                .select_from(Section)
                .join(Branch, Section.branch_id == Branch.branch_id)
                .join(Degree, Branch.degree_id == Degree.degree_id)
                .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
                .join(Term, Graduation.term_id == Term.term_id)
                .where(Section.section_id == student.section_id)
            )
            academic_row = academic_result.first()
            if academic_row:
                academic_details = {
                    "sectionName": academic_row[0],
                    "sectionCode": academic_row[1],
                    "branchName": academic_row[2],
                    "degreeName": academic_row[3],
                    "graduationName": academic_row[4],
                    "termName": academic_row[5]
                }
        
        return StudentDetailResponse(
            studentId=str(student.student_id),
            fullName=student.full_name,
            email=student.email,
            rollNumber=student.roll_number,
            admissionNumber=student.admission_number,
            isActive=student.is_active,
            isVerified=student.is_verified,
            registrationCompleted=student.registration_completed,
            approvalStatus=student.approval_status,
            approvedAt=student.approved_at,
            approvedByStaffName=student.approved_by_staff.full_name if student.approved_by_staff else None,
            rejectionReason=student.rejection_reason,
            collegeName=student.college.name if student.college else "Unknown",
            sectionName=academic_details.get("sectionName"),
            sectionCode=academic_details.get("sectionCode"),
            branchName=academic_details.get("branchName"),
            degreeName=academic_details.get("degreeName"),
            graduationName=academic_details.get("graduationName"),
            termName=academic_details.get("termName"),
            lastLoginAt=student.last_login_at,
            loginCount=student.login_count,
            emailVerifiedAt=student.email_verified_at,
            registrationDetails=student.registration_details or {},
            createdAt=student.created_at,
            updatedAt=student.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting student details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving student details"
        )


@router.put("/{student_id}/approve", response_model=StudentApprovalResponse, dependencies=[Depends(security)])
async def approve_student(
    student_id: str,
    request: ApproveStudentRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Approve a student registration. Only Principal and College Admin can approve students."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can approve students"
            )
        
        # Get student
        result = await db.execute(
            select(Student).where(Student.student_id == student_id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Verify student belongs to staff's college
        if student.college_id != current_staff.college_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only approve students from your college"
            )
        
        # Check if student registration is completed
        if not student.registration_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot approve student with incomplete registration"
            )
        
        # Check if already approved
        if student.approval_status == "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student is already approved"
            )
        
        # Approve student
        student.approve_student(current_staff.staff_id)
        await db.commit()
        
        logger.info(f"Student {student.full_name} ({student_id}) approved by {current_staff.full_name}")
        
        return StudentApprovalResponse(
            success=True,
            message=f"Student '{student.full_name}' approved successfully",
            studentId=str(student.student_id),
            studentName=student.full_name,
            rollNumber=student.roll_number,
            approvalStatus=student.approval_status,
            approvedByStaffName=current_staff.full_name,
            actionTimestamp=student.approved_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error approving student: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error approving student"
        )


@router.put("/{student_id}/reject", response_model=StudentApprovalResponse, dependencies=[Depends(security)])
async def reject_student(
    student_id: str,
    request: RejectStudentRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Reject a student registration. Only Principal and College Admin can reject students."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can reject students"
            )
        
        # Get student
        result = await db.execute(
            select(Student).where(Student.student_id == student_id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Verify student belongs to staff's college
        if student.college_id != current_staff.college_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reject students from your college"
            )
        
        # Check if student registration is completed
        if not student.registration_completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reject student with incomplete registration"
            )
        
        # Check if already rejected
        if student.approval_status == "rejected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student is already rejected"
            )
        
        # Reject student
        student.reject_student(current_staff.staff_id, request.rejection_reason)
        await db.commit()
        
        logger.info(f"Student {student.full_name} ({student_id}) rejected by {current_staff.full_name}")
        
        return StudentApprovalResponse(
            success=True,
            message=f"Student '{student.full_name}' rejected successfully",
            studentId=str(student.student_id),
            studentName=student.full_name,
            rollNumber=student.roll_number,
            approvalStatus=student.approval_status,
            approvedByStaffName=current_staff.full_name,
            actionTimestamp=student.approved_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error rejecting student: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error rejecting student"
        )