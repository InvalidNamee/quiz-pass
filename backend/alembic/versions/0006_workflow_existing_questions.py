"""add workflow existing question context flag

Revision ID: 0006_existing_q_ctx
Revises: 0005_answer_drafts
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_existing_q_ctx"
down_revision = "0005_answer_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("ai_generation_workflows")}
    if "include_existing_questions" not in columns:
        op.add_column(
            "ai_generation_workflows",
            sa.Column("include_existing_questions", sa.Boolean(), server_default=sa.false(), nullable=False),
        )


def downgrade() -> None:
    pass
