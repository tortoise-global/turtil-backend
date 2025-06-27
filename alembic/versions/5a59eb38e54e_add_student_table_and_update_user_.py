"""Add student table and update user sessions for student support

Revision ID: 5a59eb38e54e
Revises: create_academic_programs
Create Date: 2025-06-27 02:38:47.848095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a59eb38e54e'
down_revision: Union[str, Sequence[str], None] = 'create_academic_programs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create students table first
    op.create_table('students',
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=200), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_verified', sa.Boolean(), nullable=False),
    sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('login_count', sa.Integer(), nullable=False),
    sa.Column('registration_details', sa.JSON(), nullable=False),
    sa.Column('registration_completed', sa.Boolean(), nullable=False),
    sa.Column('college_id', sa.UUID(), nullable=True),
    sa.Column('section_id', sa.UUID(), nullable=True),
    sa.Column('admission_number', sa.String(length=50), nullable=True),
    sa.Column('roll_number', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['college_id'], ['colleges.college_id'], name='fk_students_college_id_colleges'),
    sa.ForeignKeyConstraint(['section_id'], ['sections.section_id'], name='fk_students_section_id_sections'),
    sa.PrimaryKeyConstraint('student_id'),
    sa.UniqueConstraint('admission_number'),
    sa.UniqueConstraint('email')
    )
    op.create_index('ix_students_admission_number', 'students', ['admission_number'], unique=False)
    op.create_index('ix_students_email', 'students', ['email'], unique=False)
    op.create_index('ix_students_roll_number', 'students', ['roll_number'], unique=False)
    op.create_index('ix_students_student_id', 'students', ['student_id'], unique=False)
    
    # Update user_sessions table
    op.add_column('user_sessions', sa.Column('student_id', sa.UUID(), nullable=True))
    
    # Add session_type column with default value first
    op.add_column('user_sessions', sa.Column('session_type', sa.String(length=20), nullable=True))
    
    # Update existing rows to set session_type to 'staff'
    op.execute("UPDATE user_sessions SET session_type = 'staff' WHERE session_type IS NULL")
    
    # Now make session_type NOT NULL
    op.alter_column('user_sessions', 'session_type', nullable=False)
    
    # Make staff_id nullable
    op.alter_column('user_sessions', 'staff_id',
               existing_type=sa.UUID(),
               nullable=True)
    
    # Add indexes and foreign keys
    op.create_index(op.f('ix_user_sessions_student_id'), 'user_sessions', ['student_id'], unique=False)
    op.create_foreign_key(op.f('fk_user_sessions_student_id_students'), 'user_sessions', 'students', ['student_id'], ['student_id'])
    
    # Add check constraint for user type validation
    op.create_check_constraint(
        'check_user_type',
        'user_sessions',
        "(staff_id IS NOT NULL AND student_id IS NULL AND session_type = 'staff') OR (student_id IS NOT NULL AND staff_id IS NULL AND session_type = 'student')"
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # Drop check constraint
    op.drop_constraint('check_user_type', 'user_sessions', type_='check')
    
    # Drop user_sessions modifications
    op.drop_constraint(op.f('fk_user_sessions_student_id_students'), 'user_sessions', type_='foreignkey')
    op.drop_index(op.f('ix_user_sessions_student_id'), table_name='user_sessions')
    op.alter_column('user_sessions', 'staff_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('user_sessions', 'session_type')
    op.drop_column('user_sessions', 'student_id')
    
    # Drop students table
    op.drop_index('ix_students_student_id', table_name='students')
    op.drop_index('ix_students_roll_number', table_name='students')
    op.drop_index('ix_students_email', table_name='students')
    op.drop_index('ix_students_admission_number', table_name='students')
    op.drop_table('students')
    # ### end Alembic commands ###
