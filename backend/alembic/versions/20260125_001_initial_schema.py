"""Initial schema - create subjects table

Revision ID: 001
Revises: 
Create Date: 2026-01-25

This migration creates the initial subjects table for tracking
study subjects with active recall scheduling.

Note: The unique constraint on name is temporary - it will be
changed to per-user uniqueness in migration 002.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create subjects table."""
    op.create_table(
        'subjects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column(
            'schedule_type', 
            sa.Enum('DEFAULT', 'CUSTOM', name='scheduletype'), 
            nullable=False,
            server_default='DEFAULT'
        ),
        sa.Column('custom_intervals_days', sa.JSON(), nullable=True),
        sa.Column(
            'created_at', 
            sa.DateTime(), 
            nullable=False, 
            server_default=sa.text('CURRENT_TIMESTAMP')
        ),
        sa.Column(
            'updated_at', 
            sa.DateTime(), 
            nullable=False, 
            server_default=sa.text('CURRENT_TIMESTAMP')
        ),
        # Unique constraint with name for later removal
        sa.UniqueConstraint('name', name='uq_subjects_name'),
    )
    
    # Create index on name for faster lookups
    op.create_index('ix_subjects_name', 'subjects', ['name'])


def downgrade() -> None:
    """Drop subjects table."""
    op.drop_index('ix_subjects_name', table_name='subjects')
    op.drop_table('subjects')
