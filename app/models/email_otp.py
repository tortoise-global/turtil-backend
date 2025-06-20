from sqlalchemy import Column, String, Integer
from app.models.base import BaseModel


class CmsEmailOTP(BaseModel):
    """
    Email OTP model - exactly matching your existing code structure.
    This model stores OTP codes for email verification.
    """

    __tablename__ = "cms_email_otp"

    email = Column(String(255), nullable=False, index=True)
    otp = Column(Integer, nullable=False)
    expiry = Column(Integer, nullable=False)  # Unix timestamp for expiration

    def __repr__(self):
        return f"<CmsEmailOTP(id={self.id}, email={self.email})>"

    @property
    def is_expired(self) -> bool:
        """Check if OTP has expired"""
        from datetime import datetime, timezone

        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        return current_timestamp > self.expiry

    def to_dict(self) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        return {
            "id": base_dict["id"],
            "email": base_dict["email"],
            "otp": base_dict["otp"],
            "expiry": base_dict["expiry"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
            "isExpired": self.is_expired,
        }
