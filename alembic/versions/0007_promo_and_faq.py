"""Add promo_code, website_url, and faq_items.

Revision ID: 0007_promo_and_faq
Revises: 0006_bonuses
Create Date: 2026-05-20 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007_promo_and_faq"
down_revision: Union[str, None] = "0006_bonuses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("branches", sa.Column("website_url", sa.String(), nullable=True))
    op.add_column("branch_bonuses", sa.Column("promo_code", sa.String(), nullable=True))
    op.add_column("admin_bonuses", sa.Column("promo_code", sa.String(), nullable=True))
    op.add_column("admin_bonuses", sa.Column("website_url", sa.String(), nullable=True))

    op.create_table(
        "faq_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("faq_items")
    op.drop_column("admin_bonuses", "website_url")
    op.drop_column("admin_bonuses", "promo_code")
    op.drop_column("branch_bonuses", "promo_code")
    op.drop_column("branches", "website_url")
