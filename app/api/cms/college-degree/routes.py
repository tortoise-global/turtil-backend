from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.cms.models import CollegeDegree
from app.schemas.cms.college_degree import DegreeCreate, DegreeUpdate, DegreeResponse

router = APIRouter()


@router.post("/collegedegree/", response_model=DegreeResponse)
async def add_college_degree(
    degree_data: DegreeCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_degree = CollegeDegree(**degree_data.model_dump())
    db.add(db_degree)
    db.commit()
    db.refresh(db_degree)
    return db_degree


@router.put("/collegedegree/{college_id}", response_model=DegreeResponse)
async def update_college_degree(
    college_id: str,
    degree_data: DegreeUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    degree = db.query(CollegeDegree).filter(CollegeDegree.college_id == college_id).first()
    if not degree:
        raise HTTPException(status_code=404, detail="College degree not found")
    
    for field, value in degree_data.model_dump(exclude_unset=True).items():
        setattr(degree, field, value)
    
    db.commit()
    db.refresh(degree)
    return degree


@router.delete("/collegedegree/{college_id}")
async def delete_college_degree(
    college_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    degree = db.query(CollegeDegree).filter(CollegeDegree.college_id == college_id).first()
    if not degree:
        raise HTTPException(status_code=404, detail="College degree not found")
    
    db.delete(degree)
    db.commit()
    return {}


@router.get("/collegedegree/id/{college_id}", response_model=DegreeResponse)
async def get_college_degree_by_id(
    college_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    degree = db.query(CollegeDegree).filter(CollegeDegree.college_id == college_id).first()
    if not degree:
        raise HTTPException(status_code=404, detail="College degree not found")
    return degree


@router.get("/collegedegree/shortname/{short_name}", response_model=DegreeResponse)
async def get_college_degree_by_short_name(
    short_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    degree = db.query(CollegeDegree).filter(CollegeDegree.college_short_name == short_name).first()
    if not degree:
        raise HTTPException(status_code=404, detail="College degree not found")
    return degree