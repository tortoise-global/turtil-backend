from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid
from datetime import datetime, timezone


class Student(UUIDBaseModel):
    """Student model with UUID primary key for mobile app authentication and academic tracking"""

    __tablename__ = "students"

    # UUID Primary Key - descriptive and intuitive
    student_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Basic student information
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=False)

    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Email verification
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Last login tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    
    # Push notification token for mobile app
    expo_push_token = Column(String(200), nullable=True, index=True)

    # Registration progress tracking (JSON field for step-by-step flow)
    registration_details = Column(JSON, default={}, nullable=False)
    registration_completed = Column(Boolean, default=False, nullable=False)

    # Final academic assignment (populated after complete registration)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.college_id"), nullable=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.section_id"), nullable=True)

    # Student identifiers (assigned after section selection)
    admission_number = Column(String(50), unique=True, nullable=True, index=True)
    roll_number = Column(String(50), nullable=True, index=True)
    
    # Approval workflow fields
    approval_status = Column(String(20), default="pending", nullable=False, index=True)  # "pending", "approved", "rejected"
    approved_by_staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.staff_id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(String(500), nullable=True)

    # Relationships
    college = relationship("College", foreign_keys=[college_id])
    section = relationship("Section", foreign_keys=[section_id])
    sessions = relationship("UserSession", back_populates="student")
    approved_by_staff = relationship("Staff", foreign_keys=[approved_by_staff_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_student_college_roll', 'college_id', 'roll_number', unique=True),
        Index('idx_student_college_approval', 'college_id', 'approval_status'),
        Index('idx_student_section_approval', 'section_id', 'approval_status'),
    )

    def __repr__(self):
        return f"<Student(student_id={self.student_id}, email={self.email})>"

    def verify_email(self):
        """Mark email as verified"""
        self.is_verified = True
        self.email_verified_at = datetime.now(timezone.utc)

    def record_login(self):
        """Record a successful login"""
        self.last_login_at = datetime.now(timezone.utc)
        self.login_count += 1
    
    def update_expo_push_token(self, token: str):
        """Update the Expo push notification token"""
        self.expo_push_token = token

    def update_registration_step(self, step: str, data: dict, reset_approval: bool = True):
        """Update registration progress with new step data"""
        if not self.registration_details:
            self.registration_details = {}
        
        # Update the step data
        self.registration_details.update(data)
        self.registration_details["current_step"] = step
        self.registration_details["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Reset approval status if making changes after initial registration
        if reset_approval and self.registration_completed:
            self.approval_status = "pending"
            self.approved_by_staff_id = None
            self.approved_at = None
            self.rejection_reason = None

    def complete_registration(self, college_id: uuid.UUID, section_id: uuid.UUID, admission_number: str = None, roll_number: str = None):
        """Complete the registration process and assign final academic details"""
        self.college_id = college_id
        self.section_id = section_id
        self.registration_completed = True
        self.approval_status = "pending"  # Set to pending approval by default
        
        if admission_number:
            self.admission_number = admission_number
            
        if roll_number:
            self.roll_number = roll_number
        
        # Update registration details to mark completion
        if not self.registration_details:
            self.registration_details = {}
        self.registration_details["current_step"] = "completed"
        self.registration_details["completed_at"] = datetime.now(timezone.utc).isoformat()

    def get_registration_progress(self) -> dict:
        """Get current registration progress"""
        if not self.registration_details:
            return {"current_step": "college_selection", "progress_percentage": 0}
        
        # Define step progression for progress calculation
        steps = ["college_selection", "term_selection", "graduation_selection", 
                "degree_selection", "branch_selection", "section_selection", "completed"]
        
        current_step = self.registration_details.get("current_step", "college_selection")
        
        try:
            step_index = steps.index(current_step)
            progress_percentage = int((step_index / (len(steps) - 1)) * 100)
        except ValueError:
            progress_percentage = 0
        
        return {
            "current_step": current_step,
            "progress_percentage": progress_percentage,
            "details": self.registration_details
        }

    def approve_student(self, approved_by_staff_id: uuid.UUID):
        """Approve student registration"""
        self.approval_status = "approved"
        self.approved_by_staff_id = approved_by_staff_id
        self.approved_at = datetime.now(timezone.utc)
        self.rejection_reason = None  # Clear any previous rejection reason
    
    def reject_student(self, approved_by_staff_id: uuid.UUID, reason: str = None):
        """Reject student registration"""
        self.approval_status = "rejected"
        self.approved_by_staff_id = approved_by_staff_id
        self.approved_at = datetime.now(timezone.utc)
        self.rejection_reason = reason
    
    def can_access_app(self) -> bool:
        """Check if student can access the main app features"""
        return self.is_verified and self.is_active and self.registration_completed and self.approval_status == "approved"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert to dictionary with camelCase for API responses.
        Excludes sensitive information by default.
        """
        base_dict = super().to_dict()
        result = {
            "studentId": base_dict["student_id"],
            "email": base_dict["email"],
            "fullName": base_dict["full_name"],
            "isActive": base_dict["is_active"],
            "isVerified": base_dict["is_verified"],
            "emailVerifiedAt": base_dict["email_verified_at"],
            "lastLoginAt": base_dict["last_login_at"],
            "loginCount": base_dict["login_count"],
            "expoPushToken": base_dict["expo_push_token"],
            "registrationDetails": base_dict["registration_details"],
            "registrationCompleted": base_dict["registration_completed"],
            "collegeId": base_dict["college_id"],
            "sectionId": base_dict["section_id"],
            "admissionNumber": base_dict["admission_number"],
            "rollNumber": base_dict["roll_number"],
            "approvalStatus": base_dict["approval_status"],
            "approvedByStaffId": base_dict["approved_by_staff_id"],
            "approvedAt": base_dict["approved_at"],
            "rejectionReason": base_dict["rejection_reason"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"],
        }

        if include_sensitive:
            result["hashedPassword"] = base_dict["hashed_password"]

        return result

    def to_token_payload(self) -> dict:
        """Create JWT token payload for student authentication"""
        return {
            "sub": str(self.student_id),
            "email": self.email,
            "collegeId": str(self.college_id) if self.college_id else None,
            "sectionId": str(self.section_id) if self.section_id else None,
            "registrationCompleted": self.registration_completed,
            "approvalStatus": self.approval_status,
            "canAccessApp": self.can_access_app()
        }