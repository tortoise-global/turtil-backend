"""
Student Registration Flow API
Step-by-step academic registration for students
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
import datetime

from app.database import get_db
from app.models.student import Student
from app.models.college import College
from app.models.term import Term
from app.models.graduation import Graduation
from app.models.degree import Degree
from app.models.branch import Branch
from app.models.section import Section
from app.api.student.deps import check_registration_in_progress
from app.schemas.student_registration_schemas import (
    CollegeListResponse, CollegeOption,
    SelectCollegeRequest, SelectCollegeResponse,
    TermListResponse, TermOption,
    SelectTermRequest, SelectTermResponse,
    GraduationListResponse, GraduationOption,
    SelectGraduationRequest, SelectGraduationResponse,
    DegreeListResponse, DegreeOption,
    SelectDegreeRequest, SelectDegreeResponse,
    BranchListResponse, BranchOption,
    SelectBranchRequest, SelectBranchResponse,
    SectionListResponse, SectionOption, SectionStatusOption,
    SelectSectionRequest, SelectSectionResponse,
    UserDetailsRequest, UserDetailsResponse,
    RegistrationStatusResponse, RegistrationStepDetails,
    ResetRegistrationRequest, ResetRegistrationResponse
)
import logging

router = APIRouter(prefix="/registration", tags=["Student Registration"])
logger = logging.getLogger(__name__)


@router.get("/colleges", response_model=CollegeListResponse)
async def get_available_colleges(
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Get list of available colleges for student registration"""
    try:
        # Get all active colleges
        result = await db.execute(
            select(College)
            .where(College.auto_approved == True)
            .order_by(College.name)
        )
        colleges = result.scalars().all()
        
        college_options = []
        for college in colleges:
            college_options.append(CollegeOption(
                collegeId=str(college.college_id),
                name=college.name,
                shortName=college.short_name or college.name,
                city=college.city or "Unknown",
                state=college.state or "Unknown",
                logoUrl=college.logo_url
            ))
        
        return CollegeListResponse(
            colleges=college_options,
            total=len(college_options)
        )
        
    except Exception as e:
        logger.error(f"Get colleges error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch colleges"
        )


@router.put("/college", response_model=SelectCollegeResponse)
async def select_college(
    request: SelectCollegeRequest,
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Select college, then move to term selection"""
    try:
        student = current_session["student"]
        college_id = request.collegeId
        
        # Validate college exists
        result = await db.execute(
            select(College).where(College.college_id == college_id)
        )
        college = result.scalar_one_or_none()
        
        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College not found"
            )
        
        if not college.auto_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="College is not available for self-registration"
            )
        
        # Update student registration details (with approval reset)
        student.update_registration_step("term_selection", {
            "college_id": college_id,
            "college_name": college.name
        }, reset_approval=True)
        await db.commit()
        
        selected_college = CollegeOption(
            collegeId=str(college.college_id),
            name=college.name,
            shortName=college.short_name or college.name,
            city=college.city or "Unknown",
            state=college.state or "Unknown",
            logoUrl=college.logo_url
        )
        
        logger.info(f"Student {student.student_id} selected college {college.name}")
        
        return SelectCollegeResponse(
            selectedCollege=selected_college
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Select college error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select college"
        )


@router.get("/terms", response_model=TermListResponse)
async def get_available_terms(
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Get available terms for selected college"""
    try:
        student = current_session["student"]
        
        # Check if college is selected
        if not student.registration_details or "college_id" not in student.registration_details:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a college first"
            )
        
        college_id = student.registration_details["college_id"]
        
        # Get active terms for the college
        result = await db.execute(
            select(Term)
            .where(Term.college_id == college_id)
            .where(Term.is_active == True)
            .order_by(Term.start_date.desc())
        )
        terms = result.scalars().all()
        
        term_options = []
        for term in terms:
            term_options.append(TermOption(
                termId=str(term.term_id),
                name=term.name,
                startDate=term.start_date,
                endDate=term.end_date,
                isActive=term.is_active
            ))
        
        return TermListResponse(
            terms=term_options,
            total=len(term_options),
            collegeId=college_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get terms error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch terms"
        )


@router.put("/term", response_model=SelectTermResponse)
async def select_term(
    request: SelectTermRequest,
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Select term and move to graduation selection"""
    try:
        student = current_session["student"]
        term_id = request.termId
        
        # Validate term exists and belongs to selected college
        college_id = student.registration_details.get("college_id")
        if not college_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a college first"
            )
        
        result = await db.execute(
            select(Term).where(Term.term_id == term_id).where(Term.college_id == college_id)
        )
        term = result.scalar_one_or_none()
        
        if not term:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Term not found for selected college"
            )
        
        if not term.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected term is not active"
            )
        
        # Update student registration details (with approval reset)
        student.update_registration_step("graduation_selection", {
            **student.registration_details,
            "term_id": term_id,
            "term_name": term.name
        }, reset_approval=True)
        await db.commit()
        
        selected_term = TermOption(
            termId=str(term.term_id),
            name=term.name,
            startDate=term.start_date,
            endDate=term.end_date,
            isActive=term.is_active
        )
        
        logger.info(f"Student {student.student_id} selected term {term.name}")
        
        return SelectTermResponse(selectedTerm=selected_term)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Select term error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select term"
        )


@router.get("/graduations", response_model=GraduationListResponse)
async def get_available_graduations(
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Get available graduation levels for selected college"""
    try:
        student = current_session["student"]
        
        # Check if college is selected
        college_id = student.registration_details.get("college_id")
        if not college_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a college first"
            )
        
        # Get graduations for the college
        result = await db.execute(
            select(Graduation)
            .where(Graduation.college_id == college_id)
            .order_by(Graduation.name)
        )
        graduations = result.scalars().all()
        
        graduation_options = []
        for graduation in graduations:
            graduation_options.append(GraduationOption(
                graduationId=str(graduation.graduation_id),
                name=graduation.name,
                code=graduation.code
            ))
        
        return GraduationListResponse(
            graduations=graduation_options,
            total=len(graduation_options),
            collegeId=college_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get graduations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch graduations"
        )


@router.put("/graduation", response_model=SelectGraduationResponse)
async def select_graduation(
    request: SelectGraduationRequest,
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Select graduation level and move to degree selection"""
    try:
        student = current_session["student"]
        graduation_id = request.graduationId
        
        # Validate graduation exists and belongs to selected college
        college_id = student.registration_details.get("college_id")
        if not college_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a college first"
            )
        
        result = await db.execute(
            select(Graduation).where(Graduation.graduation_id == graduation_id).where(Graduation.college_id == college_id)
        )
        graduation = result.scalar_one_or_none()
        
        if not graduation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graduation level not found for selected college"
            )
        
        # Update student registration details (with approval reset)
        student.update_registration_step("degree_selection", {
            **student.registration_details,
            "graduation_id": graduation_id,
            "graduation_name": graduation.name
        }, reset_approval=True)
        await db.commit()
        
        selected_graduation = GraduationOption(
            graduationId=str(graduation.graduation_id),
            name=graduation.name,
            code=graduation.code
        )
        
        logger.info(f"Student {student.student_id} selected graduation {graduation.name}")
        
        return SelectGraduationResponse(selectedGraduation=selected_graduation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Select graduation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select graduation"
        )


@router.get("/degrees", response_model=DegreeListResponse)
async def get_available_degrees(
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Get available degrees for selected graduation"""
    try:
        student = current_session["student"]
        
        # Check if graduation is selected
        graduation_id = student.registration_details.get("graduation_id")
        if not graduation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a graduation level first"
            )
        
        # Get degrees for the graduation
        result = await db.execute(
            select(Degree)
            .where(Degree.graduation_id == graduation_id)
            .order_by(Degree.name)
        )
        degrees = result.scalars().all()
        
        degree_options = []
        for degree in degrees:
            degree_options.append(DegreeOption(
                degreeId=str(degree.degree_id),
                name=degree.name,
                code=degree.code,
                durationYears=degree.duration_years
            ))
        
        return DegreeListResponse(
            degrees=degree_options,
            total=len(degree_options),
            graduationId=graduation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get degrees error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch degrees"
        )


@router.put("/degree", response_model=SelectDegreeResponse)
async def select_degree(
    request: SelectDegreeRequest,
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Select degree and move to branch selection"""
    try:
        student = current_session["student"]
        degree_id = request.degreeId
        
        # Validate degree exists and belongs to selected graduation
        graduation_id = student.registration_details.get("graduation_id")
        if not graduation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a graduation level first"
            )
        
        result = await db.execute(
            select(Degree).where(Degree.degree_id == degree_id).where(Degree.graduation_id == graduation_id)
        )
        degree = result.scalar_one_or_none()
        
        if not degree:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Degree not found for selected graduation"
            )
        
        # Update student registration details (with approval reset)
        student.update_registration_step("branch_selection", {
            **student.registration_details,
            "degree_id": degree_id,
            "degree_name": degree.name
        }, reset_approval=True)
        await db.commit()
        
        selected_degree = DegreeOption(
            degreeId=str(degree.degree_id),
            name=degree.name,
            code=degree.code,
            durationYears=degree.duration_years
        )
        
        logger.info(f"Student {student.student_id} selected degree {degree.name}")
        
        return SelectDegreeResponse(selectedDegree=selected_degree)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Select degree error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select degree"
        )


@router.get("/branches", response_model=BranchListResponse)
async def get_available_branches(
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Get available branches for selected degree"""
    try:
        student = current_session["student"]
        
        # Check if degree is selected
        degree_id = student.registration_details.get("degree_id")
        if not degree_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a degree first"
            )
        
        # Get branches for the degree
        result = await db.execute(
            select(Branch)
            .where(Branch.degree_id == degree_id)
            .order_by(Branch.name)
        )
        branches = result.scalars().all()
        
        branch_options = []
        for branch in branches:
            branch_options.append(BranchOption(
                branchId=str(branch.branch_id),
                name=branch.name,
                code=branch.code
            ))
        
        return BranchListResponse(
            branches=branch_options,
            total=len(branch_options),
            degreeId=degree_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get branches error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch branches"
        )


@router.put("/branch", response_model=SelectBranchResponse)
async def select_branch(
    request: SelectBranchRequest,
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Select branch and move to section selection"""
    try:
        student = current_session["student"]
        branch_id = request.branchId
        
        # Validate branch exists and belongs to selected degree
        degree_id = student.registration_details.get("degree_id")
        if not degree_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a degree first"
            )
        
        result = await db.execute(
            select(Branch).where(Branch.branch_id == branch_id).where(Branch.degree_id == degree_id)
        )
        branch = result.scalar_one_or_none()
        
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found for selected degree"
            )
        
        # Update student registration details (with approval reset)
        student.update_registration_step("section_selection", {
            **student.registration_details,
            "branch_id": branch_id,
            "branch_name": branch.name
        }, reset_approval=True)
        await db.commit()
        
        selected_branch = BranchOption(
            branchId=str(branch.branch_id),
            name=branch.name,
            code=branch.code
        )
        
        logger.info(f"Student {student.student_id} selected branch {branch.name}")
        
        return SelectBranchResponse(selectedBranch=selected_branch)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Select branch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select branch"
        )


@router.get("/sections", response_model=SectionListResponse)
async def get_available_sections(
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Get available sections for selected branch"""
    try:
        student = current_session["student"]
        
        # Check if branch is selected
        branch_id = student.registration_details.get("branch_id")
        if not branch_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a branch first"
            )
        
        # Get sections for the branch (with teacher information)
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(Section)
            .options(selectinload(Section.class_teacher))
            .where(Section.branch_id == branch_id)
            .where(Section.current_strength < Section.student_capacity)  # Only show sections with available slots
            .order_by(Section.sequence_order, Section.section_name)
        )
        sections = result.scalars().all()
        
        section_options = []
        for section in sections:
            available_slots = section.student_capacity - section.current_strength
            class_teacher_name = section.class_teacher.full_name if section.class_teacher else None
            
            section_options.append(SectionOption(
                sectionId=str(section.section_id),
                sectionName=section.section_name,
                sectionCode=section.section_code,
                studentCapacity=section.student_capacity,
                currentStrength=section.current_strength,
                availableSlots=available_slots,
                classTeacher=class_teacher_name
            ))
        
        return SectionListResponse(
            sections=section_options,
            total=len(section_options),
            branchId=branch_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get sections error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch sections"
        )


@router.put("/section", response_model=SelectSectionResponse)
async def select_section(
    request: SelectSectionRequest,
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Select section and move to user details step"""
    try:
        student = current_session["student"]
        section_id = request.sectionId
        
        # Validate section exists and belongs to selected branch
        branch_id = student.registration_details.get("branch_id")
        college_id = student.registration_details.get("college_id")
        
        if not branch_id or not college_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete all previous registration steps"
            )
        
        result = await db.execute(
            select(Section).where(Section.section_id == section_id).where(Section.branch_id == branch_id)
        )
        section = result.scalar_one_or_none()
        
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found for selected branch"
            )
        
        # Check if section has available capacity
        if section.current_strength >= section.student_capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected section is full. Please choose another section."
            )
        
        # Update student registration details to move to user_details step
        student.update_registration_step("user_details", {
            **student.registration_details,
            "section_id": section_id,
            "section_name": section.section_name
        }, reset_approval=True)
        await db.commit()
        
        selected_section = SectionOption(
            sectionId=str(section.section_id),
            sectionName=section.section_name,
            sectionCode=section.section_code,
            studentCapacity=section.student_capacity,
            currentStrength=section.current_strength,
            availableSlots=section.student_capacity - section.current_strength,
            classTeacher=None
        )
        
        logger.info(f"Student {student.student_id} selected section {section.section_name}, moving to user details")
        
        return SelectSectionResponse(
            selectedSection=selected_section,
            studentProfile=student.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Select section error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete registration"
        )


@router.put("/user-details", response_model=UserDetailsResponse)
async def submit_user_details(
    request: UserDetailsRequest,
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Submit user details and complete registration"""
    try:
        student = current_session["student"]
        
        # Check if section is selected (prerequisite for user details)
        section_id = student.registration_details.get("section_id")
        college_id = student.registration_details.get("college_id")
        
        if not section_id or not college_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete section selection first"
            )
        
        # Check if roll number is already taken in this college
        existing_student = await db.execute(
            select(Student).where(
                Student.college_id == college_id,
                Student.roll_number == request.rollNumber,
                Student.student_id != student.student_id  # Exclude current student
            )
        )
        if existing_student.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Roll number '{request.rollNumber}' is already taken in this college"
            )
        
        # Update student personal details
        student.full_name = request.fullName
        student.gender = request.gender
        student.email = request.email
        
        # Get section to update strength
        result = await db.execute(select(Section).where(Section.section_id == section_id))
        section = result.scalar_one_or_none()
        
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected section not found"
            )
        
        # Check section capacity one more time
        if section.current_strength >= section.student_capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected section is now full. Please select a different section."
            )
        
        # Generate admission number
        current_year = datetime.datetime.now().year
        admission_number = f"STU{current_year}{section.current_strength + 1:04d}"
        
        # Complete registration
        student.complete_registration(
            college_id=uuid.UUID(college_id),
            section_id=uuid.UUID(section_id),
            admission_number=admission_number,
            roll_number=request.rollNumber
        )
        
        # Update section strength
        section.current_strength += 1
        
        await db.commit()
        
        logger.info(f"Student {student.student_id} completed registration with user details")
        
        return UserDetailsResponse(
            studentProfile=student.to_dict(),
            admissionNumber=admission_number
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Submit user details error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete registration"
        )


@router.get("/status", response_model=RegistrationStatusResponse)
async def get_registration_status(
    current_session: dict = Depends(check_registration_in_progress),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed registration status and progress"""
    try:
        student = current_session["student"]
        progress = student.get_registration_progress()
        
        # Build step details based on current progress
        step_details = RegistrationStepDetails()
        details = progress.get("details", {})
        
        # Populate step details based on registration progress
        if details.get("college_id"):
            result = await db.execute(select(College).where(College.college_id == details["college_id"]))
            college = result.scalar_one_or_none()
            if college:
                step_details.college = CollegeOption(
                    collegeId=str(college.college_id),
                    name=college.name,
                    shortName=college.short_name or college.name,
                    city=college.city or "Unknown",
                    state=college.state or "Unknown",
                    logoUrl=college.logo_url
                )
        
        # Add roll number to step details
        if details.get("roll_number"):
            step_details.rollNumber = details["roll_number"]
        
        if details.get("term_id"):
            result = await db.execute(select(Term).where(Term.term_id == details["term_id"]))
            term = result.scalar_one_or_none()
            if term:
                step_details.term = TermOption(
                    termId=str(term.term_id),
                    name=term.name,
                    startDate=term.start_date,
                    endDate=term.end_date,
                    isActive=term.is_active
                )
        
        if details.get("graduation_id"):
            result = await db.execute(select(Graduation).where(Graduation.graduation_id == details["graduation_id"]))
            graduation = result.scalar_one_or_none()
            if graduation:
                step_details.graduation = GraduationOption(
                    graduationId=str(graduation.graduation_id),
                    name=graduation.name,
                    code=graduation.code
                )
        
        if details.get("degree_id"):
            result = await db.execute(select(Degree).where(Degree.degree_id == details["degree_id"]))
            degree = result.scalar_one_or_none()
            if degree:
                step_details.degree = DegreeOption(
                    degreeId=str(degree.degree_id),
                    name=degree.name,
                    code=degree.code,
                    durationYears=degree.duration_years
                )
        
        if details.get("branch_id"):
            result = await db.execute(select(Branch).where(Branch.branch_id == details["branch_id"]))
            branch = result.scalar_one_or_none()
            if branch:
                step_details.branch = BranchOption(
                    branchId=str(branch.branch_id),
                    name=branch.name,
                    code=branch.code
                )
        
        # Use simplified section schema for status display (no capacity/teacher info)
        if student.section_id:
            result = await db.execute(select(Section).where(Section.section_id == student.section_id))
            section = result.scalar_one_or_none()
            if section:
                step_details.section = SectionStatusOption(
                    sectionId=str(section.section_id),
                    sectionName=section.section_name,
                    sectionCode=section.section_code
                )
        
        # Determine next action based on current step and approval status
        if student.registration_completed:
            if student.approval_status == "pending":
                next_action = "Registration completed! Waiting for college approval to access the app"
            elif student.approval_status == "approved":
                next_action = "Registration approved! You can now access the app"
            elif student.approval_status == "rejected":
                rejection_reason = student.rejection_reason or "No reason provided"
                next_action = f"Registration rejected: {rejection_reason}. Contact college administration"
            else:
                next_action = "Registration completed! You can now access the app"
        else:
            next_actions = {
                "college_selection": "Select your college",
                "term_selection": "Choose the current academic term",
                "graduation_selection": "Select your graduation level (UG/PG/PhD)",
                "degree_selection": "Choose your degree program",
                "branch_selection": "Select your academic specialization",
                "section_selection": "Choose your class section",
                "user_details": "Enter your personal details to complete registration",
            }
            next_action = next_actions.get(progress["current_step"], "Continue registration")
        
        return RegistrationStatusResponse(
            currentStep=progress["current_step"],
            progressPercentage=progress["progress_percentage"],
            registrationCompleted=student.registration_completed,
            approvalStatus=student.approval_status,
            canAccessApp=student.can_access_app(),
            stepDetails=step_details,
            nextAction=next_action,
            updatedAt=datetime.datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Get registration status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get registration status"
        )