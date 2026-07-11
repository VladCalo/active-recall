"""Adaptive Active Recall engine (category/stage state) + Final Recall / Reference Mode

Revision ID: 20260127_006
Revises: 20260126_005
Create Date: 2026-01-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM


# revision identifiers, used by Alembic.
revision: str = "20260127_006"
down_revision: Union[str, None] = "20260126_005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# create_type=False: the enum types are created explicitly (once) in
# upgrade()/downgrade() below - without this, every add_column/create_table
# that references the same Enum object re-issues CREATE TYPE and fails with
# "type already exists" on Postgres. (Generic sa.Enum's create_type kwarg is
# not reliably honored on create_table - postgresql.ENUM is the documented
# fix for this exact Alembic/Postgres gotcha.)
category_enum = PG_ENUM("HARD", "MEDIUM", "EASY", name="category_enum", create_type=False)
rating_enum = PG_ENUM(
    "MAJOR_GAPS", "MANY_CONFUSIONS", "GOOD_MINOR_HESITATION", "EXCELLENT",
    name="rating_enum", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    category_enum.create(bind, checkfirst=True)
    rating_enum.create(bind, checkfirst=True)

    # Drop the old static-schedule review tracking table entirely - replaced
    # by review_completions (a log of completed sessions, not a
    # precomputed due_date/is_completed toggle).
    op.drop_index("ix_review_events_rescheduled_to", table_name="review_events")
    op.drop_index("ix_review_events_subject_due_date", table_name="review_events")
    op.drop_index("ix_review_events_user_id", table_name="review_events")
    op.drop_table("review_events")

    # Old static-schedule fields on subjects, replaced by the adaptive engine's
    # category/stage state.
    op.drop_column("subjects", "schedule_type")
    op.drop_column("subjects", "custom_intervals_days")
    op.execute("DROP TYPE IF EXISTS scheduletype")

    op.add_column("subjects", sa.Column("category", category_enum, nullable=False, server_default="MEDIUM"))
    op.add_column("subjects", sa.Column("stage", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("subjects", sa.Column("next_due_date", sa.Date(), nullable=True))
    op.add_column("subjects", sa.Column("last_active_recall_date", sa.Date(), nullable=True))
    op.add_column(
        "subjects",
        sa.Column("is_final_recall_reached", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("subjects", sa.Column("final_active_recall_date", sa.Date(), nullable=True))
    op.add_column("subjects", sa.Column("final_category", category_enum, nullable=True))
    op.add_column("subjects", sa.Column("reread_completed_at", sa.DateTime(), nullable=True))

    op.create_table(
        "review_completions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.String(36), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completed_at", sa.Date(), nullable=False),
        sa.Column("rating", rating_enum, nullable=False),
        sa.Column("category_before", category_enum, nullable=False),
        sa.Column("stage_before", sa.Integer(), nullable=False),
        sa.Column("category_after", category_enum, nullable=False),
        sa.Column("stage_after", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_review_completions_user_id", "review_completions", ["user_id"], unique=False)
    op.create_index("ix_review_completions_subject_id", "review_completions", ["subject_id"], unique=False)

    op.drop_column("users", "review_tracking_start_date")


def downgrade() -> None:
    op.add_column("users", sa.Column("review_tracking_start_date", sa.Date(), nullable=True))

    op.drop_index("ix_review_completions_subject_id", table_name="review_completions")
    op.drop_index("ix_review_completions_user_id", table_name="review_completions")
    op.drop_table("review_completions")

    op.drop_column("subjects", "reread_completed_at")
    op.drop_column("subjects", "final_category")
    op.drop_column("subjects", "final_active_recall_date")
    op.drop_column("subjects", "is_final_recall_reached")
    op.drop_column("subjects", "last_active_recall_date")
    op.drop_column("subjects", "next_due_date")
    op.drop_column("subjects", "stage")
    op.drop_column("subjects", "category")

    schedule_type_enum = PG_ENUM("DEFAULT", "CUSTOM", name="scheduletype", create_type=False)
    schedule_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "subjects",
        sa.Column("schedule_type", schedule_type_enum, nullable=False, server_default="DEFAULT"),
    )
    op.add_column("subjects", sa.Column("custom_intervals_days", sa.JSON(), nullable=True))

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
        "ix_review_events_subject_due_date", "review_events", ["subject_id", "due_date"], unique=True
    )
    op.create_index("ix_review_events_rescheduled_to", "review_events", ["rescheduled_to"], unique=False)

    rating_enum.drop(op.get_bind(), checkfirst=True)
    category_enum.drop(op.get_bind(), checkfirst=True)
