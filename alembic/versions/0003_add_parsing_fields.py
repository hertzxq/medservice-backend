"""Add parsing support fields

- branches.platform_urls (JSON) — stores platform URLs per branch
- reviews.response_text (VARCHAR) — organization reply from parsed reviews
- Widen reviews.rating constraint from (2,3,4,5) to 1..5

Revision ID: 0003_add_parsing_fields
Revises: 55b9ff315408
Create Date: 2026-04-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_add_parsing_fields"
down_revision: Union[str, Sequence[str], None] = "55b9ff315408"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- branches: platform_urls
    op.add_column("branches", sa.Column("platform_urls", sa.JSON(), nullable=True, server_default="{}"))

    # -- reviews: response_text
    op.add_column("reviews", sa.Column("response_text", sa.String(), nullable=True))

    # -- reviews: widen rating constraint from IN (2,3,4,5) → BETWEEN 1 AND 5
    # Drop the old constraint (name from migration 0002)
    op.drop_constraint("ck_reviews_rating_allowed_values", "reviews", type_="check")
    op.create_check_constraint(
        "ck_reviews_rating_range",
        "reviews",
        "rating BETWEEN 1 AND 5",
    )


def downgrade() -> None:
    # Restore the old constraint
    op.drop_constraint("ck_reviews_rating_range", "reviews", type_="check")
    op.create_check_constraint(
        "ck_reviews_rating_allowed_values",
        "reviews",
        "rating IN (2, 3, 4, 5)",
    )

    op.drop_column("reviews", "response_text")
    op.drop_column("branches", "platform_urls")
