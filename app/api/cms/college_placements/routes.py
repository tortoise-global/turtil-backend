from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.cms.models import CMSPlacementDrive, CMSCompany
from app.schemas.cms.college_placements import CollegePlacementCreate, CollegePlacementUpdate, CollegePlacementResponse

router = APIRouter()


@router.post("/collegeplacements/", response_model=CollegePlacementResponse)
async def add_college_placement(
    placement_data: CollegePlacementCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a new college placement record
    
    **Request Body:**
    - college_id (string, required): Unique identifier for the college
    - college_short_name (string, required): Short name/abbreviation of college
    - college_name (string, required): Full name of the college
    - placement_date (integer, required): Placement date as Unix timestamp
    - degree (string, required): Degree program (e.g., "B.Tech", "M.Tech")
    - company (string, required): Name of the hiring company
    - batch (string, required): Academic batch year
    - branch (string, required): Academic branch/specialization
    
    **Parameters:** None
    
    **Headers:**
    - Content-Type: application/json
    - Authorization: Bearer {access_token}
    
    **Example Request:**
    ```json
    {
        "college_id": "clg_rajivgandhi_001",
        "college_short_name": "RGIT",
        "college_name": "Rajiv Gandhi Institute of Technology",
        "placement_date": 1704067200,
        "degree": "B.Tech",
        "company": "TCS",
        "batch": "2024",
        "branch": "Computer Science Engineering"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "id": 1,
        "college_id": "clg_rajivgandhi_001",
        "college_short_name": "RGIT",
        "college_name": "Rajiv Gandhi Institute of Technology",
        "placement_date": 1704067200,
        "degree": "B.Tech",
        "company": "TCS",
        "batch": "2024",
        "branch": "Computer Science Engineering",
        "created_at": 1704153600,
        "updated_at": null
    }
    ```
    
    **Status Codes:**
    - 200: Placement record created successfully
    - 401: Unauthorized (invalid token)
    - 422: Validation error
    """
    db_placement = CollegePlacement(**placement_data.model_dump())
    db.add(db_placement)
    db.commit()
    db.refresh(db_placement)
    return db_placement


@router.get("/collegeplacements/{id}", response_model=CollegePlacementResponse)
async def get_college_placement(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific college placement by ID
    
    **Request Body:** None
    
    **Path Parameters:**
    - id (integer, required): Unique ID of the placement record
    
    **Query Parameters:** None
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Example URL:** GET /collegeplacements/1
    
    **Example Response:**
    ```json
    {
        "id": 1,
        "college_id": "clg_rajivgandhi_001",
        "college_short_name": "RGIT",
        "college_name": "Rajiv Gandhi Institute of Technology",
        "placement_date": 1704067200,
        "degree": "B.Tech",
        "company": "TCS",
        "batch": "2024",
        "branch": "Computer Science Engineering",
        "created_at": 1704153600,
        "updated_at": null
    }
    ```
    
    **Status Codes:**
    - 200: Placement record retrieved successfully
    - 401: Unauthorized (invalid token)
    - 404: College placement not found
    """
    placement = db.query(CollegePlacement).filter(CollegePlacement.id == id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="College placement not found")
    return placement


@router.put("/collegeplacements/{id}", response_model=CollegePlacementResponse)
async def update_college_placement(
    id: int,
    placement_data: CollegePlacementUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a college placement record
    
    **Request Body (partial update allowed):**
    - college_id (string, optional): Unique identifier for the college
    - college_short_name (string, optional): Short name/abbreviation of college
    - college_name (string, optional): Full name of the college
    - placement_date (integer, optional): Placement date as Unix timestamp
    - degree (string, optional): Degree program
    - company (string, optional): Name of the hiring company
    - batch (string, optional): Academic batch year
    - branch (string, optional): Academic branch/specialization
    
    **Path Parameters:**
    - id (integer, required): Unique ID of the placement record to update
    
    **Query Parameters:** None
    
    **Headers:**
    - Content-Type: application/json
    - Authorization: Bearer {access_token}
    
    **Example URL:** PUT /collegeplacements/1
    
    **Example Request (partial update):**
    ```json
    {
        "company": "Infosys",
        "placement_date": 1704153600
    }
    ```
    
    **Example Response:**
    ```json
    {
        "id": 1,
        "college_id": "clg_rajivgandhi_001",
        "college_short_name": "RGIT",
        "college_name": "Rajiv Gandhi Institute of Technology",
        "placement_date": 1704153600,
        "degree": "B.Tech",
        "company": "Infosys",
        "batch": "2024",
        "branch": "Computer Science Engineering",
        "created_at": 1704153600,
        "updated_at": 1704240000
    }
    ```
    
    **Status Codes:**
    - 200: Placement record updated successfully
    - 401: Unauthorized (invalid token)
    - 404: College placement not found
    - 422: Validation error
    """
    placement = db.query(CollegePlacement).filter(CollegePlacement.id == id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="College placement not found")
    
    for field, value in placement_data.model_dump(exclude_unset=True).items():
        setattr(placement, field, value)
    
    db.commit()
    db.refresh(placement)
    return placement


@router.delete("/collegeplacements/{id}")
async def delete_college_placement(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a college placement record
    
    **Request Body:** None
    
    **Path Parameters:**
    - id (integer, required): Unique ID of the placement record to delete
    
    **Query Parameters:** None
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Example URL:** DELETE /collegeplacements/1
    
    **Example Response:**
    ```json
    {}
    ```
    
    **Status Codes:**
    - 200: Placement record deleted successfully
    - 401: Unauthorized (invalid token)
    - 404: College placement not found
    """
    placement = db.query(CollegePlacement).filter(CollegePlacement.id == id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="College placement not found")
    
    db.delete(placement)
    db.commit()
    return {}