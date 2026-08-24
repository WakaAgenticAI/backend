"""
Add reports.insights_json and create materialized views for daily sales and monthly audit

This migration is defensive against partially present schemas. It will:
- Create table reports if it does not exist (minimal schema used by PRD)
- Add column insights_json to reports if it does not exist
- Create materialized views mv_daily_sales, mv_daily_sales_by_product, mv_monthly_audit
  • Views are created only if their dependencies exist; otherwise they are skipped for now
- Create indexes on the materialized views when created

Downgrade will drop the materialized views and remove insights_json, but will NOT drop
reports table if it already existed before.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250823_1355"
down_revision = "92093110c13f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        # 1) Ensure reports table exists (minimal schema per PRD)
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR(64) NOT NULL,
                    params JSONB DEFAULT '{}'::jsonb,
                    file_url TEXT,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
                """
            )
        )

        # 2) Add insights_json column if missing
        op.execute(
            sa.text(
                """
                ALTER TABLE reports
                ADD COLUMN IF NOT EXISTS insights_json JSONB;
                """
            )
        )

        # 3) mv_daily_sales (uses orders + optional payments/refunds)
        op.execute(
            sa.text(
                """
                DO $$
                DECLARE
                  has_orders BOOLEAN := to_regclass('public.orders') IS NOT NULL;
                  has_payments BOOLEAN := to_regclass('public.payments') IS NOT NULL;
                  has_refunds BOOLEAN := to_regclass('public.refunds') IS NOT NULL;
                BEGIN
                  IF has_orders THEN
                    IF to_regclass('public.mv_daily_sales') IS NOT NULL THEN
                      EXECUTE 'DROP MATERIALIZED VIEW IF EXISTS public.mv_daily_sales';
                    END IF;

                    IF has_payments AND has_refunds THEN
                      EXECUTE $mv$
                        CREATE MATERIALIZED VIEW public.mv_daily_sales AS
                        WITH base_orders AS (
                          SELECT DATE(o.created_at) AS sales_date, o.id, o.total, 0.0::numeric AS tax, 0.0::numeric AS discount
                          FROM public.orders o
                          WHERE o.status IN ('PAID','FULFILLED','paid','fulfilled','completed')
                        ),
                        paid AS (
                          SELECT DATE(p.paid_at) AS sales_date, SUM(p.amount) AS gross_collected
                          FROM public.payments p WHERE p.status IN ('SUCCESS','success','paid') GROUP BY 1
                        ),
                        refunds AS (
                          SELECT DATE(r.processed_at) AS sales_date, SUM(r.amount) AS total_refunds
                          FROM public.refunds r WHERE r.status IN ('PROCESSED','processed') GROUP BY 1
                        )
                        SELECT b.sales_date,
                               COUNT(*) AS orders_count,
                               SUM(b.total) AS gross_sales,
                               SUM(b.discount) AS discounts,
                               SUM(b.tax) AS tax,
                               COALESCE(p.gross_collected,0) AS gross_collected,
                               COALESCE(r.total_refunds,0) AS refunds,
                               (COALESCE(p.gross_collected,0)-COALESCE(r.total_refunds,0)) AS net_collected,
                               CASE WHEN COUNT(*)>0 THEN SUM(b.total)::numeric/COUNT(*) ELSE 0 END AS avg_order_value
                        FROM base_orders b
                        LEFT JOIN paid p ON p.sales_date=b.sales_date
                        LEFT JOIN refunds r ON r.sales_date=b.sales_date
                        GROUP BY b.sales_date,p.gross_collected,r.total_refunds
                        ORDER BY b.sales_date DESC;
                      $mv$;
                    ELSE
                      EXECUTE $mv$
                        CREATE MATERIALIZED VIEW public.mv_daily_sales AS
                        SELECT DATE(o.created_at) AS sales_date,
                               COUNT(*) AS orders_count,
                               SUM(o.total) AS gross_sales,
                               0.0::numeric AS discounts,
                               0.0::numeric AS tax,
                               0.0::numeric AS gross_collected,
                               0.0::numeric AS refunds,
                               0.0::numeric AS net_collected,
                               CASE WHEN COUNT(*)>0 THEN SUM(o.total)::numeric/COUNT(*) ELSE 0 END AS avg_order_value
                        FROM public.orders o
                        WHERE o.status IN ('PAID','FULFILLED','paid','fulfilled','completed')
                        GROUP BY DATE(o.created_at)
                        ORDER BY DATE(o.created_at) DESC;
                      $mv$;
                    END IF;

                    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_mv_daily_sales_date ON public.mv_daily_sales (sales_date)';
                  END IF;
                END$$;
                """
            )
        )

        # 4) mv_daily_sales_by_product
        op.execute(
            sa.text(
                """
                DO $$
                DECLARE
                  has_orders BOOLEAN := to_regclass('public.orders') IS NOT NULL;
                  has_order_items BOOLEAN := to_regclass('public.order_items') IS NOT NULL;
                BEGIN
                  IF has_orders AND has_order_items THEN
                    IF to_regclass('public.mv_daily_sales_by_product') IS NOT NULL THEN
                      EXECUTE 'DROP MATERIALIZED VIEW IF EXISTS public.mv_daily_sales_by_product';
                    END IF;

                    EXECUTE $mvp$
                      CREATE MATERIALIZED VIEW public.mv_daily_sales_by_product AS
                      SELECT DATE(o.created_at) AS sales_date, oi.product_id,
                             SUM(oi.qty) AS units_sold, SUM(oi.line_total) AS revenue
                      FROM public.orders o
                      JOIN public.order_items oi ON oi.order_id=o.id
                      WHERE o.status IN ('PAID','FULFILLED','paid','fulfilled','completed')
                      GROUP BY 1,2
                      ORDER BY 1 DESC, 2 ASC;
                    $mvp$;

                    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_mv_daily_sales_by_product_date ON public.mv_daily_sales_by_product (sales_date)';
                    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_mv_daily_sales_by_product_product ON public.mv_daily_sales_by_product (product_id)';
                  END IF;
                END$$;
                """
            )
        )

        # 5) mv_monthly_audit
        op.execute(
            sa.text(
                """
                DO $$
                DECLARE
                  has_audit BOOLEAN := to_regclass('public.audit_logs') IS NOT NULL;
                  has_gl BOOLEAN := to_regclass('public.gl_entries') IS NOT NULL;
                BEGIN
                  IF has_audit THEN
                    IF to_regclass('public.mv_monthly_audit') IS NOT NULL THEN
                      EXECUTE 'DROP MATERIALIZED VIEW IF EXISTS public.mv_monthly_audit';
                    END IF;

                    IF has_gl THEN
                      EXECUTE $mma$
                        CREATE MATERIALIZED VIEW public.mv_monthly_audit AS
                        WITH months AS (
                          SELECT date_trunc('month', ts)::date AS month FROM (
                            SELECT created_at AS ts FROM public.audit_logs
                            UNION ALL
                            SELECT created_at AS ts FROM public.gl_entries
                          ) s
                        ),
                        audit AS (
                          SELECT date_trunc('month', created_at)::date AS month,
                                 COUNT(*) FILTER (WHERE action ILIKE 'LOGIN%') AS logins,
                                 COUNT(*) FILTER (WHERE action ILIKE 'ROLE%') AS role_changes
                          FROM public.audit_logs GROUP BY 1
                        ),
                        ledger AS (
                          SELECT date_trunc('month', created_at)::date AS month,
                                 SUM(dr) AS total_debits, SUM(cr) AS total_credits,
                                 (SUM(dr)-SUM(cr)) AS imbalance
                          FROM public.gl_entries GROUP BY 1
                        )
                        SELECT m.month,
                               COALESCE(a.logins,0) AS login_events,
                               COALESCE(a.role_changes,0) AS role_changes,
                               COALESCE(l.total_debits,0) AS total_debits,
                               COALESCE(l.total_credits,0) AS total_credits,
                               COALESCE(l.imbalance,0) AS ledger_imbalance
                        FROM (SELECT DISTINCT month FROM months) m
                        LEFT JOIN audit a ON a.month=m.month
                        LEFT JOIN ledger l ON l.month=m.month
                        ORDER BY m.month DESC;
                      $mma$;
                    ELSE
                      EXECUTE $mma$
                        CREATE MATERIALIZED VIEW public.mv_monthly_audit AS
                        WITH audit AS (
                          SELECT date_trunc('month', created_at)::date AS month,
                                 COUNT(*) FILTER (WHERE action ILIKE 'LOGIN%') AS logins,
                                 COUNT(*) FILTER (WHERE action ILIKE 'ROLE%') AS role_changes
                          FROM public.audit_logs GROUP BY 1
                        )
                        SELECT a.month,
                               a.logins AS login_events,
                               a.role_changes AS role_changes,
                               0.0::numeric AS total_debits,
                               0.0::numeric AS total_credits,
                               0.0::numeric AS ledger_imbalance
                        FROM audit a
                        ORDER BY a.month DESC;
                      $mma$;
                    END IF;

                    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_mv_monthly_audit_month ON public.mv_monthly_audit (month)';
                  END IF;
                END$$;
                """
            )
        )
    else:
        # SQLite / others: create minimal reports table and insights column; skip matviews.
        op.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type VARCHAR(64) NOT NULL,
                    params TEXT DEFAULT '{}',
                    file_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )

        # Try to add insights_json column as TEXT if not present
        try:
            op.execute(sa.text("ALTER TABLE reports ADD COLUMN insights_json TEXT"))
        except Exception:
            # Column likely exists or SQLite version does not support IF NOT EXISTS; ignore
            pass


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS public.mv_daily_sales"))
        op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS public.mv_daily_sales_by_product"))
        op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS public.mv_monthly_audit"))

        op.execute(
            sa.text(
                """
                DO $$
                BEGIN
                  IF to_regclass('public.reports') IS NOT NULL THEN
                    IF EXISTS (
                      SELECT 1 FROM information_schema.columns
                      WHERE table_schema='public' AND table_name='reports' AND column_name='insights_json'
                    ) THEN
                      EXECUTE 'ALTER TABLE public.reports DROP COLUMN IF EXISTS insights_json';
                    END IF;
                  END IF;
                END$$;
                """
            )
        )
    else:
        # SQLite: no matviews to drop; attempt to drop column is not trivial, so skip.
        pass
