"""add concrete mistake attempts

Revision ID: 0010_mistake_attempts
Revises: 0009_four_question_types
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_mistake_attempts"
down_revision = "0009_four_question_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("practice_sessions", sa.Column("mistake_source_type", sa.String(length=32), nullable=True))
    op.add_column("practice_sessions", sa.Column("mistake_source_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_practice_sessions_mistake_source_type"), "practice_sessions", ["mistake_source_type"], unique=False)
    op.create_index(op.f("ix_practice_sessions_mistake_source_id"), "practice_sessions", ["mistake_source_id"], unique=False)
    op.create_table(
        "mistake_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("practice_session_id", sa.Integer(), nullable=False),
        sa.Column("practice_answer_id", sa.Integer(), nullable=True),
        sa.Column("question_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("user_answer_json", sa.JSON(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False),
        sa.Column("wrong_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["practice_answer_id"], ["practice_answers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["practice_session_id"], ["practice_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mistake_attempts_bank_id"), "mistake_attempts", ["bank_id"], unique=False)
    op.create_index(op.f("ix_mistake_attempts_is_resolved"), "mistake_attempts", ["is_resolved"], unique=False)
    op.create_index(op.f("ix_mistake_attempts_practice_answer_id"), "mistake_attempts", ["practice_answer_id"], unique=False)
    op.create_index(op.f("ix_mistake_attempts_practice_session_id"), "mistake_attempts", ["practice_session_id"], unique=False)
    op.create_index(op.f("ix_mistake_attempts_question_id"), "mistake_attempts", ["question_id"], unique=False)
    op.create_index(op.f("ix_mistake_attempts_user_id"), "mistake_attempts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mistake_attempts_user_id"), table_name="mistake_attempts")
    op.drop_index(op.f("ix_mistake_attempts_question_id"), table_name="mistake_attempts")
    op.drop_index(op.f("ix_mistake_attempts_practice_session_id"), table_name="mistake_attempts")
    op.drop_index(op.f("ix_mistake_attempts_practice_answer_id"), table_name="mistake_attempts")
    op.drop_index(op.f("ix_mistake_attempts_is_resolved"), table_name="mistake_attempts")
    op.drop_index(op.f("ix_mistake_attempts_bank_id"), table_name="mistake_attempts")
    op.drop_table("mistake_attempts")
    op.drop_index(op.f("ix_practice_sessions_mistake_source_id"), table_name="practice_sessions")
    op.drop_index(op.f("ix_practice_sessions_mistake_source_type"), table_name="practice_sessions")
    op.drop_column("practice_sessions", "mistake_source_id")
    op.drop_column("practice_sessions", "mistake_source_type")
