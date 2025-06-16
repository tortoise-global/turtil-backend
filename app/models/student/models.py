import uuid

from sqlalchemy import (
    DECIMAL,
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base
from app.models.cms.models import Branch, CMSUser, College, Degree, Department, Subject, UUID

student_user_role = ENUM("student", name="student_user_role", create_type=False)


class StudentUser(Base):
    __tablename__ = "student_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    role = Column(student_user_role, default="student")
    student_id = Column(String(50), unique=True, nullable=False)
    roll_number = Column(String(50))
    admission_number = Column(String(50))
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    degree_id = Column(UUID(as_uuid=True), ForeignKey("degrees.id"))
    batch_year = Column(Integer)
    current_semester = Column(Integer)
    admission_date = Column(Date)
    graduation_date = Column(Date)
    profile_image_url = Column(Text)
    guardian_name = Column(String(255))
    guardian_phone = Column(String(20))
    emergency_contact = Column(String(20))
    blood_group = Column(String(5))
    date_of_birth = Column(Date)
    gender = Column(String(10))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    last_login = Column(BigInteger)
    created_at = Column(
        BigInteger,
        nullable=False,
        default=func.extract("epoch", func.now()).cast(Integer),
    )
    updated_at = Column(
        BigInteger,
        nullable=True,
        onupdate=func.extract("epoch", func.now()).cast(Integer),
    )

    college = relationship("College")
    department = relationship("Department")
    branch = relationship("Branch")
    degree = relationship("Degree")
