"""add ai response format type

Revision ID: 0003_ai_response_format_type
Revises: 0002_email_auth_tokens
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_ai_response_format_type"
down_revision = "0002_email_auth_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_ai_provider_configs",
        sa.Column("response_format_type", sa.String(length=32), server_default="json_object", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_ai_provider_configs", "response_format_type")
