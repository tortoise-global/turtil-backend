"""Add student approval workflow and enhanced roll number system

Revision ID: f1a2b3c4d5e6
Revises: 5a59eb38e54e
Create Date: 2025-06-27 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '5a59eb38e54e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add approval workflow fields to students table
    op.add_column('students', sa.Column('approval_status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('students', sa.Column('approved_by_staff_id', sa.UUID(), nullable=True))
    op.add_column('students', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('students', sa.Column('rejection_reason', sa.String(length=500), nullable=True))
    
    # Create indexes for approval status
    op.create_index('ix_students_approval_status', 'students', ['approval_status'], unique=False)
    op.create_index('idx_student_college_approval', 'students', ['college_id', 'approval_status'], unique=False)
    op.create_index('idx_student_section_approval', 'students', ['section_id', 'approval_status'], unique=False)
    
    # Create unique index for college_id + roll_number combination
    op.create_index('idx_student_college_roll', 'students', ['college_id', 'roll_number'], unique=True)
    
    # Add foreign key constraint for approved_by_staff_id
    op.create_foreign_key('fk_students_approved_by_staff_id_staff', 'students', 'staff', ['approved_by_staff_id'], ['staff_id'])
    
    # Update existing students to have 'pending' approval status
    op.execute("UPDATE students SET approval_status = 'pending' WHERE approval_status IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraint
    op.drop_constraint('fk_students_approved_by_staff_id_staff', 'students', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('idx_student_college_roll', table_name='students')
    op.drop_index('idx_student_section_approval', table_name='students')
    op.drop_index('idx_student_college_approval', table_name='students')
    op.drop_index('ix_students_approval_status', table_name='students')
    
    # Drop columns
    op.drop_column('students', 'rejection_reason')
    op.drop_column('students', 'approved_at')
    op.drop_column('students', 'approved_by_staff_id')
    op.drop_column('students', 'approval_status')