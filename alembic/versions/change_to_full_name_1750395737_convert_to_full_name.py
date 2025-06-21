"""Convert first_name and last_name to full_name

Revision ID: change_to_full_name_1750395737
Revises: 11f4247f604f
Create Date: 2025-06-20 10:32:17.109431

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'change_to_full_name_1750395737'
down_revision: Union[str, Sequence[str], None] = '11f4247f604f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema to use full_name instead of first_name and last_name"""
    # First, add the new full_name column
    op.add_column('staff', sa.Column('full_name', sa.String(length=200), nullable=True))
    
    # Populate full_name with concatenated first_name and last_name
    op.execute("""
        UPDATE staff 
        SET full_name = CONCAT(first_name, ' ', last_name)
        WHERE first_name IS NOT NULL AND last_name IS NOT NULL
    """)
    
    # Make full_name NOT NULL after populating
    op.alter_column('staff', 'full_name', nullable=False)
    
    # Drop the old columns
    op.drop_column('staff', 'first_name')
    op.drop_column('staff', 'last_name')

def downgrade() -> None:
    """Downgrade schema back to first_name and last_name"""
    # Add back the original columns
    op.add_column('staff', sa.Column('first_name', sa.String(length=100), nullable=True))
    op.add_column('staff', sa.Column('last_name', sa.String(length=100), nullable=True))
    
    # Try to split full_name back into first_name and last_name
    # This is a best-effort approach and may not be perfect for all names
    op.execute("""
        UPDATE staff 
        SET 
            first_name = SPLIT_PART(full_name, ' ', 1),
            last_name = CASE 
                WHEN POSITION(' ' IN full_name) > 0 
                THEN SUBSTRING(full_name FROM POSITION(' ' IN full_name) + 1)
                ELSE ''
            END
        WHERE full_name IS NOT NULL
    """)
    
    # Make the columns NOT NULL
    op.alter_column('staff', 'first_name', nullable=False)
    op.alter_column('staff', 'last_name', nullable=False)
    
    # Drop the full_name column
    op.drop_column('staff', 'full_name')
