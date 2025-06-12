from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.student.models import StudentUser
from app.schemas.cms.college_students import CollegeStudentCreate, CollegeStudentUpdate, CollegeStudentResponse, PaginatedResponse

router = APIRouter()


@router.post("/college-students", response_model=CollegeStudentResponse)
async def create_student(
    student_data: CollegeStudentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new college student record
    
    **Request Body:**
    - id (string, required): Unique identifier for the student record
    - college_id (string, required): Unique identifier for the college
    - college_short_name (string, required): Short name/abbreviation of college
    - college_name (string, required): Full name of the college
    - student_id (string, required): Student's enrollment/roll number
    - student_name (string, required): Full name of the student
    - email (string, required): Student's email address
    - phone (string, required): Student's phone number with country code
    - degree (string, required): Degree program (e.g., "B.Tech", "M.Tech")
    - batch (string, required): Academic batch year
    - branch (string, required): Academic branch/specialization
    - section (string, required): Section within the branch
    - gender (string, required): Student's gender
    
    **Parameters:** None
    
    **Headers:**
    - Content-Type: application/json
    - Authorization: Bearer {access_token}
    
    **Example Request:**
    ```json
    {
        "id": "std_rajesh_2024_cse_001",
        "college_id": "clg_rajivgandhi_001",
        "college_short_name": "RGIT",
        "college_name": "Rajiv Gandhi Institute of Technology",
        "student_id": "24CSE001",
        "student_name": "Rajesh Kumar",
        "email": "rajesh.kumar@student.rgit.edu",
        "phone": "+91-9876543210",
        "degree": "B.Tech",
        "batch": "2024",
        "branch": "Computer Science Engineering",
        "section": "A",
        "gender": "Male"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "id": "std_rajesh_2024_cse_001",
        "college_id": "clg_rajivgandhi_001",
        "college_short_name": "RGIT",
        "college_name": "Rajiv Gandhi Institute of Technology",
        "student_id": "24CSE001",
        "student_name": "Rajesh Kumar",
        "email": "rajesh.kumar@student.rgit.edu",
        "phone": "+91-9876543210",
        "degree": "B.Tech",
        "batch": "2024",
        "branch": "Computer Science Engineering",
        "section": "A",
        "gender": "Male",
        "created_at": 1704153600,
        "updated_at": null
    }
    ```
    
    **Status Codes:**
    - 200: Student record created successfully
    - 401: Unauthorized (invalid token)
    - 422: Validation error (duplicate ID, invalid data)
    """
    db_student = CollegeStudent(**student_data.model_dump())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@router.get("/college-students", response_model=PaginatedResponse)
async def get_students(
    college_id: Optional[str] = Query(None),
    college_short_name: Optional[str] = Query(None),
    student_id: Optional[str] = Query(None),
    student_name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    degree: Optional[str] = Query(None),
    batch: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated list of college students with filtering
    
    **Request Body:** None
    
    **Path Parameters:** None
    
    **Query Parameters (all optional):**
    - college_id (string): Filter by college ID
    - college_short_name (string): Filter by college short name
    - student_id (string): Filter by student ID
    - student_name (string): Filter by student name (partial match)
    - email (string): Filter by exact email address
    - phone (string): Filter by exact phone number
    - degree (string): Filter by degree program
    - batch (string): Filter by academic batch
    - branch (string): Filter by academic branch
    - section (string): Filter by section
    - gender (string): Filter by gender
    - page (integer): Page number (default: 1, minimum: 1)
    - page_size (integer): Items per page (default: 10, min: 1, max: 100)
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Example URLs:**
    - GET /college-students?page=1&page_size=10
    - GET /college-students?college_id=clg_rajivgandhi_001&batch=2024
    - GET /college-students?branch=Computer%20Science%20Engineering&section=A
    - GET /college-students?student_name=rajesh&gender=Male
    
    **Example Response:**
    ```json
    {
        "total": 150,
        "page": 1,
        "per_page": 10,
        "items": [
            {
                "id": "std_rajesh_2024_cse_001",
                "college_id": "clg_rajivgandhi_001",
                "college_short_name": "RGIT",
                "college_name": "Rajiv Gandhi Institute of Technology",
                "student_id": "24CSE001",
                "student_name": "Rajesh Kumar",
                "email": "rajesh.kumar@student.rgit.edu",
                "phone": "+91-9876543210",
                "degree": "B.Tech",
                "batch": "2024",
                "branch": "Computer Science Engineering",
                "section": "A",
                "gender": "Male",
                "created_at": 1704153600,
                "updated_at": null
            }
        ]
    }
    ```
    
    **Status Codes:**
    - 200: Students retrieved successfully
    - 401: Unauthorized (invalid token)
    - 422: Validation error (invalid query parameters)
    """
    query = db.query(CollegeStudent)
    
    if college_id:
        query = query.filter(CollegeStudent.college_id == college_id)
    if college_short_name:
        query = query.filter(CollegeStudent.college_short_name == college_short_name)
    if student_id:
        query = query.filter(CollegeStudent.student_id == student_id)
    if student_name:
        query = query.filter(CollegeStudent.student_name.ilike(f"%{student_name}%"))
    if email:
        query = query.filter(CollegeStudent.email == email)
    if phone:
        query = query.filter(CollegeStudent.phone == phone)
    if degree:
        query = query.filter(CollegeStudent.degree == degree)
    if batch:
        query = query.filter(CollegeStudent.batch == batch)
    if branch:
        query = query.filter(CollegeStudent.branch == branch)
    if section:
        query = query.filter(CollegeStudent.section == section)
    if gender:
        query = query.filter(CollegeStudent.gender == gender)
    
    total = query.count()
    offset = (page - 1) * page_size
    students = query.offset(offset).limit(page_size).all()
    
    return PaginatedResponse(
        total=total,
        page=page,
        per_page=page_size,
        items=students
    )


@router.get("/college-students/{student_id}", response_model=CollegeStudentResponse)
async def get_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific student by ID
    
    **Request Body:** None
    
    **Path Parameters:**
    - student_id (string, required): Unique ID of the student record
    
    **Query Parameters:** None
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Example URL:** GET /college-students/std_rajesh_2024_cse_001
    
    **Example Response:**
    ```json
    {
        "id": "std_rajesh_2024_cse_001",
        "college_id": "clg_rajivgandhi_001",
        "college_short_name": "RGIT",
        "college_name": "Rajiv Gandhi Institute of Technology",
        "student_id": "24CSE001",
        "student_name": "Rajesh Kumar",
        "email": "rajesh.kumar@student.rgit.edu",
        "phone": "+91-9876543210",
        "degree": "B.Tech",
        "batch": "2024",
        "branch": "Computer Science Engineering",
        "section": "A",
        "gender": "Male",
        "created_at": 1704153600,
        "updated_at": null
    }
    ```
    
    **Status Codes:**
    - 200: Student retrieved successfully
    - 401: Unauthorized (invalid token)
    - 404: Student not found
    """
    student = db.query(CollegeStudent).filter(CollegeStudent.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/college-students/{student_id}", response_model=CollegeStudentResponse)
async def update_student(
    student_id: str,
    student_data: CollegeStudentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a student record
    
    **Request Body (partial update allowed):**
    - college_id (string, optional): Unique identifier for the college
    - college_short_name (string, optional): Short name/abbreviation of college
    - college_name (string, optional): Full name of the college
    - student_id (string, optional): Student's enrollment/roll number
    - student_name (string, optional): Full name of the student
    - email (string, optional): Student's email address
    - phone (string, optional): Student's phone number with country code
    - degree (string, optional): Degree program
    - batch (string, optional): Academic batch year
    - branch (string, optional): Academic branch/specialization
    - section (string, optional): Section within the branch
    - gender (string, optional): Student's gender
    
    **Path Parameters:**
    - student_id (string, required): Unique ID of the student record to update
    
    **Query Parameters:** None
    
    **Headers:**
    - Content-Type: application/json
    - Authorization: Bearer {access_token}
    
    **Example URL:** PUT /college-students/std_rajesh_2024_cse_001
    
    **Example Request (partial update):**
    ```json
    {
        "phone": "+91-9876543211",
        "email": "rajesh.new@student.rgit.edu",
        "section": "B"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "id": "std_rajesh_2024_cse_001",
        "college_id": "clg_rajivgandhi_001",
        "college_short_name": "RGIT",
        "college_name": "Rajiv Gandhi Institute of Technology",
        "student_id": "24CSE001",
        "student_name": "Rajesh Kumar",
        "email": "rajesh.new@student.rgit.edu",
        "phone": "+91-9876543211",
        "degree": "B.Tech",
        "batch": "2024",
        "branch": "Computer Science Engineering",
        "section": "B",
        "gender": "Male",
        "created_at": 1704153600,
        "updated_at": 1704240000
    }
    ```
    
    **Status Codes:**
    - 200: Student updated successfully
    - 401: Unauthorized (invalid token)
    - 404: Student not found
    - 422: Validation error
    """
    student = db.query(CollegeStudent).filter(CollegeStudent.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    for field, value in student_data.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    
    db.commit()
    db.refresh(student)
    return student


@router.delete("/college-students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    student = db.query(CollegeStudent).filter(CollegeStudent.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    db.delete(student)
    db.commit()


@router.get("/search-students", response_model=List[CollegeStudentResponse])
async def search_students(
    query: Optional[str] = Query(None),
    college_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Search students by name or student ID
    
    **Request Body:** None
    
    **Path Parameters:** None
    
    **Query Parameters:**
    - query (string, optional): Search term for student name or student ID (partial match)
    - college_id (string, optional): Filter results by college ID
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Example URLs:**
    - GET /search-students?query=rajesh
    - GET /search-students?query=24CSE001&college_id=clg_rajivgandhi_001
    - GET /search-students?college_id=clg_rajivgandhi_001
    
    **Example Response:**
    ```json
    [
        {
            "id": "std_rajesh_2024_cse_001",
            "college_id": "clg_rajivgandhi_001",
            "college_short_name": "RGIT",
            "college_name": "Rajiv Gandhi Institute of Technology",
            "student_id": "24CSE001",
            "student_name": "Rajesh Kumar",
            "email": "rajesh.kumar@student.rgit.edu",
            "phone": "+91-9876543210",
            "degree": "B.Tech",
            "batch": "2024",
            "branch": "Computer Science Engineering",
            "section": "A",
            "gender": "Male",
            "created_at": 1704153600,
            "updated_at": null
        }
    ]
    ```
    
    **Status Codes:**
    - 200: Search completed successfully
    - 401: Unauthorized (invalid token)
    - 422: Validation error
    
    **Search Logic:**
    - If query is provided: searches in student_id and student_name fields
    - If college_id is provided: filters results by college
    - If both provided: applies both filters
    - If neither provided: returns all students for the college
    """
    db_query = db.query(CollegeStudent)
    
    if college_id:
        db_query = db_query.filter(CollegeStudent.college_id == college_id)
    
    if query:
        db_query = db_query.filter(
            (CollegeStudent.student_id.ilike(f"%{query}%")) |
            (CollegeStudent.student_name.ilike(f"%{query}%"))
        )
    
    students = db_query.all()
    return students