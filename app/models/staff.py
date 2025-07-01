from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid
from datetime import datetime, timezone


class Staff(UUIDBaseModel):
    """Staff model with UUID primary key for authentication and staff management"""

    __tablename__ = "staff"

    # UUID Primary Key - descriptive and intuitive
    staff_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Basic staff information
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=True)  # Collected during profile setup
    contact_number = Column(String(20), nullable=True)  # Staff contact number (collected during profile setup)

    # Authentication
    hashed_password = Column(String(255), nullable=True)  # Set during profile setup
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superstaff = Column(Boolean, default=False, nullable=False)

    # Email verification
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Last login tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)

    # CMS-specific fields with UUID foreign keys
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.college_id"), nullable=True)
    division_id = Column(UUID(as_uuid=True), ForeignKey("divisions.division_id"), nullable=True)  # Division assignment
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.department_id"), nullable=True)
    cms_role = Column(String(50), default="staff", nullable=False)  # 'principal', 'admin', 'hod', 'staff'

    # Invitation & Onboarding System
    invitation_status = Column(String(50), default="pending", nullable=False)  # 'pending', 'accepted', 'active'
    temporary_password = Column(Boolean, default=False, nullable=False)
    must_reset_password = Column(Boolean, default=False, nullable=False)
    can_assign_department = Column(Boolean, default=False, nullable=False)
    invited_by_staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.staff_id"), nullable=True)
    is_hod = Column(Boolean, default=False, nullable=False)  # Head of Department status

    # Relationships
    college = relationship("College", back_populates="staff_members", foreign_keys=[college_id])
    division = relationship("Division", back_populates="staff_members", foreign_keys=[division_id])
    department = relationship("Department", back_populates="staff_members", foreign_keys=[department_id])
    invited_by = relationship("Staff", remote_side=[staff_id])
    sessions = relationship("UserSession", back_populates="staff")

    def __repr__(self):
        return f"<Staff(staff_id={self.staff_id}, email={self.email})>"

    def verify_email(self):
        """Mark email as verified"""
        self.is_verified = True
        self.email_verified_at = datetime.now(timezone.utc)

    def record_login(self):
        """Record a successful login"""
        self.last_login_at = datetime.now(timezone.utc)
        self.login_count += 1

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert to dictionary with camelCase for API responses.
        Excludes sensitive information by default.
        """
        base_dict = super().to_dict()
        result = {
            "staffId": base_dict["staff_id"],
            "email": base_dict["email"],
            "fullName": base_dict["full_name"],
            "contactNumber": base_dict["contact_number"],
            "isActive": base_dict["is_active"],
            "isVerified": base_dict["is_verified"],
            "isSuperstaff": base_dict["is_superstaff"],
            "emailVerifiedAt": base_dict["email_verified_at"],
            "lastLoginAt": base_dict["last_login_at"],
            "loginCount": base_dict["login_count"],
            # CMS-specific fields
            "collegeId": base_dict["college_id"],
            "divisionId": base_dict["division_id"],
            "departmentId": base_dict["department_id"],
            "cmsRole": base_dict["cms_role"],
            "invitationStatus": base_dict["invitation_status"],
            "temporaryPassword": base_dict["temporary_password"],
            "mustResetPassword": base_dict["must_reset_password"],
            "canAssignDepartment": base_dict["can_assign_department"],
            "invitedByStaffId": base_dict["invited_by_staff_id"],
            "isHod": base_dict["is_hod"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }

        if include_sensitive:
            result["hashedPassword"] = base_dict["hashed_password"]

        return result

    def to_token_payload(self) -> dict:
        """Create payload for JWT token"""
        # Determine flow control flags
        requires_password_reset = (
            self.must_reset_password or 
            self.temporary_password or
            (self.invitation_status == "pending" and self.hashed_password)
        )
        
        requires_details = (
            not self.college_id or 
            (self.cms_role == "principal" and self.invitation_status == "pending")
        )
        
        return {
            "sub": str(self.staff_id),  # Subject (staff identifier)
            "staffId": str(self.staff_id),  # Explicit staff ID for clarity
            "email": self.email,
            "fullName": self.full_name,
            "isVerified": self.is_verified,
            "isSuperstaff": self.is_superstaff,
            # CMS-specific token data
            "cmsRole": self.cms_role,
            "collegeId": str(self.college_id) if self.college_id else None,
            "divisionId": str(self.division_id) if self.division_id else None,
            "departmentId": str(self.department_id) if self.department_id else None,
            "invitationStatus": self.invitation_status,
            "requiresPasswordReset": requires_password_reset,
            "requiresDetails": requires_details,
        }