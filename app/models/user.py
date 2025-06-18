from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
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
            "id": base_dict["id"],
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
            "isSuperuser": self.is_superuser
        }