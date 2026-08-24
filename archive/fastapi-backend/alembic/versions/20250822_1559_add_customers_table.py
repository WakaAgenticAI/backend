"""add customers table

Revision ID: 20250822_1559_add_customers
Revises: 677a6b8f90ea
Create Date: 2025-08-22 15:59:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250822_1559_add_customers"
down_revision = "677a6b8f90ea"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("customers"):
        op.create_table(
            "customers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=64), nullable=True),
            sa.Column("segment", sa.String(length=32), nullable=False, server_default="regular"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("location", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_customers_id", "customers", ["id"], unique=False)
        op.create_index("ix_customers_email", "customers", ["email"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_idx = {idx["name"] for idx in inspector.get_indexes("customers")} if inspector.has_table("customers") else set()
    if "ix_customers_email" in existing_idx:
        op.drop_index("ix_customers_email", table_name="customers")
    if "ix_customers_id" in existing_idx:
        op.drop_index("ix_customers_id", table_name="customers")
    if inspector.has_table("customers"):
        op.drop_table("customers")
