"""add workflow queue fields and audit events

Revision ID: 0007_queue_audit
Revises: 0006_existing_q_ctx
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_queue_audit"
down_revision = "0006_existing_q_ctx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    import_job_columns = {column["name"] for column in sa.inspect(bind).get_columns("import_jobs")}
    if "queue_job_id" not in import_job_columns:
        op.add_column("import_jobs", sa.Column("queue_job_id", sa.String(length=128), nullable=True))
    if "enqueued_at" not in import_job_columns:
        op.add_column("import_jobs", sa.Column("enqueued_at", sa.DateTime(), nullable=True))

    if not sa.inspect(bind).has_table("audit_events"):
        op.create_table(
            "audit_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("target_type", sa.String(length=64), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_audit_events_actor_user_id"), "audit_events", ["actor_user_id"], unique=False)
        op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False)
        op.create_index(op.f("ix_audit_events_target_type"), "audit_events", ["target_type"], unique=False)
        op.create_index(op.f("ix_audit_events_target_id"), "audit_events", ["target_id"], unique=False)


def downgrade() -> None:
    pass
