"""initial clean schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("avatar_source", sa.String(length=32), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "user_ai_provider_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("api_base_url", sa.String(length=512), nullable=False),
        sa.Column("api_key_encrypted", sa.String(length=2048), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_ai_provider_configs_user_id"), "user_ai_provider_configs", ["user_id"], unique=False)

    op.create_table(
        "user_prompt_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_prompt_templates_user_id"), "user_prompt_templates", ["user_id"], unique=False)

    op.create_table(
        "question_bank_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_bank_tags_name"), "question_bank_tags", ["name"], unique=True)

    op.create_table(
        "question_banks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("desired_visibility", sa.String(length=32), nullable=False),
        sa.Column("generation_status", sa.String(length=32), nullable=False),
        sa.Column("ai_context", sa.Text(), nullable=True),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("favorite_count", sa.Integer(), nullable=False),
        sa.Column("ai_provider_config_id", sa.Integer(), nullable=True),
        sa.Column("ai_model_name", sa.String(length=128), nullable=True),
        sa.Column("ai_base_url_host", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ai_provider_config_id"], ["user_ai_provider_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_banks_generation_status"), "question_banks", ["generation_status"], unique=False)
    op.create_index(op.f("ix_question_banks_owner_id"), "question_banks", ["owner_id"], unique=False)
    op.create_index(op.f("ix_question_banks_title"), "question_banks", ["title"], unique=False)
    op.create_index(op.f("ix_question_banks_visibility"), "question_banks", ["visibility"], unique=False)

    op.create_table(
        "question_bank_tag_links",
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["question_bank_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("bank_id", "tag_id"),
        sa.UniqueConstraint("bank_id", "tag_id", name="uq_question_bank_tag_link"),
    )

    op.create_table(
        "question_bank_favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "bank_id", name="uq_question_bank_favorite"),
    )
    op.create_index(op.f("ix_question_bank_favorites_bank_id"), "question_bank_favorites", ["bank_id"], unique=False)
    op.create_index(op.f("ix_question_bank_favorites_user_id"), "question_bank_favorites", ["user_id"], unique=False)

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("generated_model", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_questions_bank_id"), "questions", ["bank_id"], unique=False)

    op.create_table(
        "question_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=8), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_options_question_id"), "question_options", ["question_id"], unique=False)

    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_practice_sessions_bank_id"), "practice_sessions", ["bank_id"], unique=False)
    op.create_index(op.f("ix_practice_sessions_user_id"), "practice_sessions", ["user_id"], unique=False)

    op.create_table(
        "practice_session_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["practice_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "question_id", name="uq_practice_session_question"),
    )
    op.create_index(op.f("ix_practice_session_questions_question_id"), "practice_session_questions", ["question_id"], unique=False)
    op.create_index(op.f("ix_practice_session_questions_session_id"), "practice_session_questions", ["session_id"], unique=False)

    op.create_table(
        "practice_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("selected_option_ids", sa.JSON(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("is_submitted", sa.Boolean(), nullable=False),
        sa.Column("answered_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["practice_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_practice_answers_question_id"), "practice_answers", ["question_id"], unique=False)
    op.create_index(op.f("ix_practice_answers_session_id"), "practice_answers", ["session_id"], unique=False)

    op.create_table(
        "mistake_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("last_wrong_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "bank_id", "question_id", name="uq_mistake_record"),
    )
    op.create_index(op.f("ix_mistake_records_bank_id"), "mistake_records", ["bank_id"], unique=False)
    op.create_index(op.f("ix_mistake_records_question_id"), "mistake_records", ["question_id"], unique=False)
    op.create_index(op.f("ix_mistake_records_user_id"), "mistake_records", ["user_id"], unique=False)

    op.create_table(
        "ai_generation_workflows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("generation_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_file_name", sa.String(length=255), nullable=True),
        sa.Column("source_text_snapshot", sa.Text(), nullable=True),
        sa.Column("bank_title_snapshot", sa.String(length=255), nullable=True),
        sa.Column("requested_count", sa.Integer(), nullable=True),
        sa.Column("generate_description", sa.String(length=8), nullable=False),
        sa.Column("extra_instruction", sa.Text(), nullable=True),
        sa.Column("inherit_context", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("include_existing_questions", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("retry_of_workflow_id", sa.Integer(), nullable=True),
        sa.Column("ai_provider_config_id", sa.Integer(), nullable=True),
        sa.Column("ai_model_snapshot", sa.String(length=128), nullable=True),
        sa.Column("ai_base_url_snapshot", sa.String(length=512), nullable=True),
        sa.Column("repair_attempts", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ai_provider_config_id"], ["user_ai_provider_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["retry_of_workflow_id"], ["ai_generation_workflows.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_generation_workflows_bank_id"), "ai_generation_workflows", ["bank_id"], unique=False)
    op.create_index(op.f("ix_ai_generation_workflows_purpose"), "ai_generation_workflows", ["purpose"], unique=False)
    op.create_index(op.f("ix_ai_generation_workflows_retry_of_workflow_id"), "ai_generation_workflows", ["retry_of_workflow_id"], unique=False)
    op.create_index(op.f("ix_ai_generation_workflows_status"), "ai_generation_workflows", ["status"], unique=False)
    op.create_index(op.f("ix_ai_generation_workflows_user_id"), "ai_generation_workflows", ["user_id"], unique=False)

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
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["ai_generation_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_generation_workflow_steps_status"), "ai_generation_workflow_steps", ["status"], unique=False)
    op.create_index(op.f("ix_ai_generation_workflow_steps_step_name"), "ai_generation_workflow_steps", ["step_name"], unique=False)
    op.create_index(op.f("ix_ai_generation_workflow_steps_workflow_id"), "ai_generation_workflow_steps", ["workflow_id"], unique=False)

    op.create_table(
        "ai_generation_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_description", sa.Text(), nullable=True),
        sa.Column("raw_payload_json", sa.Text(), nullable=True),
        sa.Column("repaired_payload_json", sa.Text(), nullable=True),
        sa.Column("validation_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["ai_generation_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_generation_drafts_bank_id"), "ai_generation_drafts", ["bank_id"], unique=False)
    op.create_index(op.f("ix_ai_generation_drafts_status"), "ai_generation_drafts", ["status"], unique=False)
    op.create_index(op.f("ix_ai_generation_drafts_user_id"), "ai_generation_drafts", ["user_id"], unique=False)
    op.create_index(op.f("ix_ai_generation_drafts_workflow_id"), "ai_generation_drafts", ["workflow_id"], unique=False)

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
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["ai_generation_drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_generation_draft_questions_draft_id"), "ai_generation_draft_questions", ["draft_id"], unique=False)

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=True),
        sa.Column("workflow_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("desired_visibility", sa.String(length=32), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("ai_provider_config_id", sa.Integer(), nullable=True),
        sa.Column("ai_base_url_snapshot", sa.String(length=512), nullable=True),
        sa.Column("ai_model_snapshot", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ai_provider_config_id"], ["user_ai_provider_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["ai_generation_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_import_jobs_bank_id"), "import_jobs", ["bank_id"], unique=False)
    op.create_index(op.f("ix_import_jobs_status"), "import_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_import_jobs_user_id"), "import_jobs", ["user_id"], unique=False)
    op.create_index(op.f("ix_import_jobs_workflow_id"), "import_jobs", ["workflow_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_import_jobs_workflow_id"), table_name="import_jobs")
    op.drop_index(op.f("ix_import_jobs_user_id"), table_name="import_jobs")
    op.drop_index(op.f("ix_import_jobs_status"), table_name="import_jobs")
    op.drop_index(op.f("ix_import_jobs_bank_id"), table_name="import_jobs")
    op.drop_table("import_jobs")
    op.drop_index(op.f("ix_ai_generation_draft_questions_draft_id"), table_name="ai_generation_draft_questions")
    op.drop_table("ai_generation_draft_questions")
    op.drop_index(op.f("ix_ai_generation_drafts_workflow_id"), table_name="ai_generation_drafts")
    op.drop_index(op.f("ix_ai_generation_drafts_user_id"), table_name="ai_generation_drafts")
    op.drop_index(op.f("ix_ai_generation_drafts_status"), table_name="ai_generation_drafts")
    op.drop_index(op.f("ix_ai_generation_drafts_bank_id"), table_name="ai_generation_drafts")
    op.drop_table("ai_generation_drafts")
    op.drop_index(op.f("ix_ai_generation_workflow_steps_workflow_id"), table_name="ai_generation_workflow_steps")
    op.drop_index(op.f("ix_ai_generation_workflow_steps_step_name"), table_name="ai_generation_workflow_steps")
    op.drop_index(op.f("ix_ai_generation_workflow_steps_status"), table_name="ai_generation_workflow_steps")
    op.drop_table("ai_generation_workflow_steps")
    op.drop_index(op.f("ix_ai_generation_workflows_user_id"), table_name="ai_generation_workflows")
    op.drop_index(op.f("ix_ai_generation_workflows_status"), table_name="ai_generation_workflows")
    op.drop_index(op.f("ix_ai_generation_workflows_retry_of_workflow_id"), table_name="ai_generation_workflows")
    op.drop_index(op.f("ix_ai_generation_workflows_purpose"), table_name="ai_generation_workflows")
    op.drop_index(op.f("ix_ai_generation_workflows_bank_id"), table_name="ai_generation_workflows")
    op.drop_table("ai_generation_workflows")
    op.drop_index(op.f("ix_mistake_records_user_id"), table_name="mistake_records")
    op.drop_index(op.f("ix_mistake_records_question_id"), table_name="mistake_records")
    op.drop_index(op.f("ix_mistake_records_bank_id"), table_name="mistake_records")
    op.drop_table("mistake_records")
    op.drop_index(op.f("ix_practice_answers_session_id"), table_name="practice_answers")
    op.drop_index(op.f("ix_practice_answers_question_id"), table_name="practice_answers")
    op.drop_table("practice_answers")
    op.drop_index(op.f("ix_practice_session_questions_session_id"), table_name="practice_session_questions")
    op.drop_index(op.f("ix_practice_session_questions_question_id"), table_name="practice_session_questions")
    op.drop_table("practice_session_questions")
    op.drop_index(op.f("ix_practice_sessions_user_id"), table_name="practice_sessions")
    op.drop_index(op.f("ix_practice_sessions_bank_id"), table_name="practice_sessions")
    op.drop_table("practice_sessions")
    op.drop_index(op.f("ix_question_options_question_id"), table_name="question_options")
    op.drop_table("question_options")
    op.drop_index(op.f("ix_questions_bank_id"), table_name="questions")
    op.drop_table("questions")
    op.drop_index(op.f("ix_question_bank_favorites_user_id"), table_name="question_bank_favorites")
    op.drop_index(op.f("ix_question_bank_favorites_bank_id"), table_name="question_bank_favorites")
    op.drop_table("question_bank_favorites")
    op.drop_table("question_bank_tag_links")
    op.drop_index(op.f("ix_question_banks_visibility"), table_name="question_banks")
    op.drop_index(op.f("ix_question_banks_title"), table_name="question_banks")
    op.drop_index(op.f("ix_question_banks_owner_id"), table_name="question_banks")
    op.drop_index(op.f("ix_question_banks_generation_status"), table_name="question_banks")
    op.drop_table("question_banks")
    op.drop_index(op.f("ix_question_bank_tags_name"), table_name="question_bank_tags")
    op.drop_table("question_bank_tags")
    op.drop_index(op.f("ix_user_prompt_templates_user_id"), table_name="user_prompt_templates")
    op.drop_table("user_prompt_templates")
    op.drop_index(op.f("ix_user_ai_provider_configs_user_id"), table_name="user_ai_provider_configs")
    op.drop_table("user_ai_provider_configs")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
