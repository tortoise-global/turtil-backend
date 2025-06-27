"""add notifications table

Revision ID: j3k4l5m6n7o8
Revises: e7f8g9h0i1j2
Create Date: 2024-12-26 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'j3k4l5m6n7o8'
down_revision = 'e7f8g9h0i1j2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notifications table
    op.create_table('notifications',
        sa.Column('notification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('data_payload', sa.JSON(), nullable=True),
        sa.Column('sound', sa.String(length=50), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('ttl', sa.Integer(), nullable=True),
        sa.Column('expiration', sa.Integer(), nullable=True),
        sa.Column('college_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sent_by_staff_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_student_ids', sa.JSON(), nullable=False),
        sa.Column('successful_student_ids', sa.JSON(), nullable=True),
        sa.Column('failed_student_ids', sa.JSON(), nullable=True),
        sa.Column('expo_tickets', sa.JSON(), nullable=True),
        sa.Column('expo_receipt_ids', sa.JSON(), nullable=True),
        sa.Column('expo_receipts', sa.JSON(), nullable=True),
        sa.Column('total_requested', sa.Integer(), nullable=False),
        sa.Column('total_with_valid_tokens', sa.Integer(), nullable=False),
        sa.Column('total_sent_successfully', sa.Integer(), nullable=False),
        sa.Column('total_failed', sa.Integer(), nullable=False),
        sa.Column('notification_status', sa.String(length=20), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('max_retries', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.college_id'], ),
        sa.ForeignKeyConstraint(['sent_by_staff_id'], ['staff.staff_id'], ),
        sa.PrimaryKeyConstraint('notification_id')
    )
    
    # Create indexes for performance
    op.create_index('idx_notifications_notification_id', 'notifications', ['notification_id'], unique=False)
    op.create_index('idx_notifications_college_id', 'notifications', ['college_id'], unique=False)
    op.create_index('idx_notifications_status', 'notifications', ['notification_status'], unique=False)
    op.create_index('idx_notifications_sent_at', 'notifications', ['sent_at'], unique=False)
    op.create_index('idx_notifications_college_status', 'notifications', ['college_id', 'notification_status'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_notifications_college_status', table_name='notifications')
    op.drop_index('idx_notifications_sent_at', table_name='notifications')
    op.drop_index('idx_notifications_status', table_name='notifications')
    op.drop_index('idx_notifications_college_id', table_name='notifications')
    op.drop_index('idx_notifications_notification_id', table_name='notifications')
    
    # Drop the table
    op.drop_table('notifications')