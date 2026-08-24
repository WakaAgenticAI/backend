"""Comprehensive endpoint tests for orders, products, roles, notifications, reports."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient


# ── Orders endpoints ─────────────────────────────────────────

def test_list_orders(client: TestClient, auth_headers):
    r = client.get("/api/v1/orders", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_orders_with_pagination(client: TestClient, auth_headers):
    r = client.get("/api/v1/orders?page=1&page_size=5", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) <= 5


def test_list_orders_filter_status(client: TestClient, auth_headers):
    r = client.get("/api/v1/orders?status=created", headers=auth_headers)
    assert r.status_code == 200


def test_list_orders_filter_customer(client: TestClient, auth_headers):
    r = client.get("/api/v1/orders?customer_id=1", headers=auth_headers)
    assert r.status_code == 200


def test_get_order_not_found(client: TestClient, auth_headers):
    r = client.get("/api/v1/orders/999999", headers=auth_headers)
    assert r.status_code == 404


def test_create_order_missing_product(client: TestClient, auth_headers):
    r = client.post("/api/v1/orders", headers=auth_headers, json={
        "customer_id": 1,
        "items": [{"product_id": 999999, "qty": 1}],
    })
    assert r.status_code in (400, 409, 422)


def test_create_order_success(client: TestClient, auth_headers):
    # Get a product first
    prods = client.get("/api/v1/products", headers=auth_headers).json()
    if not prods:
        pytest.skip("No products seeded")
    pid = prods[0]["id"]
    r = client.post("/api/v1/orders", headers=auth_headers, json={
        "customer_id": 1,
        "items": [{"product_id": pid, "qty": 1}],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "created"
    assert data["id"] > 0


def test_get_order_success(client: TestClient, auth_headers):
    # Create an order first
    prods = client.get("/api/v1/products", headers=auth_headers).json()
    if not prods:
        pytest.skip("No products seeded")
    pid = prods[0]["id"]
    created = client.post("/api/v1/orders", headers=auth_headers, json={
        "customer_id": 1,
        "items": [{"product_id": pid, "qty": 1}],
    }).json()
    oid = created["id"]

    r = client.get(f"/api/v1/orders/{oid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == oid


def test_update_order_status(client: TestClient, auth_headers):
    prods = client.get("/api/v1/products", headers=auth_headers).json()
    if not prods:
        pytest.skip("No products seeded")
    pid = prods[0]["id"]
    created = client.post("/api/v1/orders", headers=auth_headers, json={
        "customer_id": 1,
        "items": [{"product_id": pid, "qty": 1}],
    }).json()
    oid = created["id"]

    r = client.patch(f"/api/v1/orders/{oid}", headers=auth_headers, json={"status": "paid"})
    assert r.status_code == 200
    assert r.json()["status"] == "paid"


def test_update_order_not_found(client: TestClient, auth_headers):
    r = client.patch("/api/v1/orders/999999", headers=auth_headers, json={"status": "paid"})
    assert r.status_code == 404


def test_fulfill_order(client: TestClient, auth_headers):
    prods = client.get("/api/v1/products", headers=auth_headers).json()
    if not prods:
        pytest.skip("No products seeded")
    pid = prods[0]["id"]
    created = client.post("/api/v1/orders", headers=auth_headers, json={
        "customer_id": 1,
        "items": [{"product_id": pid, "qty": 1}],
    }).json()
    oid = created["id"]

    r = client.post(f"/api/v1/orders/{oid}/fulfill", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "fulfilled"


def test_fulfill_order_not_found(client: TestClient, auth_headers):
    r = client.post("/api/v1/orders/999999/fulfill", headers=auth_headers)
    assert r.status_code == 400


# ── Products endpoints ───────────────────────────────────────

def test_list_products(client: TestClient, auth_headers):
    r = client.get("/api/v1/products", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_products_pagination(client: TestClient, auth_headers):
    r = client.get("/api/v1/products?page=1&page_size=2", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) <= 2


def test_list_products_search(client: TestClient, auth_headers):
    r = client.get("/api/v1/products?q=Apple", headers=auth_headers)
    assert r.status_code == 200


def test_list_products_filter_sku(client: TestClient, auth_headers):
    r = client.get("/api/v1/products?sku=SKU-APPLE", headers=auth_headers)
    assert r.status_code == 200


def test_create_product(client: TestClient, auth_headers):
    import uuid
    sku = f"TST-{uuid.uuid4().hex[:6].upper()}"
    r = client.post("/api/v1/products", headers=auth_headers, json={
        "sku": sku,
        "name": "Test Product",
        "unit": "unit",
        "price_ngn": 100.0,
        "tax_rate": 5.0,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["sku"] == sku


def test_create_product_duplicate_sku(client: TestClient, auth_headers):
    r = client.post("/api/v1/products", headers=auth_headers, json={
        "sku": "SKU-APPLE",
        "name": "Duplicate",
        "unit": "unit",
        "price_ngn": 100.0,
        "tax_rate": 0,
    })
    assert r.status_code == 409


def test_update_product(client: TestClient, auth_headers):
    prods = client.get("/api/v1/products", headers=auth_headers).json()
    if not prods:
        pytest.skip("No products")
    pid = prods[0]["id"]
    r = client.patch(f"/api/v1/products/{pid}", headers=auth_headers, json={"name": "Updated Name"})
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"


def test_update_product_not_found(client: TestClient, auth_headers):
    r = client.patch("/api/v1/products/999999", headers=auth_headers, json={"name": "X"})
    assert r.status_code == 404


def test_delete_product(client: TestClient, auth_headers):
    import uuid
    sku = f"DEL-{uuid.uuid4().hex[:6].upper()}"
    created = client.post("/api/v1/products", headers=auth_headers, json={
        "sku": sku, "name": "To Delete", "unit": "unit", "price_ngn": 10, "tax_rate": 0,
    }).json()
    pid = created["id"]
    r = client.delete(f"/api/v1/products/{pid}", headers=auth_headers)
    assert r.status_code == 204


def test_delete_product_not_found(client: TestClient, auth_headers):
    r = client.delete("/api/v1/products/999999", headers=auth_headers)
    assert r.status_code == 204  # idempotent


# ── Notifications endpoints ──────────────────────────────────

def test_notification_status(client: TestClient, auth_headers):
    r = client.get("/api/v1/notifications/status", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "enabled" in data
    assert "has_api_key" in data
    assert "recipients" in data


def test_notification_test_email(client: TestClient, auth_headers):
    r = client.post("/api/v1/notifications/test", headers=auth_headers, json={
        "subject": "Test from pytest",
        "message": "Automated test notification",
    })
    assert r.status_code == 200


def test_notification_low_stock_alert(client: TestClient, auth_headers):
    r = client.post("/api/v1/notifications/alert/low-stock", headers=auth_headers, json={
        "items": [{"sku": "TST-1", "product_name": "Test", "on_hand": 2, "reorder_point": 10}],
    })
    assert r.status_code == 200


def test_notification_fraud_alert(client: TestClient, auth_headers):
    r = client.post("/api/v1/notifications/alert/fraud", headers=auth_headers, json={
        "order_id": 1, "risk_score": 0.9, "risk_level": "high", "factors": ["test"],
    })
    assert r.status_code == 200


def test_notification_overdue_debts_alert(client: TestClient, auth_headers):
    r = client.post("/api/v1/notifications/alert/overdue-debts", headers=auth_headers, json={
        "debts": [{"id": 1, "type": "receivable", "entity_type": "customer", "amount_ngn": 5000, "due_date": "2025-01-01"}],
    })
    assert r.status_code == 200


def test_notification_requires_auth(client: TestClient):
    r = client.get("/api/v1/notifications/status")
    assert r.status_code == 401


# ── Reports endpoints ────────────────────────────────────────

def test_reports_require_auth(client: TestClient):
    r = client.get("/api/v1/reports/1")
    assert r.status_code == 401


# ── Roles endpoints ──────────────────────────────────────────

def test_roles_require_auth(client: TestClient):
    r = client.get("/api/v1/roles")
    assert r.status_code == 401


# ── Debts endpoints ──────────────────────────────────────────

def test_create_debt(client: TestClient, auth_headers):
    r = client.post("/api/v1/debts", headers=auth_headers, json={
        "type": "receivable",
        "entity_type": "customer",
        "amount_ngn": 5000,
        "description": "Test debt from endpoint test",
        "priority": "medium",
    })
    assert r.status_code in (200, 201)


def test_list_debts_endpoint(client: TestClient, auth_headers):
    r = client.get("/api/v1/debts", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_debts_summary_endpoint(client: TestClient, auth_headers):
    r = client.get("/api/v1/debts/reports/summary", headers=auth_headers)
    assert r.status_code == 200


def test_debts_aging_endpoint(client: TestClient, auth_headers):
    r = client.get("/api/v1/debts/reports/aging", headers=auth_headers)
    assert r.status_code == 200


# ── Inventory endpoints ──────────────────────────────────────

def test_list_inventory(client: TestClient, auth_headers):
    r = client.get("/api/v1/inventory", headers=auth_headers)
    assert r.status_code == 200


def test_list_warehouses(client: TestClient, auth_headers):
    r = client.get("/api/v1/warehouses", headers=auth_headers)
    assert r.status_code == 200


# ── Customers endpoints ──────────────────────────────────────

def test_list_customers(client: TestClient, auth_headers):
    r = client.get("/api/v1/customers", headers=auth_headers)
    assert r.status_code == 200
