from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    description = Column(Text)
    website = Column(String)
    contact_email = Column(String)
    contact_phone = Column(String)
    address = Column(Text)
    
    # Company details
    company_size = Column(String)  # Startup, Small, Medium, Large, Enterprise
    company_type = Column(String)  # Private, Public, Government, NGO
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    placement_drives = relationship("PlacementDrive", back_populates="company", cascade="all, delete-orphan")


class PlacementDrive(Base):
    __tablename__ = "placement_drives"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    
    # Drive details
    job_role = Column(String, nullable=False)
    job_type = Column(String, nullable=False)  # Full-time, Internship, Part-time
    location = Column(String, nullable=False)
    salary_min = Column(Float)
    salary_max = Column(Float)
    currency = Column(String, default="INR")
    
    # Requirements
    eligible_programs = Column(Text)  # JSON string of program IDs
    min_cgpa = Column(Float)
    max_backlogs = Column(Integer, default=0)
    required_skills = Column(Text)  # JSON string of skills
    
    # Drive timeline
    registration_start = Column(DateTime(timezone=True), nullable=False)
    registration_end = Column(DateTime(timezone=True), nullable=False)
    drive_date = Column(Date, nullable=False)
    
    # Status
    status = Column(String, default="upcoming")  # upcoming, ongoing, completed, cancelled
    is_active = Column(Boolean, default=True)
    
    # Stats
    total_registered = Column(Integer, default=0)
    total_selected = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="placement_drives")
    institute = relationship("Institute")
    applications = relationship("PlacementApplication", back_populates="placement_drive", cascade="all, delete-orphan")


class PlacementApplication(Base):
    __tablename__ = "placement_applications"

    id = Column(Integer, primary_key=True, index=True)
    placement_drive_id = Column(Integer, ForeignKey("placement_drives.id"), nullable=False)
    student_email = Column(String, nullable=False)  # For now, using email instead of student relationship
    student_name = Column(String, nullable=False)
    student_program = Column(String, nullable=False)
    
    # Application details
    resume_url = Column(String)
    cover_letter = Column(Text)
    cgpa = Column(Float, nullable=False)
    current_backlogs = Column(Integer, default=0)
    skills = Column(Text)  # JSON string of skills
    
    # Application status
    status = Column(String, default="applied")  # applied, shortlisted, interview_scheduled, selected, rejected
    interview_date = Column(DateTime(timezone=True))
    interview_feedback = Column(Text)
    final_result = Column(String)  # selected, rejected, waitlisted
    
    # Timestamps
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    placement_drive = relationship("PlacementDrive", back_populates="applications")