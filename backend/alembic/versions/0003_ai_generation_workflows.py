"""ai generation workflows

Revision ID: 0003_ai_generation_workflows
Revises: 0002_question_bank_tags
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0003_ai_generation_workflows"
down_revision = "0002_question_bank_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("ai_generation_workflows"):
        op.create_table(
            "ai_generation_workflows",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("bank_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=True),
            sa.Column("purpose", sa.String(length=32), nullable=False),
            sa.Column("generation_mode", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("source_file_name", sa.String(length=255), nullable=True),
            sa.Column("source_text_snapshot", sa.Text(), nullable=True),
            sa.Column("requested_count", sa.Integer(), nullable=True),
            sa.Column("generate_description", sa.String(length=8), nullable=False),
            sa.Column("extra_instruction", sa.Text(), nullable=True),
            sa.Column("ai_provider_config_id", sa.Integer(), nullable=True),
            sa.Column("ai_model_snapshot", sa.String(length=128), nullable=True),
            sa.Column("ai_base_url_snapshot", sa.String(length=512), nullable=True),
            sa.Column("repair_attempts", sa.Integer(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["ai_provider_config_id"], ["user_ai_provider_configs.id"]),
            sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"]),
            sa.ForeignKeyConstraint(["job_id"], ["import_jobs.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ai_generation_workflows_bank_id"), "ai_generation_workflows", ["bank_id"], unique=False)
        op.create_index(op.f("ix_ai_generation_workflows_job_id"), "ai_generation_workflows", ["job_id"], unique=False)
        op.create_index(op.f("ix_ai_generation_workflows_purpose"), "ai_generation_workflows", ["purpose"], unique=False)
        op.create_index(op.f("ix_ai_generation_workflows_status"), "ai_generation_workflows", ["status"], unique=False)
        op.create_index(op.f("ix_ai_generation_workflows_user_id"), "ai_generation_workflows", ["user_id"], unique=False)

    if not inspector.has_table("ai_generation_workflow_steps"):
        op.create_table(
        "ai_generation_workflow_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["ai_generation_workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ai_generation_workflow_steps_step_name"), "ai_generation_workflow_steps", ["step_name"], unique=False)
        op.create_index(op.f("ix_ai_generation_workflow_steps_status"), "ai_generation_workflow_steps", ["status"], unique=False)
        op.create_index(op.f("ix_ai_generation_workflow_steps_workflow_id"), "ai_generation_workflow_steps", ["workflow_id"], unique=False)

    if not inspector.has_table("ai_generation_drafts"):
        op.create_table(
        "ai_generation_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_description", sa.Text(), nullable=True),
        sa.Column("raw_payload_json", sa.Text(), nullable=True),
        sa.Column("repaired_payload_json", sa.Text(), nullable=True),
        sa.Column("validation_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["import_jobs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["ai_generation_workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ai_generation_drafts_bank_id"), "ai_generation_drafts", ["bank_id"], unique=False)
        op.create_index(op.f("ix_ai_generation_drafts_job_id"), "ai_generation_drafts", ["job_id"], unique=False)
        op.create_index(op.f("ix_ai_generation_drafts_status"), "ai_generation_drafts", ["status"], unique=False)
        op.create_index(op.f("ix_ai_generation_drafts_user_id"), "ai_generation_drafts", ["user_id"], unique=False)
        op.create_index(op.f("ix_ai_generation_drafts_workflow_id"), "ai_generation_drafts", ["workflow_id"], unique=False)

    if not inspector.has_table("ai_generation_draft_questions"):
        op.create_table(
        "ai_generation_draft_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=32), nullable=True),
        sa.Column("options_json", sa.Text(), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("validation_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["ai_generation_drafts.id"]),
        sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ai_generation_draft_questions_draft_id"), "ai_generation_draft_questions", ["draft_id"], unique=False)

    import_job_columns = {column["name"] for column in inspector.get_columns("import_jobs")}
    if "workflow_id" not in import_job_columns:
        op.add_column("import_jobs", sa.Column("workflow_id", sa.Integer(), nullable=True))
        op.create_index(op.f("ix_import_jobs_workflow_id"), "import_jobs", ["workflow_id"], unique=False)
        if bind.dialect.name != "sqlite":
            op.create_foreign_key("fk_import_jobs_workflow_id", "import_jobs", "ai_generation_workflows", ["workflow_id"], ["id"])


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_import_jobs_workflow_id", "import_jobs", type_="foreignkey")
    op.drop_index(op.f("ix_import_jobs_workflow_id"), table_name="import_jobs")
    op.drop_column("import_jobs", "workflow_id")
    op.drop_index(op.f("ix_ai_generation_draft_questions_draft_id"), table_name="ai_generation_draft_questions")
    op.drop_table("ai_generation_draft_questions")
    op.drop_index(op.f("ix_ai_generation_drafts_workflow_id"), table_name="ai_generation_drafts")
    op.drop_index(op.f("ix_ai_generation_drafts_user_id"), table_name="ai_generation_drafts")
    op.drop_index(op.f("ix_ai_generation_drafts_status"), table_name="ai_generation_drafts")
    op.drop_index(op.f("ix_ai_generation_drafts_job_id"), table_name="ai_generation_drafts")
    op.drop_index(op.f("ix_ai_generation_drafts_bank_id"), table_name="ai_generation_drafts")
    op.drop_table("ai_generation_drafts")
    op.drop_index(op.f("ix_ai_generation_workflow_steps_workflow_id"), table_name="ai_generation_workflow_steps")
    op.drop_index(op.f("ix_ai_generation_workflow_steps_status"), table_name="ai_generation_workflow_steps")
    op.drop_index(op.f("ix_ai_generation_workflow_steps_step_name"), table_name="ai_generation_workflow_steps")
    op.drop_table("ai_generation_workflow_steps")
    op.drop_index(op.f("ix_ai_generation_workflows_user_id"), table_name="ai_generation_workflows")
    op.drop_index(op.f("ix_ai_generation_workflows_status"), table_name="ai_generation_workflows")
    op.drop_index(op.f("ix_ai_generation_workflows_purpose"), table_name="ai_generation_workflows")
    op.drop_index(op.f("ix_ai_generation_workflows_job_id"), table_name="ai_generation_workflows")
    op.drop_index(op.f("ix_ai_generation_workflows_bank_id"), table_name="ai_generation_workflows")
    op.drop_table("ai_generation_workflows")
