"""add question bank shared copy fields

Revision ID: 0008_bank_share
Revises: 0007_queue_audit
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_bank_share"
down_revision = "0007_queue_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("question_banks")}
    missing_source_bank_id = "source_bank_id" not in columns
    missing_is_shared_copy = "is_shared_copy" not in columns
    if missing_source_bank_id or missing_is_shared_copy:
        with op.batch_alter_table("question_banks") as batch_op:
            if missing_source_bank_id:
                batch_op.add_column(
                    sa.Column(
                        "source_bank_id",
                        sa.Integer(),
                        sa.ForeignKey("question_banks.id", name="fk_question_banks_source_bank_id", ondelete="SET NULL"),
                        nullable=True,
                    ),
                )
            if missing_is_shared_copy:
                batch_op.add_column(sa.Column("is_shared_copy", sa.Boolean(), server_default=sa.false(), nullable=False))
    if missing_source_bank_id:
        op.create_index(op.f("ix_question_banks_source_bank_id"), "question_banks", ["source_bank_id"], unique=False)
    if missing_is_shared_copy:
        op.create_index(op.f("ix_question_banks_is_shared_copy"), "question_banks", ["is_shared_copy"], unique=False)


def downgrade() -> None:
    pass
