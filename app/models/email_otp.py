from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import UUIDBaseModel
import uuid


class CmsEmailOTP(UUIDBaseModel):
    """
    Email OTP model with UUID primary key for email verification.
    This model stores OTP codes for email verification.
    """

    __tablename__ = "cms_email_otp"

    # UUID Primary Key - descriptive and intuitive
    otp_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    email = Column(String(255), nullable=False, index=True)
    otp = Column(Integer, nullable=False)
    expiry = Column(Integer, nullable=False)  # Unix timestamp for expiration

    def __repr__(self):
        return f"<CmsEmailOTP(otp_id={self.otp_id}, email={self.email})>"

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
            "otpId": base_dict["otp_id"],
            "email": base_dict["email"],
            "otp": base_dict["otp"],
            "expiry": base_dict["expiry"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
            "isExpired": self.is_expired,
        }