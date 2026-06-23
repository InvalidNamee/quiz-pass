"""add offline practice sync fields

Revision ID: 0011_offline_practice_sync
Revises: 0010_mistake_attempts
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_offline_practice_sync"
down_revision = "0010_mistake_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("practice_sessions") as batch_op:
        batch_op.add_column(sa.Column("offline_device_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("offline_client_session_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("offline_synced_at", sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f("ix_practice_sessions_offline_device_id"), ["offline_device_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_practice_sessions_offline_client_session_id"), ["offline_client_session_id"], unique=False)
        batch_op.create_unique_constraint(
            "uq_practice_session_offline_client",
            ["user_id", "offline_device_id", "offline_client_session_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("practice_sessions") as batch_op:
        batch_op.drop_constraint("uq_practice_session_offline_client", type_="unique")
        batch_op.drop_index(batch_op.f("ix_practice_sessions_offline_client_session_id"))
        batch_op.drop_index(batch_op.f("ix_practice_sessions_offline_device_id"))
        batch_op.drop_column("offline_synced_at")
        batch_op.drop_column("offline_client_session_id")
        batch_op.drop_column("offline_device_id")
