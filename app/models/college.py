from sqlalchemy import Column, String, Boolean, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid


class College(UUIDBaseModel):
    """College model with UUID primary key for CMS system"""

    __tablename__ = "colleges"

    # UUID Primary Key - descriptive and intuitive
    college_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # College Details
    name = Column(String(255), nullable=False)  # "Acme Engineering College"
    short_name = Column(String(50), nullable=False)  # "ACME"
    college_reference_id = Column(String(100), nullable=False)  # "ACME001" (staff reference)
    logo_url = Column(String(500), nullable=True)  # S3 URL (optional)
    phone_number = Column(String(20), nullable=True)  # College contact number

    # Address Details
    area = Column(String(255), nullable=False)  # "Padmavathi Nagar, Soorpet"
    city = Column(String(100), nullable=False)  # "Hyderabad"
    district = Column(String(100), nullable=False)  # "Rangareddy"
    state = Column(String(100), nullable=False)  # "Telangana"
    pincode = Column(String(10), nullable=False)  # "530000"
    latitude = Column(DECIMAL(10, 8), nullable=True)  # Optional coordinates
    longitude = Column(DECIMAL(11, 8), nullable=True)  # Optional coordinates

    # Administrative - UUID foreign keys
    principal_staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.staff_id"), nullable=True)

    # Contact Information for CMS Support
    contact_number = Column(String(20), nullable=True)  # Contact number for CMS support
    contact_staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.staff_id"), nullable=True)  # Staff responsible for contact

    # Settings
    auto_approved = Column(Boolean, default=True, nullable=False)  # Development mode

    # Relationships
    staff_members = relationship("Staff", back_populates="college", foreign_keys="Staff.college_id")
    divisions = relationship("Division", back_populates="college", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="college")
    terms = relationship("Term", back_populates="college")
    principal = relationship("Staff", foreign_keys=[principal_staff_id], post_update=True)
    contact_staff = relationship("Staff", foreign_keys=[contact_staff_id], post_update=True)

    def __repr__(self):
        return f"<College(college_id={self.college_id}, name={self.name})>"

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
            "collegeId": base_dict["college_id"],
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
            "phoneNumber": base_dict["phone_number"],
            "principalStaffId": base_dict["principal_staff_id"],
            "contactNumber": base_dict["contact_number"],
            "contactStaffId": base_dict["contact_staff_id"],
            "autoApproved": base_dict["auto_approved"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }

        return result