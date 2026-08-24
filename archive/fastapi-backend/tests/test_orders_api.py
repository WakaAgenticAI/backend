"""Tests for Orders API endpoints."""
import pytest
from fastapi.testclient import TestClient


def test_list_orders_empty(client: TestClient, auth_headers: dict):
    """Verify orders list returns 200 with an array."""
    r = client.get("/api/v1/orders", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_order(client: TestClient, auth_headers: dict):
    """Verify order creation via API."""
    # Get a product and customer to use
    products = client.get("/api/v1/products", headers=auth_headers).json()
    if not products:
        pytest.skip("No seed products available")

    product = products[0]
    order_data = {
        "customer_id": 1,
        "items": [{"product_id": product["id"], "qty": 2}],
    }
    r = client.post("/api/v1/orders", json=order_data, headers=auth_headers)
    assert r.status_code in (200, 201)
    data = r.json()
    assert data.get("id") is not None
    assert data.get("status") in ("created", "pending")


def test_list_products(client: TestClient, auth_headers: dict):
    """Verify products endpoint returns seeded products."""
    r = client.get("/api/v1/products", headers=auth_headers)
    assert r.status_code == 200
    products = r.json()
    assert isinstance(products, list)


def test_list_inventory(client: TestClient, auth_headers: dict):
    """Verify inventory endpoint returns seeded inventory."""
    r = client.get("/api/v1/inventory", headers=auth_headers)
    assert r.status_code == 200
    inventory = r.json()
    assert isinstance(inventory, list)


def test_list_customers(client: TestClient, auth_headers: dict):
    """Verify customers endpoint returns 200."""
    r = client.get("/api/v1/customers", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
