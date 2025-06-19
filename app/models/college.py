from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid
from datetime import datetime, timezone


class College(BaseModel):
    """College model for CMS system"""
    __tablename__ = "colleges"
    
    # Use UUID for better security (separate from primary key)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # College Details
    name = Column(String(255), nullable=False)  # "Acme Engineering College"
    short_name = Column(String(50), nullable=False)  # "ACME"
    college_reference_id = Column(String(100), nullable=False)  # "ACME001" (user reference)
    logo_url = Column(String(500), nullable=True)  # S3 URL (optional)
    
    # Address Details
    area = Column(String(255), nullable=False)  # "Padmavathi Nagar, Soorpet"
    city = Column(String(100), nullable=False)  # "Hyderabad"
    district = Column(String(100), nullable=False)  # "Rangareddy"
    state = Column(String(100), nullable=False)  # "Telangana"
    pincode = Column(String(10), nullable=False)  # "530000"
    latitude = Column(DECIMAL(10, 8), nullable=True)  # Optional coordinates
    longitude = Column(DECIMAL(11, 8), nullable=True)  # Optional coordinates
    
    # Administrative
    principal_cms_user_id = Column(Integer, nullable=True)  # Will be FK after User model update
    
    # Settings
    auto_approved = Column(Boolean, default=True, nullable=False)  # Development mode
    
    # Relationships (will be defined after creating other models)
    # users = relationship("User", back_populates="college")
    # departments = relationship("Department", back_populates="college")
    
    def __repr__(self):
        return f"<College(id={self.id}, name={self.name})>"
    
    @property
    def full_address(self) -> str:
        """Get college's full address"""
        return f"{self.area}, {self.city}, {self.district}, {self.state} - {self.pincode}"
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert to dictionary with camelCase for API responses.
        """
        base_dict = super().to_dict()
        result = {
            "id": base_dict["id"],
            "uuid": str(self.uuid),
            "name": base_dict["name"],
            "shortName": base_dict["short_name"],
            "collegeReferenceId": base_dict["college_reference_id"],
            "logoUrl": base_dict["logo_url"],
            "area": base_dict["area"],
            "city": base_dict["city"],
            "district": base_dict["district"],
            "state": base_dict["state"],
            "pincode": base_dict["pincode"],
            "latitude": str(base_dict["latitude"]) if base_dict["latitude"] else None,
            "longitude": str(base_dict["longitude"]) if base_dict["longitude"] else None,
            "fullAddress": self.full_address,
            "principalCmsUserId": base_dict["principal_cms_user_id"],
            "autoApproved": base_dict["auto_approved"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"]
        }
        
        return result