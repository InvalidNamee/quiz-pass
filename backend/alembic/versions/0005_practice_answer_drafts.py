"""add practice answer draft flag

Revision ID: 0005_answer_drafts
Revises: 0004_ai_workflow_ctx
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_answer_drafts"
down_revision = "0004_ai_workflow_ctx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("practice_answers")}
    if "is_submitted" not in columns:
        op.add_column(
            "practice_answers",
            sa.Column("is_submitted", sa.Boolean(), server_default=sa.true(), nullable=False),
        )


def downgrade() -> None:
    pass
