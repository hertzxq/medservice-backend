"""Add branch logo_url column

Revision ID: 0011_add_branch_logo
Revises: 0010_add_user_branches
Create Date: 2026-06-13

Per-branch patient-facing logo, shown on the mini branch tile. Stored inline as
a base64 data URL (PNG ≤150 KB) — there is no separate object store. Nullable;
branches without a logo fall back to the first-letter avatar in the mini.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_add_branch_logo"
down_revision: Union[str, None] = "0010_add_user_branches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("branches", sa.Column("logo_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("branches", "logo_url")
