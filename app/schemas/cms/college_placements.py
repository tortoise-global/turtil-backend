from pydantic import BaseModel
from typing import Optional


class CollegePlacementCreate(BaseModel):
    collegeId: str
    collegeShortName: str
    collegeName: str
    placementDate: int
    degree: str
    company: str
    batch: str
    branch: str


class CollegePlacementUpdate(BaseModel):
    collegeId: Optional[str] = None
    collegeShortName: Optional[str] = None
    collegeName: Optional[str] = None
    placementDate: Optional[int] = None
    degree: Optional[str] = None
    company: Optional[str] = None
    batch: Optional[str] = None
    branch: Optional[str] = None


class CollegePlacementResponse(BaseModel):
    id: int
    collegeId: str
    collegeShortName: str
    collegeName: str
    placementDate: int
    degree: str
    company: str
    batch: str
    branch: str
    createdAt: int
    updatedAt: Optional[int] = None

    class Config:
        from_attributes = True