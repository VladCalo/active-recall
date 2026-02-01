"""Add admin and disabled fields to users

Revision ID: 20260125_004
Revises: 003
Create Date: 2026-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260125_004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_admin column with default False
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'))
    op.create_index(op.f('ix_users_is_admin'), 'users', ['is_admin'], unique=False)
    
    # Add is_disabled column with default False
    op.add_column('users', sa.Column('is_disabled', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'is_disabled')
    op.drop_index(op.f('ix_users_is_admin'), table_name='users')
    op.drop_column('users', 'is_admin')
