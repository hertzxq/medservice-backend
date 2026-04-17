"""Relax rating constraints to allow rating=1 for reviews and complaints

Revision ID: 0004_rating_range_1_5
Revises: 0003_add_parsing_fields
Create Date: 2026-04-17 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0004_rating_range_1_5"
down_revision: Union[str, None] = "0003_add_parsing_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # reviews already has ck_reviews_rating_range with rating >= 1 AND <= 5;
    # rename it to the canonical name used elsewhere.
    op.drop_constraint("ck_reviews_rating_range", "reviews", type_="check")
    op.create_check_constraint(
        "ck_reviews_rating_allowed_values",
        "reviews",
        "rating BETWEEN 1 AND 5",
    )

    # complaints still has the old IN (2,3,4,5) constraint.
    op.drop_constraint("ck_complaints_rating_allowed_values", "complaints", type_="check")
    op.create_check_constraint(
        "ck_complaints_rating_allowed_values",
        "complaints",
        "rating BETWEEN 1 AND 5",
    )


def downgrade() -> None:
    op.drop_constraint("ck_complaints_rating_allowed_values", "complaints", type_="check")
    op.execute("UPDATE complaints SET rating = GREATEST(rating, 2)")
    op.create_check_constraint(
        "ck_complaints_rating_allowed_values",
        "complaints",
        "rating IN (2, 3, 4, 5)",
    )

    op.drop_constraint("ck_reviews_rating_allowed_values", "reviews", type_="check")
    op.execute("UPDATE reviews SET rating = GREATEST(rating, 2)")
    op.create_check_constraint(
        "ck_reviews_rating_range",
        "reviews",
        "rating >= 1 AND rating <= 5",
    )
