"""create attendance sessions tables

Revision ID: 004
Revises: 003
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create attendance sessions and records tables for CENSEUR module."""
    
    # Create attendance_sessions table
    op.create_table(
        'attendance_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_time', sa.String(10), nullable=False, server_default='07h30'),
        sa.Column('location', sa.String(100), nullable=False, server_default='Sacristie'),
        sa.Column('conducted_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['conducted_by'], ['users.id'], ondelete='RESTRICT'),
    )
    
    # Create attendance_records table
    op.create_table(
        'attendance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('servant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),  # PRESENT, ABSENT, LATE, EXCUSED
        sa.Column('arrival_time', sa.String(10), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('recorded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['servant_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ondelete='RESTRICT'),
        
        # Constraints
        sa.CheckConstraint(
            "status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED')",
            name='check_status_valid'
        ),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_attendance_sessions_date', 'attendance_sessions', ['session_date'])
    op.create_index('idx_attendance_sessions_conducted_by', 'attendance_sessions', ['conducted_by'])
    
    op.create_index('idx_attendance_records_session_id', 'attendance_records', ['session_id'])
    op.create_index('idx_attendance_records_servant_id', 'attendance_records', ['servant_id'])
    op.create_index('idx_attendance_records_status', 'attendance_records', ['status'])
    
    # Composite index for common queries
    op.create_index(
        'idx_attendance_records_servant_session',
        'attendance_records',
        ['servant_id', 'session_id']
    )


def downgrade() -> None:
    """Drop attendance sessions and records tables."""
    op.drop_index('idx_attendance_records_servant_session', table_name='attendance_records')
    op.drop_index('idx_attendance_records_status', table_name='attendance_records')
    op.drop_index('idx_attendance_records_servant_id', table_name='attendance_records')
    op.drop_index('idx_attendance_records_session_id', table_name='attendance_records')
    op.drop_index('idx_attendance_sessions_conducted_by', table_name='attendance_sessions')
    op.drop_index('idx_attendance_sessions_date', table_name='attendance_sessions')
    op.drop_table('attendance_records')
    op.drop_table('attendance_sessions')
