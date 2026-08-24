Got it ✅ — I’ll give you a **clean, final PRD** that includes everything:

* **Database migrations (Alembic)**
* **Materialized views**
* **Celery jobs**
* **Groq AI assist layer**
* **API endpoints**
* **Frontend UX**
* **Deployment plan**

This will be the **final unified PRD** for **Admin Daily Sales & Monthly Audit Reports with AI assist**.

---

# 📑 Final PRD – Admin Daily Sales & Monthly Audit Reports (with AI Assist via Groq API)

---

## 🎯 Objectives

1. Deliver **auditable daily sales reports** and **monthly audit reports**.
2. Keep existing system untouched — reports are **read-only**.
3. Use **Postgres materialized views** for reliable deterministic data.
4. Add **AI insights & anomaly detection** using **Groq API** (advisory only).
5. Surface reports in **Admin/Finance dashboards** with CSV/PDF downloads + AI summaries.

---

## 🗂️ Database Layer

### 1. Schema Changes (Alembic Migration)

```sql
-- Extend reports table to hold AI insights
ALTER TABLE reports
ADD COLUMN IF NOT EXISTS insights_json JSONB;

-- Daily sales view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_sales AS
WITH base_orders AS (
  SELECT DATE(o.created_at) AS sales_date, o.id, o.total, o.tax, o.discount
  FROM orders o
  WHERE o.status IN ('PAID','FULFILLED')
),
paid AS (
  SELECT DATE(p.paid_at) AS sales_date, SUM(p.amount) AS gross_collected
  FROM payments p WHERE p.status='SUCCESS' GROUP BY 1
),
refunds AS (
  SELECT DATE(r.processed_at) AS sales_date, SUM(r.amount) AS total_refunds
  FROM refunds r WHERE r.status='PROCESSED' GROUP BY 1
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

CREATE INDEX IF NOT EXISTS idx_mv_daily_sales_date ON mv_daily_sales (sales_date);

-- Daily sales by product
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_sales_by_product AS
SELECT DATE(o.created_at) AS sales_date, oi.product_id,
       SUM(oi.qty) AS units_sold, SUM(oi.line_total) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id=o.id
WHERE o.status IN ('PAID','FULFILLED')
GROUP BY 1,2;

-- Monthly audit view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_audit AS
WITH months AS (
  SELECT DATE_TRUNC('month', ts) AS month FROM audit_logs
  UNION SELECT DATE_TRUNC('month', created_at) FROM gl_entries
),
audit AS (
  SELECT DATE_TRUNC('month', ts) AS month,
         COUNT(*) FILTER (WHERE action ILIKE 'LOGIN%') AS logins,
         COUNT(*) FILTER (WHERE action ILIKE 'ROLE%') AS role_changes
  FROM audit_logs GROUP BY 1
),
ledger AS (
  SELECT DATE_TRUNC('month', created_at) AS month,
         SUM(dr) AS total_debits, SUM(cr) AS total_credits,
         (SUM(dr)-SUM(cr)) AS imbalance
  FROM gl_entries GROUP BY 1
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

CREATE INDEX IF NOT EXISTS idx_mv_monthly_audit_month ON mv_monthly_audit (month);
```

---

## ⚙️ Backend (FastAPI + Celery)

### Celery Jobs

```python
@celery.task
def build_daily_sales_report(run_date: str):
    metrics = query_daily_sales(run_date)
    file_url = export_and_upload(metrics, run_date)
    report_id = insert_report("daily_sales", {"date": run_date}, file_url)

    # AI Assist
    insights = generate_ai_insights(metrics, "daily_sales")
    update_report_insights(report_id, insights)
    return {"report_id": report_id, "file_url": file_url}

@celery.task
def build_monthly_audit_report(month: str):
    metrics = query_monthly_audit(month)
    file_url = export_and_upload(metrics, month, filetype="zip")
    report_id = insert_report("monthly_audit", {"month": month}, file_url)

    # AI Assist
    insights = generate_ai_insights(metrics, "monthly_audit")
    update_report_insights(report_id, insights)
    return {"report_id": report_id, "file_url": file_url}
```

---

## 🤖 AI Assist (Groq API)

### API Client

```python
import os, requests, json

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def generate_ai_insights(data: dict, report_type: str) -> dict:
    prompt = f"""
    Analyze this {report_type} report: {json.dumps(data, indent=2)}.
    - Write 2-3 sentence summary.
    - Highlight anomalies (refund spikes, imbalances, unusual logins).
    - Suggest short-term forecast if possible.
    Return JSON only with keys: summary, anomalies, forecast.
    """

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "mixtral-8x7b-32768",  # Example Groq model
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
    )
    ai_text = resp.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(ai_text)
    except Exception:
        return {"summary": ai_text, "anomalies": [], "forecast": {}}
```

---

## 🌐 API Endpoints

* `POST /admin/reports/daily-sales` → Trigger daily sales report.
* `POST /admin/reports/monthly-audit` → Trigger monthly audit report.
* `GET /reports/{id}` → Returns file URL + `insights_json`.
* `GET /admin/reports/daily-sales/latest` → Most recent.
* `GET /admin/reports/monthly-audit/latest` → Most recent.

🔐 RBAC: Only Admin + Finance roles via `reports:generate` and `reports:read` scopes.

---

## 🎨 Frontend (Admin/Finance Dashboards)

### Daily Sales (Finance → Reports)

* Download official CSV/PDF.
* AI panel:

  * Narrative summary.
  * Anomaly badges.
  * Forecast mini-chart.

### Monthly Audit (Admin → Audit)

* Download ZIP.
* AI panel:

  * Highlight anomalies.
  * Advisory notes.

⚠️ Disclaimer: “AI-generated insights — advisory only.”

---

## 🔍 Observability

* Log every report run in `audit_logs` with type = `REPORT_GENERATE`.
* Log Groq API usage with type = `REPORT_AI_SUMMARY`.
* Store hashes of AI input/output for traceability.
* Feature flag to toggle AI assist on/off.

---

## 🚀 Deployment Plan

1. Run Alembic migration (new views + `insights_json`).
2. Deploy Celery jobs (deterministic reporting first).
3. Add Groq API integration (`generate_ai_insights`).
4. Expose new endpoints in FastAPI.
5. Wire frontend UI (reports download + AI panel).
6. Backfill last 30 days daily reports + last 6 months audit reports.
7. Roll out AI assist behind feature flag, monitor usage.

---

## ✅ Deliverables

* **Daily Sales Report**: `daily_sales_YYYY-MM-DD.csv/pdf` + AI insights.
* **Monthly Audit Report**: `monthly_audit_YYYY-MM.zip` + AI insights.
* **Reports Table Entry**: `{id, type, params, file_url, insights_json}`.
* **Frontend Views**: Finance/Admin dashboards with official + AI panels.

---

This PRD ensures:

* **Auditable, deterministic SQL base**.
* **AI enrichment via Groq** (summaries, anomalies, forecasts).
* **Non-intrusive integration** with existing backend & frontend.

---

*draft the exact Alembic migration script** (Python, not just raw SQL) so you can drop it into your migrations folder
