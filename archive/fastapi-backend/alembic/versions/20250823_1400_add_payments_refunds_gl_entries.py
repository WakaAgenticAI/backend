"""
Create payments, refunds, and gl_entries tables for richer reporting views.

These tables are minimal and align with the PRD needs. If your application
later defines full models, you can extend via subsequent migrations.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250823_1400"
down_revision = "20250823_1355"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        # payments
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    method VARCHAR(32),
                    amount NUMERIC(12,2) NOT NULL DEFAULT 0,
                    status VARCHAR(32) NOT NULL,
                    reference VARCHAR(128),
                    paid_at TIMESTAMP WITHOUT TIME ZONE
                );
                CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
                CREATE INDEX IF NOT EXISTS idx_payments_paid_at ON payments(paid_at);
                """
            )
        )

        # refunds
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS refunds (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    amount NUMERIC(12,2) NOT NULL DEFAULT 0,
                    reason VARCHAR(128),
                    status VARCHAR(32) NOT NULL,
                    processed_at TIMESTAMP WITHOUT TIME ZONE
                );
                CREATE INDEX IF NOT EXISTS idx_refunds_order_id ON refunds(order_id);
                CREATE INDEX IF NOT EXISTS idx_refunds_processed_at ON refunds(processed_at);
                """
            )
        )

        # gl_entries
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS gl_entries (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR(32),
                    ref_id VARCHAR(64),
                    dr NUMERIC(14,2) DEFAULT 0,
                    cr NUMERIC(14,2) DEFAULT 0,
                    account VARCHAR(64),
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_gl_entries_created_at ON gl_entries(created_at);
                """
            )
        )
    else:
        # SQLite: create compatible schemas and create indexes separately
        # payments
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    method VARCHAR(32),
                    amount REAL NOT NULL DEFAULT 0,
                    status VARCHAR(32) NOT NULL,
                    reference VARCHAR(128),
                    paid_at TIMESTAMP
                );
                """
            )
        )
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id)"))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_payments_paid_at ON payments(paid_at)"))

        # refunds
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS refunds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    amount REAL NOT NULL DEFAULT 0,
                    reason VARCHAR(128),
                    status VARCHAR(32) NOT NULL,
                    processed_at TIMESTAMP
                );
                """
            )
        )
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_refunds_order_id ON refunds(order_id)"))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_refunds_processed_at ON refunds(processed_at)"))

        # gl_entries
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS gl_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type VARCHAR(32),
                    ref_id VARCHAR(64),
                    dr REAL DEFAULT 0,
                    cr REAL DEFAULT 0,
                    account VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_gl_entries_created_at ON gl_entries(created_at)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS gl_entries"))
    op.execute(sa.text("DROP TABLE IF EXISTS refunds"))
    op.execute(sa.text("DROP TABLE IF EXISTS payments"))
