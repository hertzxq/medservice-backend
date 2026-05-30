"""add public_token to requests (patient mini-app review flow, H4)

Revision ID: 0008_request_public_token
Revises: 0007_promo_and_faq
Create Date: 2026-05-29

"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_request_public_token"
down_revision: Union[str, None] = "0007_promo_and_faq"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # 1) add as nullable so existing rows are accepted
    op.add_column("requests", sa.Column("public_token", sa.String(), nullable=True))

    # 2) backfill existing rows with a unique token each
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM requests WHERE public_token IS NULL")).fetchall()
    for (row_id,) in rows:
        conn.execute(
            sa.text("UPDATE requests SET public_token = :tok WHERE id = :id"),
            {"tok": uuid.uuid4().hex, "id": row_id},
        )

    # 3) enforce NOT NULL + unique index now that every row has a value
    op.alter_column("requests", "public_token", existing_type=sa.String(), nullable=False)
    op.create_index(
        "ix_requests_public_token", "requests", ["public_token"], unique=True
    )

    # patient's submitted rating (nullable; set when they rate via the mini-app)
    op.add_column("requests", sa.Column("rating", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("requests", "rating")
    op.drop_index("ix_requests_public_token", table_name="requests")
    op.drop_column("requests", "public_token")
