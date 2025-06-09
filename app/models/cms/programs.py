from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    duration_years = Column(Integer, nullable=False)
    degree_type = Column(String, nullable=False)  # Bachelor, Master, PhD, Diploma, Certificate
    department = Column(String, nullable=False)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    
    # Academic details
    total_credits = Column(Integer)
    admission_capacity = Column(Integer)
    current_enrolled = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_admissions_open = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    institute = relationship("Institute", back_populates="programs")
    courses = relationship("Course", back_populates="program", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    credits = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    
    # Course details
    course_type = Column(String, nullable=False)  # Core, Elective, Lab, Project
    prerequisites = Column(Text)  # JSON string of prerequisite course IDs
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    program = relationship("Program", back_populates="courses")