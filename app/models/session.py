from sqlalchemy import Column, String, Integer, Text, Boolean, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel
import uuid


class UserSession(BaseModel):
    """User Session model for multi-device authentication tracking"""

    __tablename__ = "user_sessions"

    # Use UUID for session identification
    session_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True, nullable=False)

    # Foreign key to staff
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False, index=True)

    # Device and browser information
    browser = Column(String(100), nullable=True)  # "Chrome", "Firefox", "Safari"
    os = Column(String(100), nullable=True)       # "macOS", "Windows", "Linux"
    device = Column(String(100), nullable=True)   # "Desktop", "Mobile", "Tablet"
    user_agent = Column(Text, nullable=True)      # Full user agent string

    # Session security
    refresh_token_hash = Column(String(255), nullable=False)  # Hashed refresh token
    
    # Session tracking
    created_at_timestamp = Column(BigInteger, nullable=False)  # Unix timestamp
    last_used_timestamp = Column(BigInteger, nullable=False)   # Unix timestamp
    expires_at_timestamp = Column(BigInteger, nullable=False)  # Unix timestamp
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)

    # IP tracking (optional)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 support
    location = Column(String(200), nullable=True)   # City, Country (optional)

    def __repr__(self):
        return f"<UserSession(session_id={self.session_id}, staff_id={self.staff_id}, device={self.device})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert to dictionary with camelCase for API responses.
        """
        base_dict = super().to_dict()
        result = {
            "id": base_dict["id"],
            "sessionId": str(self.session_id),
            "staffId": base_dict["staff_id"],
            "browser": base_dict["browser"],
            "os": base_dict["os"],
            "device": base_dict["device"],
            "createdAt": base_dict["created_at_timestamp"],
            "lastUsed": base_dict["last_used_timestamp"],
            "expiresAt": base_dict["expires_at_timestamp"],
            "isActive": base_dict["is_active"],
            "ipAddress": base_dict["ip_address"] if include_sensitive else None,
            "location": base_dict["location"],
        }

        # Only include user agent if sensitive data is requested
        if include_sensitive:
            result["userAgent"] = base_dict["user_agent"]

        return result

    @property
    def device_display_name(self) -> str:
        """Get human-readable device name for display"""
        parts = []
        if self.browser:
            parts.append(self.browser)
        if self.os:
            parts.append(f"on {self.os}")
        if self.device and self.device.lower() != "desktop":
            parts.append(f"({self.device})")
        
        return " ".join(parts) if parts else "Unknown Device"

    @property
    def is_expired(self) -> bool:
        """Check if session is expired based on timestamp"""
        import time
        return time.time() > self.expires_at_timestamp

    def update_last_used(self):
        """Update last used timestamp to current time"""
        import time
        self.last_used_timestamp = int(time.time())