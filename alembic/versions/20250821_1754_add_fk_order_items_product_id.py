"""add FK order_items.product_id -> products.id

Revision ID: a1c9e5d2f7ab
Revises: 8b2d4c9e7f10
Create Date: 2025-08-21 17:54:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1c9e5d2f7ab"
down_revision = "8b2d4c9e7f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ensure index exists for product_id
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"], unique=False)
    # add FK constraint (if not already exists)
    op.create_foreign_key(
        "fk_order_items_product_id_products",
        source_table="order_items",
        referent_table="products",
        local_cols=["product_id"],
        remote_cols=["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_order_items_product_id_products", "order_items", type_="foreignkey")
    op.drop_index("ix_order_items_product_id", table_name="order_items")
