"""Add patient rating column to requests

Revision ID: 0009_add_request_rating
Revises: 0008_add_review_verification
Create Date: 2026-06-06

Stores the rating the patient submits in POST /public/requests/{token}/rating so
the real 1..5 score survives to the complaint path instead of being hardcoded to 2.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_add_request_rating"
down_revision: Union[str, None] = "0008_add_review_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("requests", sa.Column("rating", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("requests", "rating")
