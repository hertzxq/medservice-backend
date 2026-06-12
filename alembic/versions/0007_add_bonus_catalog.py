"""Add bonus catalog tables (branch bonuses, partner categories/bonuses, FAQ)

Revision ID: 0007_add_bonus_catalog
Revises: 0006_add_sms_settings
Create Date: 2026-06-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_add_bonus_catalog"
down_revision: Union[str, None] = "0006_add_sms_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clinic's own per-branch offers
    op.create_table(
        "branch_bonuses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("discount_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("promo_code", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_branch_bonuses_id", "branch_bonuses", ["id"])
    op.create_index("ix_branch_bonuses_branch_id", "branch_bonuses", ["branch_id"])

    # Global partner categories
    op.create_table(
        "bonus_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bonus_categories_id", "bonus_categories", ["id"])

    # Global partner offers inside a category
    op.create_table(
        "partner_bonuses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=False, server_default=""),
        sa.Column("discount_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("promo_code", sa.String(), nullable=True),
        sa.Column("website_url", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["bonus_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_partner_bonuses_id", "partner_bonuses", ["id"])
    op.create_index("ix_partner_bonuses_category_id", "partner_bonuses", ["category_id"])

    # Global FAQ
    op.create_table(
        "faq_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faq_items_id", "faq_items", ["id"])


def downgrade() -> None:
    op.drop_index("ix_faq_items_id", table_name="faq_items")
    op.drop_table("faq_items")
    op.drop_index("ix_partner_bonuses_category_id", table_name="partner_bonuses")
    op.drop_index("ix_partner_bonuses_id", table_name="partner_bonuses")
    op.drop_table("partner_bonuses")
    op.drop_index("ix_bonus_categories_id", table_name="bonus_categories")
    op.drop_table("bonus_categories")
    op.drop_index("ix_branch_bonuses_branch_id", table_name="branch_bonuses")
    op.drop_index("ix_branch_bonuses_id", table_name="branch_bonuses")
    op.drop_table("branch_bonuses")
