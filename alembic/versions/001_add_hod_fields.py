"""Add is_hod field to users and hod_cms_user_id FK to departments

Revision ID: 001_add_hod_fields
Revises: 
Create Date: 2025-06-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_hod_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_hod column to users table
    op.add_column('users', sa.Column('is_hod', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add hod_cms_user_id column to departments table
    op.add_column('departments', sa.Column('hod_cms_user_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint for hod_cms_user_id
    op.create_foreign_key(
        'fk_departments_hod_cms_user_id', 
        'departments', 
        'users', 
        ['hod_cms_user_id'], 
        ['id']
    )


def downgrade() -> None:
    # Remove foreign key constraint
    op.drop_constraint('fk_departments_hod_cms_user_id', 'departments', type_='foreignkey')
    
    # Remove hod_cms_user_id column from departments table
    op.drop_column('departments', 'hod_cms_user_id')
    
    # Remove is_hod column from users table
    op.drop_column('users', 'is_hod')