from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.models import CollegePlacement
from app.schemas.college_placements import CollegePlacementCreate, CollegePlacementUpdate, CollegePlacementResponse

router = APIRouter()


@router.post("/collegeplacements/", response_model=CollegePlacementResponse)
async def add_college_placement(
    placement_data: CollegePlacementCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
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
    placement = db.query(CollegePlacement).filter(CollegePlacement.id == id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="College placement not found")
    
    db.delete(placement)
    db.commit()
    return {}