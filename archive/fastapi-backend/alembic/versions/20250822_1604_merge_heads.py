"""merge heads customers and audit branch

Revision ID: 20250822_1604_merge_heads
Revises: 92093110c13f, 20250822_1559_add_customers
Create Date: 2025-08-22 16:04:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250822_1604_merge_heads"
down_revision = ("92093110c13f", "20250822_1559_add_customers")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op merge
    pass


def downgrade() -> None:
    # No-op merge
    pass
