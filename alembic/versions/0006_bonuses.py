"""Add bonuses tables and branch branding fields.

Revision ID: 0006_bonuses
Revises: 0005_admin_fields
Create Date: 2026-05-20 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_bonuses"
down_revision: Union[str, None] = "0005_admin_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("branches", sa.Column("public_name", sa.String(), nullable=True))
    op.add_column("branches", sa.Column("public_city", sa.String(), nullable=True))
    op.add_column("branches", sa.Column("logo_url", sa.Text(), nullable=True))

    op.create_table(
        "branch_bonuses",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "branch_id",
            sa.Integer(),
            sa.ForeignKey("branches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index(
        "ix_branch_bonuses_branch_published",
        "branch_bonuses",
        ["branch_id", "is_published"],
    )

    op.create_table(
        "bonus_categories",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    op.create_table(
        "admin_bonuses",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("bonus_categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index(
        "ix_admin_bonuses_category_published",
        "admin_bonuses",
        ["category_id", "is_published"],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_bonuses_category_published", table_name="admin_bonuses")
    op.drop_table("admin_bonuses")
    op.drop_table("bonus_categories")
    op.drop_index("ix_branch_bonuses_branch_published", table_name="branch_bonuses")
    op.drop_table("branch_bonuses")
    op.drop_column("branches", "logo_url")
    op.drop_column("branches", "public_city")
    op.drop_column("branches", "public_name")
