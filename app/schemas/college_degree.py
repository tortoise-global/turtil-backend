from pydantic import BaseModel
from typing import Optional, List


class DegreeCreate(BaseModel):
    collegeId: str
    collegeShortName: str
    degrees: Optional[List] = []


class DegreeUpdate(BaseModel):
    collegeId: Optional[str] = None
    collegeShortName: Optional[str] = None
    degrees: Optional[List] = []


class DegreeResponse(BaseModel):
    id: int
    collegeId: str
    collegeShortName: str
    degrees: List

    class Config:
        from_attributes = True