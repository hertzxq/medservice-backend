"""Add user_branches association (multi-tenant access control)

Revision ID: 0010_add_user_branches
Revises: 0009_add_request_rating
Create Date: 2026-06-11

Introduces per-user branch access. Non-superusers may only read/operate on
branches assigned to them via this table; superusers ignore it. Closes the
flat-authorization (BOLA) hole where any authenticated user could access any
branch by id.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_add_user_branches"
down_revision: Union[str, None] = "0009_add_request_rating"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_branches",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "branch_id"),
    )


def downgrade() -> None:
    op.drop_table("user_branches")
