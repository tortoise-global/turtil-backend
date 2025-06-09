from sqlalchemy import Column, Integer, String, Boolean, JSON, BigInteger
from sqlalchemy.sql import func
from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    college_name = Column(String, nullable=True)
    role = Column(String, nullable=True)
    status = Column(String, nullable=True)
    parent_id = Column(String, nullable=True)
    model_access = Column(JSON, default=list)
    logo = Column(JSON, default=list)
    college_details = Column(JSON, default=list)
    affiliated_university = Column(JSON, default=list)
    address = Column(JSON, default=list)
    result_format = Column(JSON, default=list)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))


class CollegeDegree(Base):
    __tablename__ = "college_degrees"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    college_id = Column(String, nullable=False, index=True)
    college_short_name = Column(String, nullable=False)
    degrees = Column(JSON, default=list)


class CollegePlacement(Base):
    __tablename__ = "college_placements"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    college_id = Column(String, nullable=False, index=True)
    college_short_name = Column(String, nullable=False)
    college_name = Column(String, nullable=False)
    placement_date = Column(BigInteger, nullable=False)
    degree = Column(String, nullable=False)
    company = Column(String, nullable=False)
    batch = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))


class CollegeStudent(Base):
    __tablename__ = "college_students"
    
    id = Column(String, primary_key=True, index=True)
    college_id = Column(String, nullable=False, index=True)
    college_short_name = Column(String, nullable=False, index=True)
    college_name = Column(String, nullable=False)
    student_id = Column(String, nullable=False, index=True)
    student_name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=False)
    degree = Column(String, nullable=False, index=True)
    batch = Column(String, nullable=False, index=True)
    branch = Column(String, nullable=False, index=True)
    section = Column(String, nullable=False, index=True)
    gender = Column(String, nullable=False, index=True)
    created_at = Column(BigInteger, nullable=False, default=func.extract('epoch', func.now()).cast(Integer))
    updated_at = Column(BigInteger, nullable=True, onupdate=func.extract('epoch', func.now()).cast(Integer))