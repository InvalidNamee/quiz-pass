"""question bank tags

Revision ID: 0002_question_bank_tags
Revises: 0001_initial
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_question_bank_tags"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_bank_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_bank_tags_name"), "question_bank_tags", ["name"], unique=True)
    op.create_table(
        "question_bank_tag_links",
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["question_bank_tags.id"]),
        sa.PrimaryKeyConstraint("bank_id", "tag_id"),
        sa.UniqueConstraint("bank_id", "tag_id", name="uq_question_bank_tag_link"),
    )


def downgrade() -> None:
    op.drop_table("question_bank_tag_links")
    op.drop_index(op.f("ix_question_bank_tags_name"), table_name="question_bank_tags")
    op.drop_table("question_bank_tags")
