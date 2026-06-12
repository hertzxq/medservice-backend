"""Add review-verification (publish-claim) fields to requests

Revision ID: 0008_add_review_verification
Revises: 0007_add_bonus_catalog
Create Date: 2026-06-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_add_review_verification"
down_revision: Union[str, None] = "0007_add_bonus_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("requests", sa.Column("claimed_platform", sa.String(), nullable=True))
    op.add_column("requests", sa.Column("review_claim_name", sa.String(), nullable=True))
    op.add_column("requests", sa.Column("review_claim_text", sa.String(), nullable=True))
    op.add_column("requests", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("requests", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("requests", sa.Column("verification_status", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("requests", "verification_status")
    op.drop_column("requests", "verified_at")
    op.drop_column("requests", "claimed_at")
    op.drop_column("requests", "review_claim_text")
    op.drop_column("requests", "review_claim_name")
    op.drop_column("requests", "claimed_platform")
