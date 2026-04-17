"""Add admin fields: branch is_active/paid_until, user phone/role

Revision ID: 0005_admin_fields
Revises: 0004_rating_range_1_5
Create Date: 2026-04-17 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_admin_fields"
down_revision: Union[str, None] = "0004_rating_range_1_5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("branches", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("branches", sa.Column("paid_until", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "role")
    op.drop_column("users", "phone")
    op.drop_column("branches", "paid_until")
    op.drop_column("branches", "is_active")
