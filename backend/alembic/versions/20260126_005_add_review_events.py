"""Add review events and tracking start date

Revision ID: 20260126_005
Revises: 20260125_004
Create Date: 2026-01-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260126_005"
down_revision: Union[str, None] = "20260125_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tracking start date to users
    op.add_column("users", sa.Column("review_tracking_start_date", sa.Date(), nullable=True))

    # Create review_events table
    op.create_table(
        "review_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.String(36), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("rescheduled_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_review_events_user_id", "review_events", ["user_id"], unique=False)
    op.create_index(
        "ix_review_events_subject_due_date",
        "review_events",
        ["subject_id", "due_date"],
        unique=True
    )
    op.create_index("ix_review_events_rescheduled_to", "review_events", ["rescheduled_to"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_review_events_rescheduled_to", table_name="review_events")
    op.drop_index("ix_review_events_subject_due_date", table_name="review_events")
    op.drop_index("ix_review_events_user_id", table_name="review_events")
    op.drop_table("review_events")
    op.drop_column("users", "review_tracking_start_date")
