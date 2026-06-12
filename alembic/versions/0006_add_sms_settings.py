"""Add per-branch SMS settings

Revision ID: 0006_add_sms_settings
Revises: 0005_admin_fields
Create Date: 2026-06-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_add_sms_settings"
down_revision: Union[str, None] = "0005_admin_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TEMPLATE = "Здравствуйте! Будем благодарны за отзыв о визите. Ссылка: {link}"


def upgrade() -> None:
    op.add_column(
        "branches",
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "branches",
        sa.Column("sms_template", sa.String(), nullable=True, server_default=DEFAULT_TEMPLATE),
    )
    op.add_column(
        "branches",
        sa.Column("sms_monthly_limit", sa.Integer(), nullable=True, server_default="150"),
    )


def downgrade() -> None:
    op.drop_column("branches", "sms_monthly_limit")
    op.drop_column("branches", "sms_template")
    op.drop_column("branches", "sms_enabled")
