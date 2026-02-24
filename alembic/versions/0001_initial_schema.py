"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-02-18 20:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


platform_enum = sa.Enum(
    "YANDEX_MAPS",
    "GOOGLE_MAPS",
    "TWO_GIS",
    "PRODOCTOROV",
    "NAPOPRAVKU",
    "OTHER",
    name="platformenum",
)

request_status_enum = sa.Enum(
    "SENT",
    "OPENED",
    "RATED",
    "VISITED",
    "PUBLISHED",
    "COMPLAINT",
    name="requeststatusenum",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("avg_rating", sa.Float(), nullable=True, server_default=sa.text("0")),
        sa.Column("nps_score", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_branches_id"), "branches", ["id"], unique=False)

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_name", sa.String(), nullable=True),
        sa.Column("reviewer_phone", sa.String(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("text", sa.String(), nullable=True),
        sa.Column("platform", platform_enum, nullable=False),
        sa.Column("external_url", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reviews_id"), "reviews", ["id"], unique=False)
    op.create_index(op.f("ix_reviews_branch_id"), "reviews", ["branch_id"], unique=False)

    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("client_name", sa.String(), nullable=True),
        sa.Column("client_phone", sa.String(), nullable=True),
        sa.Column("client_email", sa.String(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("intercepted", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("resolved", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_complaints_id"), "complaints", ["id"], unique=False)
    op.create_index(op.f("ix_complaints_branch_id"), "complaints", ["branch_id"], unique=False)

    op.create_table(
        "requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("client_name", sa.String(), nullable=False),
        sa.Column("client_phone", sa.String(), nullable=False),
        sa.Column("client_email", sa.String(), nullable=True),
        sa.Column("status", request_status_enum, nullable=False, server_default=sa.text("'SENT'::requeststatusenum")),
        sa.Column("request_link", sa.String(), nullable=True),
        sa.Column("review_id", sa.Integer(), nullable=True),
        sa.Column("complaint_id", sa.Integer(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requests_id"), "requests", ["id"], unique=False)
    op.create_index(op.f("ix_requests_branch_id"), "requests", ["branch_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_requests_branch_id"), table_name="requests")
    op.drop_index(op.f("ix_requests_id"), table_name="requests")
    op.drop_table("requests")

    op.drop_index(op.f("ix_complaints_branch_id"), table_name="complaints")
    op.drop_index(op.f("ix_complaints_id"), table_name="complaints")
    op.drop_table("complaints")

    op.drop_index(op.f("ix_reviews_branch_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_id"), table_name="reviews")
    op.drop_table("reviews")

    op.drop_index(op.f("ix_branches_id"), table_name="branches")
    op.drop_table("branches")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    request_status_enum.drop(bind, checkfirst=True)
    platform_enum.drop(bind, checkfirst=True)
