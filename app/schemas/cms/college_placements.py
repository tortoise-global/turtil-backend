from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import date
from app.schemas.cms.academic import CMSPlacementDriveCreate, CMSPlacementDriveUpdate, CMSPlacementDriveResponse

CollegePlacementCreate = CMSPlacementDriveCreate
CollegePlacementUpdate = CMSPlacementDriveUpdate
CollegePlacementResponse = CMSPlacementDriveResponse