"""Per-user editable exam date (Final Recall cutoff / Reference Mode end derive from it)

Revision ID: 20260128_007
Revises: 20260127_006
Create Date: 2026-01-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260128_007"
down_revision: Union[str, None] = "20260127_006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("exam_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "exam_date")
