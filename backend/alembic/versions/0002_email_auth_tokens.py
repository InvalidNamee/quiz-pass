"""email verification and password reset tokens

Revision ID: 0002_email_auth_tokens
Revises: 0001_initial
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_email_auth_tokens"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE users SET email_verified_at = CURRENT_TIMESTAMP WHERE email_verified_at IS NULL")
    op.create_table(
        "email_auth_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_email_auth_tokens_id"), "email_auth_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_email_auth_tokens_user_id"), "email_auth_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix_email_auth_tokens_email"), "email_auth_tokens", ["email"], unique=False)
    op.create_index(op.f("ix_email_auth_tokens_purpose"), "email_auth_tokens", ["purpose"], unique=False)
    op.create_index(op.f("ix_email_auth_tokens_token_hash"), "email_auth_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_email_auth_tokens_expires_at"), "email_auth_tokens", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_auth_tokens_expires_at"), table_name="email_auth_tokens")
    op.drop_index(op.f("ix_email_auth_tokens_token_hash"), table_name="email_auth_tokens")
    op.drop_index(op.f("ix_email_auth_tokens_purpose"), table_name="email_auth_tokens")
    op.drop_index(op.f("ix_email_auth_tokens_email"), table_name="email_auth_tokens")
    op.drop_index(op.f("ix_email_auth_tokens_user_id"), table_name="email_auth_tokens")
    op.drop_index(op.f("ix_email_auth_tokens_id"), table_name="email_auth_tokens")
    op.drop_table("email_auth_tokens")
    op.drop_column("users", "email_verified_at")
