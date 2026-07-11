"""New self-registrations require admin approval before login

Revision ID: 20260130_009
Revises: 20260129_008
Create Date: 2026-01-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260130_009"
down_revision: Union[str, None] = "20260129_008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default=true so existing users (including the seeded admin)
    # aren't retroactively locked out - only new registrations explicitly
    # set is_approved=False going forward (see AuthService.register).
    op.add_column(
        "users",
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("users", "is_approved")
