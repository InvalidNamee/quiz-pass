"""add blank and short answer question support

Revision ID: 0009_four_question_types
Revises: 0008_bank_share
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_four_question_types"
down_revision = "0008_bank_share"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_blanks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=16), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_blanks_question_id"), "question_blanks", ["question_id"], unique=False)
    op.add_column("practice_answers", sa.Column("text_answers", sa.JSON(), nullable=True))
    op.execute("UPDATE practice_answers SET text_answers = '[]' WHERE text_answers IS NULL")
    op.add_column("ai_generation_draft_questions", sa.Column("blanks_json", sa.Text(), nullable=True))
    op.execute("UPDATE ai_generation_draft_questions SET blanks_json = '[]' WHERE blanks_json IS NULL")
    op.add_column("ai_generation_workflows", sa.Column("question_type_settings_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_generation_workflows", "question_type_settings_json")
    op.drop_column("ai_generation_draft_questions", "blanks_json")
    op.drop_column("practice_answers", "text_answers")
    op.drop_index(op.f("ix_question_blanks_question_id"), table_name="question_blanks")
    op.drop_table("question_blanks")
