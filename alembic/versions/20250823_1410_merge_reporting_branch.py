"""
merge reporting branch into main head

Revision ID: 20250823_1410_merge_reporting_branch
Revises: 20250822_1604_merge_heads, 20250823_1400
Create Date: 2025-08-23 14:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250823_1410_merge_reporting_branch"
down_revision: Union[str, Sequence[str], None] = (
    "20250822_1604_merge_heads",
    "20250823_1400",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge point, no-op.
    pass


def downgrade() -> None:
    # No-op for merge.
    pass
