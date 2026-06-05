"""Initial tables

Revision ID: 0001
Revises:
Create Date: 2026-06-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pii_person
    op.create_table(
        "pii_person",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("person_key", sa.String(36), index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(254)),
        sa.Column("phone", sa.String(20)),
        sa.Column("identification_code", sa.String(30)),
        sa.Column("identification_type", sa.String(20)),
        sa.Column("date_of_birth", sa.Date()),
        sa.Column("address_json", sa.JSON()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("purge_after", sa.Date()),
    )

    # pii_questionnaire_answer
    op.create_table(
        "pii_questionnaire_answer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_key", sa.String(36), nullable=False, index=True),
        sa.Column("question_key", sa.String(36), nullable=False),
        sa.Column("question_text", sa.String(500)),
        sa.Column("answer_body", sa.Text(), nullable=False),
        sa.Column("pseudonymized_body", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # proxy_token (created before audit_log due to FK)
    op.create_table(
        "proxy_token",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("scopes", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
    )

    # audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255)),
        sa.Column("external_id", sa.String(255)),
        sa.Column("client_ip", sa.String(45)),
        sa.Column("token_id", sa.Integer(), sa.ForeignKey("proxy_token.id")),
        sa.Column("request_method", sa.String(10)),
        sa.Column("request_path", sa.String(500)),
        sa.Column("pii_fields_accessed", sa.JSON()),
        sa.Column("details", sa.JSON()),
    )

    # notification_log
    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False, index=True),
        sa.Column("appointment_key", sa.String(36)),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient", sa.String(254), nullable=False),
        sa.Column("subject", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_detail", sa.Text()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notification_log")
    op.drop_table("audit_log")
    op.drop_table("proxy_token")
    op.drop_table("pii_questionnaire_answer")
    op.drop_table("pii_person")
