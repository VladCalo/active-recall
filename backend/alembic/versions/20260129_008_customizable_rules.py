"""Per-user customizable interval ladders + no-revision-day rule

Revision ID: 20260129_008
Revises: 20260128_007
Create Date: 2026-01-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260129_008"
down_revision: Union[str, None] = "20260128_007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("custom_ladders", sa.JSON(), nullable=True))
    op.add_column(
        "users",
        sa.Column("no_revision_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "users",
        sa.Column("no_revision_weekday", sa.Integer(), nullable=False, server_default="6"),
    )


def downgrade() -> None:
    op.drop_column("users", "no_revision_weekday")
    op.drop_column("users", "no_revision_enabled")
    op.drop_column("users", "custom_ladders")
