"""add ai workflow cancel retry context fields

Revision ID: 0004_ai_workflow_ctx
Revises: 0003_ai_response_format_type
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_ai_workflow_ctx"
down_revision = "0003_ai_response_format_type"
branch_labels = None
depends_on = None


def _find_fk(inspector, table_name: str, column_name: str, referred_table: str):
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get("constrained_columns") == [column_name] and fk.get("referred_table") == referred_table:
            return fk
    return None


def _fk_ondelete(fk) -> str | None:
    options = fk.get("options") or {}
    ondelete = options.get("ondelete")
    return ondelete.upper() if isinstance(ondelete, str) else ondelete


def _ensure_mysql_set_null_fk(table_name: str, column_name: str, referred_table: str, referred_column: str, constraint_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    fk = _find_fk(inspector, table_name, column_name, referred_table)
    if fk and _fk_ondelete(fk) == "SET NULL":
        return
    if fk and fk.get("name"):
        op.drop_constraint(fk["name"], table_name, type_="foreignkey")
    op.alter_column(table_name, column_name, existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        constraint_name,
        table_name,
        referred_table,
        [column_name],
        [referred_column],
        ondelete="SET NULL",
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    bank_columns = {column["name"] for column in inspector.get_columns("question_banks")}
    workflow_columns = {column["name"] for column in inspector.get_columns("ai_generation_workflows")}
    workflow_indexes = {index["name"] for index in inspector.get_indexes("ai_generation_workflows")}

    if "ai_context" not in bank_columns:
        op.add_column("question_banks", sa.Column("ai_context", sa.Text(), nullable=True))
    if "bank_title_snapshot" not in workflow_columns:
        op.add_column("ai_generation_workflows", sa.Column("bank_title_snapshot", sa.String(length=255), nullable=True))
    if "inherit_context" not in workflow_columns:
        op.add_column("ai_generation_workflows", sa.Column("inherit_context", sa.Boolean(), server_default=sa.false(), nullable=False))
    created_retry_column = "retry_of_workflow_id" not in workflow_columns
    if created_retry_column:
        op.add_column("ai_generation_workflows", sa.Column("retry_of_workflow_id", sa.Integer(), nullable=True))
    if "cancel_reason" not in workflow_columns:
        op.add_column("ai_generation_workflows", sa.Column("cancel_reason", sa.Text(), nullable=True))
    if "ix_ai_generation_workflows_retry_of_workflow_id" not in workflow_indexes:
        op.create_index(op.f("ix_ai_generation_workflows_retry_of_workflow_id"), "ai_generation_workflows", ["retry_of_workflow_id"], unique=False)

    retry_fk = _find_fk(inspector, "ai_generation_workflows", "retry_of_workflow_id", "ai_generation_workflows")
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("ai_generation_workflows") as batch_op:
            batch_op.alter_column("bank_id", existing_type=sa.Integer(), nullable=True)
            if not retry_fk:
                batch_op.create_foreign_key(
                    "fk_ai_generation_workflows_retry_of_workflow_id",
                    "ai_generation_workflows",
                    ["retry_of_workflow_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
    else:
        _ensure_mysql_set_null_fk(
            "ai_generation_workflows",
            "bank_id",
            "question_banks",
            "id",
            "fk_ai_generation_workflows_bank_id_question_banks",
        )
        _ensure_mysql_set_null_fk(
            "import_jobs",
            "bank_id",
            "question_banks",
            "id",
            "fk_import_jobs_bank_id_question_banks",
        )
        inspector = sa.inspect(bind)
        retry_fk = _find_fk(inspector, "ai_generation_workflows", "retry_of_workflow_id", "ai_generation_workflows")
        if not retry_fk:
            op.create_foreign_key(
                "fk_ai_generation_workflows_retry_of_workflow_id",
                "ai_generation_workflows",
                "ai_generation_workflows",
                ["retry_of_workflow_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    # Current development migrations intentionally keep the clean schema in
    # 0001. This compatibility migration may be a no-op on fresh databases, so
    # downgrading it should not remove columns that belong to the baseline.
    pass
