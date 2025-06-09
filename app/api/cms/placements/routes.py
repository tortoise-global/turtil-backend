from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from app.db.database import get_db
from app.core.auth import get_current_active_user, get_admin_user
from app.models.cms.models import User, Institute
from app.models.cms.placements import Company, PlacementDrive, PlacementApplication
from app.schemas.cms.placements import (
    Company as CompanySchema,
    CompanyCreate,
    CompanyUpdate,
    PlacementDrive as PlacementDriveSchema,
    PlacementDriveCreate,
    PlacementDriveUpdate,
    PlacementDriveWithDetails,
    PlacementApplication as PlacementApplicationSchema,
    PlacementApplicationCreate,
    PlacementApplicationUpdate,
    PlacementStats
)

router = APIRouter()


# Company Routes
@router.get("/companies", response_model=List[CompanySchema])
def get_companies(
    skip: int = 0,
    limit: int = 100,
    industry: Optional[str] = Query(None),
    is_verified: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Company)
    
    if industry:
        query = query.filter(Company.industry == industry)
    if is_verified is not None:
        query = query.filter(Company.is_verified == is_verified)
    
    companies = query.offset(skip).limit(limit).all()
    return companies


@router.get("/companies/{company_id}", response_model=CompanySchema)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("/companies", response_model=CompanySchema)
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_company = Company(**company.dict())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


@router.put("/companies/{company_id}", response_model=CompanySchema)
def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    update_data = company_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_company, field, value)
    
    db.commit()
    db.refresh(db_company)
    return db_company


# Placement Drive Routes
@router.get("/drives", response_model=List[PlacementDriveSchema])
def get_placement_drives(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    job_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(PlacementDrive)
    
    if status:
        query = query.filter(PlacementDrive.status == status)
    if company_id:
        query = query.filter(PlacementDrive.company_id == company_id)
    if job_type:
        query = query.filter(PlacementDrive.job_type == job_type)
    
    drives = query.offset(skip).limit(limit).all()
    return drives


@router.get("/drives/{drive_id}", response_model=PlacementDriveWithDetails)
def get_placement_drive(
    drive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    drive = db.query(PlacementDrive).filter(PlacementDrive.id == drive_id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Placement drive not found")
    return drive


@router.post("/drives", response_model=PlacementDriveSchema)
def create_placement_drive(
    drive: PlacementDriveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    # Validate company exists
    company = db.query(Company).filter(Company.id == drive.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Validate institute exists
    institute = db.query(Institute).filter(Institute.id == drive.institute_id).first()
    if not institute:
        raise HTTPException(status_code=404, detail="Institute not found")
    
    db_drive = PlacementDrive(**drive.dict())
    db.add(db_drive)
    db.commit()
    db.refresh(db_drive)
    return db_drive


@router.put("/drives/{drive_id}", response_model=PlacementDriveSchema)
def update_placement_drive(
    drive_id: int,
    drive_update: PlacementDriveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_drive = db.query(PlacementDrive).filter(PlacementDrive.id == drive_id).first()
    if not db_drive:
        raise HTTPException(status_code=404, detail="Placement drive not found")
    
    update_data = drive_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_drive, field, value)
    
    db.commit()
    db.refresh(db_drive)
    return db_drive


# Application Routes
@router.get("/drives/{drive_id}/applications", response_model=List[PlacementApplicationSchema])
def get_drive_applications(
    drive_id: int,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    # Check if drive exists
    drive = db.query(PlacementDrive).filter(PlacementDrive.id == drive_id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Placement drive not found")
    
    query = db.query(PlacementApplication).filter(PlacementApplication.placement_drive_id == drive_id)
    
    if status:
        query = query.filter(PlacementApplication.status == status)
    
    applications = query.all()
    return applications


@router.post("/drives/{drive_id}/apply", response_model=PlacementApplicationSchema)
def apply_to_placement_drive(
    drive_id: int,
    application: PlacementApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Check if drive exists and is active
    drive = db.query(PlacementDrive).filter(PlacementDrive.id == drive_id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Placement drive not found")
    
    if not drive.is_active or drive.status != "upcoming":
        raise HTTPException(status_code=400, detail="Placement drive is not accepting applications")
    
    # Check if registration is open
    now = datetime.now()
    if now < drive.registration_start or now > drive.registration_end:
        raise HTTPException(status_code=400, detail="Registration period is closed")
    
    # Check if already applied
    existing_application = db.query(PlacementApplication).filter(
        PlacementApplication.placement_drive_id == drive_id,
        PlacementApplication.student_email == application.student_email
    ).first()
    
    if existing_application:
        raise HTTPException(status_code=400, detail="Already applied to this drive")
    
    # Set the drive ID
    application.placement_drive_id = drive_id
    
    db_application = PlacementApplication(**application.dict())
    db.add(db_application)
    
    # Update drive statistics
    drive.total_registered += 1
    
    db.commit()
    db.refresh(db_application)
    return db_application


@router.put("/applications/{application_id}", response_model=PlacementApplicationSchema)
def update_application(
    application_id: int,
    application_update: PlacementApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_application = db.query(PlacementApplication).filter(PlacementApplication.id == application_id).first()
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    update_data = application_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_application, field, value)
    
    # Update placement statistics if final result is set
    if "final_result" in update_data and update_data["final_result"] == "selected":
        drive = db.query(PlacementDrive).filter(PlacementDrive.id == db_application.placement_drive_id).first()
        if drive:
            drive.total_selected += 1
    
    db.commit()
    db.refresh(db_application)
    return db_application


@router.get("/stats", response_model=PlacementStats)
def get_placement_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    total_companies = db.query(Company).filter(Company.is_active == True).count()
    active_drives = db.query(PlacementDrive).filter(PlacementDrive.status == "upcoming").count()
    total_applications = db.query(PlacementApplication).count()
    total_placements = db.query(PlacementApplication).filter(PlacementApplication.final_result == "selected").count()
    
    placement_percentage = (total_placements / total_applications * 100) if total_applications > 0 else 0
    
    return PlacementStats(
        total_companies=total_companies,
        active_drives=active_drives,
        total_applications=total_applications,
        total_placements=total_placements,
        placement_percentage=round(placement_percentage, 2)
    )