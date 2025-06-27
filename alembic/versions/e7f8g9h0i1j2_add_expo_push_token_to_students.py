"""add expo push token to students

Revision ID: e7f8g9h0i1j2
Revises: f1a2b3c4d5e6
Create Date: 2024-12-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7f8g9h0i1j2'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add expo_push_token column to students table
    op.add_column('students', sa.Column('expo_push_token', sa.String(length=200), nullable=True))
    
    # Create index on expo_push_token for performance
    op.create_index('idx_students_expo_push_token', 'students', ['expo_push_token'], unique=False)


def downgrade() -> None:
    # Drop index first
    op.drop_index('idx_students_expo_push_token', table_name='students')
    
    # Drop the column
    op.drop_column('students', 'expo_push_token')