"""Restrict ratings to integer values in range 2..5

Revision ID: 0002_rating_int_2_5
Revises: 0001_initial_schema
Create Date: 2026-02-24 01:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_rating_int_2_5"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Normalize existing values before adding strict constraints.
    op.execute("UPDATE reviews SET rating = LEAST(5, GREATEST(2, ROUND(rating)::int))")
    op.execute("UPDATE complaints SET rating = LEAST(5, GREATEST(2, ROUND(rating)::int))")

    op.alter_column(
        "reviews",
        "rating",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="LEAST(5, GREATEST(2, ROUND(rating)::int))",
    )
    op.alter_column(
        "complaints",
        "rating",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="LEAST(5, GREATEST(2, ROUND(rating)::int))",
    )

    op.create_check_constraint(
        "ck_reviews_rating_allowed_values",
        "reviews",
        "rating IN (2, 3, 4, 5)",
    )
    op.create_check_constraint(
        "ck_complaints_rating_allowed_values",
        "complaints",
        "rating IN (2, 3, 4, 5)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_complaints_rating_allowed_values", "complaints", type_="check")
    op.drop_constraint("ck_reviews_rating_allowed_values", "reviews", type_="check")

    op.alter_column(
        "complaints",
        "rating",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using="rating::double precision",
    )
    op.alter_column(
        "reviews",
        "rating",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using="rating::double precision",
    )
