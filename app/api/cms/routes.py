from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.core.auth import get_current_active_user, get_admin_user
from app.models.cms.models import Institute, User
from app.schemas.cms.schemas import (
    Institute as InstituteSchema, 
    InstituteCreate, 
    InstituteUpdate,
    User as UserSchema
)

# Import sub-routers
from app.api.cms.auth.routes import router as auth_router
from app.api.cms.programs.routes import router as programs_router
from app.api.cms.placements.routes import router as placements_router

router = APIRouter()

# Include sub-routers
router.include_router(auth_router, prefix="/auth", tags=["cms-auth"])
router.include_router(programs_router, prefix="/programs", tags=["cms-programs"])
router.include_router(placements_router, prefix="/placements", tags=["cms-placements"])


@router.get("/institutes", response_model=List[InstituteSchema])
def get_institutes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    institutes = db.query(Institute).offset(skip).limit(limit).all()
    return institutes


@router.get("/institutes/{institute_id}", response_model=InstituteSchema)
def get_institute(institute_id: int, db: Session = Depends(get_db)):
    institute = db.query(Institute).filter(Institute.id == institute_id).first()
    if institute is None:
        raise HTTPException(status_code=404, detail="Institute not found")
    return institute


@router.post("/institutes", response_model=InstituteSchema)
def create_institute(
    institute: InstituteCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_institute = db.query(Institute).filter(Institute.code == institute.code).first()
    if db_institute:
        raise HTTPException(status_code=400, detail="Institute code already exists")
    
    db_institute = Institute(**institute.dict())
    db.add(db_institute)
    db.commit()
    db.refresh(db_institute)
    return db_institute


@router.put("/institutes/{institute_id}", response_model=InstituteSchema)
def update_institute(institute_id: int, institute_update: InstituteUpdate, db: Session = Depends(get_db)):
    db_institute = db.query(Institute).filter(Institute.id == institute_id).first()
    if db_institute is None:
        raise HTTPException(status_code=404, detail="Institute not found")
    
    update_data = institute_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_institute, field, value)
    
    db.commit()
    db.refresh(db_institute)
    return db_institute


@router.delete("/institutes/{institute_id}")
def delete_institute(institute_id: int, db: Session = Depends(get_db)):
    db_institute = db.query(Institute).filter(Institute.id == institute_id).first()
    if db_institute is None:
        raise HTTPException(status_code=404, detail="Institute not found")
    
    db.delete(db_institute)
    db.commit()
    return {"message": "Institute deleted successfully"}


@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_institutes = db.query(Institute).count()
    active_institutes = db.query(Institute).filter(Institute.is_active == True).count()
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    return {
        "total_institutes": total_institutes,
        "active_institutes": active_institutes,
        "total_users": total_users,
        "active_users": active_users
    }