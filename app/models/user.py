from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid
from datetime import datetime, timezone


class User(BaseModel):
    """User model for authentication and user management"""
    __tablename__ = "users"
    
    # Use UUID as primary key for better security
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Basic user information
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Email verification
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Last login tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    
    # CMS-specific fields
    phone_number = Column(String(20), nullable=True)
    marketing_consent = Column(Boolean, default=False, nullable=False)
    terms_accepted = Column(Boolean, default=False, nullable=False)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    cms_role = Column(String(50), default='staff', nullable=False)  # 'principal', 'college_admin', 'hod', 'staff'
    
    # Invitation & Onboarding System
    invitation_status = Column(String(50), default='pending', nullable=False)  # 'pending', 'accepted', 'active'
    temporary_password = Column(Boolean, default=False, nullable=False)
    must_reset_password = Column(Boolean, default=False, nullable=False)
    can_assign_department = Column(Boolean, default=False, nullable=False)
    invited_by_cms_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_hod = Column(Boolean, default=False, nullable=False)  # Head of Department status
    
    # Relationships
    # college = relationship("College", back_populates="users")
    # department = relationship("Department", back_populates="users")
    # invited_by = relationship("User", remote_side=[id])
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
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
            "cmsUserId": base_dict["id"],
            "uuid": str(self.uuid),
            "email": base_dict["email"],
            "firstName": base_dict["first_name"],
            "lastName": base_dict["last_name"],
            "fullName": self.full_name,
            "isActive": base_dict["is_active"],
            "isVerified": base_dict["is_verified"],
            "isSuperuser": base_dict["is_superuser"],
            "emailVerifiedAt": base_dict["email_verified_at"],
            "lastLoginAt": base_dict["last_login_at"],
            "loginCount": base_dict["login_count"],
            # CMS-specific fields
            "phoneNumber": base_dict["phone_number"],
            "marketingConsent": base_dict["marketing_consent"],
            "termsAccepted": base_dict["terms_accepted"],
            "collegeId": base_dict["college_id"],
            "departmentId": base_dict["department_id"],
            "cmsRole": base_dict["cms_role"],
            "invitationStatus": base_dict["invitation_status"],
            "temporaryPassword": base_dict["temporary_password"],
            "mustResetPassword": base_dict["must_reset_password"],
            "canAssignDepartment": base_dict["can_assign_department"],
            "invitedByCmsUserId": base_dict["invited_by_cms_user_id"],
            "isHod": base_dict["is_hod"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"]
        }
        
        if include_sensitive:
            result["hashedPassword"] = base_dict["hashed_password"]
        
        return result
    
    def to_token_payload(self) -> dict:
        """Create payload for JWT token"""
        return {
            "sub": str(self.uuid),  # Subject (user identifier)
            "email": self.email,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "isVerified": self.is_verified,
            "isSuperuser": self.is_superuser,
            # CMS-specific token data
            "cmsRole": self.cms_role,
            "collegeId": self.college_id,
            "departmentId": self.department_id,
            "invitationStatus": self.invitation_status,
            "mustResetPassword": self.must_reset_password
        }