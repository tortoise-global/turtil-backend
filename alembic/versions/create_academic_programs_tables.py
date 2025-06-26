"""Create academic programs tables

Revision ID: create_academic_programs
Revises: 37b2cb331c35
Create Date: 2025-06-26 09:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_academic_programs'
down_revision: Union[str, Sequence[str], None] = '37b2cb331c35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create academic programs tables."""
    
    # Create terms table
    op.create_table('terms',
        sa.Column('term_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('batch_year', sa.Integer(), nullable=False),
        sa.Column('current_year', sa.Integer(), nullable=False),
        sa.Column('current_semester', sa.Integer(), nullable=False),
        sa.Column('term_name', sa.String(length=255), nullable=False),
        sa.Column('term_code', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_ongoing', sa.Boolean(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('college_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('current_year >= 1 AND current_year <= 4', name='check_current_year'),
        sa.CheckConstraint('current_semester >= 1 AND current_semester <= 2', name='check_current_semester'),
        sa.CheckConstraint('batch_year >= 2020 AND batch_year <= 2050', name='check_batch_year'),
        sa.CheckConstraint('end_date > start_date', name='check_date_order'),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.college_id'], ),
        sa.PrimaryKeyConstraint('term_id'),
        sa.UniqueConstraint('college_id', 'batch_year', 'current_year', 'current_semester', name='unique_college_term')
    )
    op.create_index('ix_terms_term_id', 'terms', ['term_id'])
    op.create_index('ix_terms_batch_year', 'terms', ['batch_year'])
    op.create_index('ix_terms_current_year', 'terms', ['current_year'])
    op.create_index('ix_terms_current_semester', 'terms', ['current_semester'])
    op.create_index('ix_terms_term_code', 'terms', ['term_code'])

    # Create graduations table
    op.create_table('graduations',
        sa.Column('graduation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('graduation_name', sa.String(length=255), nullable=False),
        sa.Column('graduation_code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('term_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['term_id'], ['terms.term_id'], ),
        sa.PrimaryKeyConstraint('graduation_id'),
        sa.UniqueConstraint('term_id', 'graduation_code', name='unique_term_graduation_code')
    )
    op.create_index('ix_graduations_graduation_id', 'graduations', ['graduation_id'])

    # Create degrees table
    op.create_table('degrees',
        sa.Column('degree_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('degree_name', sa.String(length=255), nullable=False),
        sa.Column('degree_code', sa.String(length=20), nullable=False),
        sa.Column('short_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('graduation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['graduation_id'], ['graduations.graduation_id'], ),
        sa.PrimaryKeyConstraint('degree_id'),
        sa.UniqueConstraint('graduation_id', 'degree_code', name='unique_graduation_degree_code')
    )
    op.create_index('ix_degrees_degree_id', 'degrees', ['degree_id'])

    # Create branches table
    op.create_table('branches',
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('branch_name', sa.String(length=255), nullable=False),
        sa.Column('branch_code', sa.String(length=20), nullable=False),
        sa.Column('short_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('degree_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['degree_id'], ['degrees.degree_id'], ),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id'], ),
        sa.PrimaryKeyConstraint('branch_id'),
        sa.UniqueConstraint('degree_id', 'branch_code', name='unique_degree_branch_code')
    )
    op.create_index('ix_branches_branch_id', 'branches', ['branch_id'])

    # Create subjects table
    op.create_table('subjects',
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_name', sa.String(length=255), nullable=False),
        sa.Column('subject_code', sa.String(length=20), nullable=False),
        sa.Column('short_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('subject_type', sa.String(length=20), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('credits >= 1 AND credits <= 8', name='check_credits_range'),
        sa.CheckConstraint("subject_type IN ('theory', 'practical', 'project', 'elective')", name='check_subject_type'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.branch_id'], ),
        sa.PrimaryKeyConstraint('subject_id'),
        sa.UniqueConstraint('branch_id', 'subject_code', name='unique_branch_subject_code')
    )
    op.create_index('ix_subjects_subject_id', 'subjects', ['subject_id'])

    # Create sections table
    op.create_table('sections',
        sa.Column('section_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_name', sa.String(length=100), nullable=False),
        sa.Column('section_code', sa.String(length=10), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('student_capacity', sa.Integer(), nullable=False),
        sa.Column('current_strength', sa.Integer(), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('class_teacher_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('student_capacity >= 1 AND student_capacity <= 200', name='check_student_capacity'),
        sa.CheckConstraint('current_strength >= 0', name='check_current_strength'),
        sa.CheckConstraint('current_strength <= student_capacity', name='check_strength_within_capacity'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.branch_id'], ),
        sa.ForeignKeyConstraint(['class_teacher_id'], ['staff.staff_id'], ),
        sa.PrimaryKeyConstraint('section_id'),
        sa.UniqueConstraint('branch_id', 'section_code', name='unique_branch_section_code')
    )
    op.create_index('ix_sections_section_id', 'sections', ['section_id'])

    # Create section_subjects table
    op.create_table('section_subjects',
        sa.Column('section_subject_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_staff_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_staff_id'], ['staff.staff_id'], ),
        sa.ForeignKeyConstraint(['section_id'], ['sections.section_id'], ),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.subject_id'], ),
        sa.PrimaryKeyConstraint('section_subject_id'),
        sa.UniqueConstraint('section_id', 'subject_id', name='unique_section_subject')
    )
    op.create_index('ix_section_subjects_section_subject_id', 'section_subjects', ['section_subject_id'])


def downgrade() -> None:
    """Drop academic programs tables."""
    op.drop_table('section_subjects')
    op.drop_table('sections')
    op.drop_table('subjects')
    op.drop_table('branches')
    op.drop_table('degrees')
    op.drop_table('graduations')
    op.drop_table('terms')