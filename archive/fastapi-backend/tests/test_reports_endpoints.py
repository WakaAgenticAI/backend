from __future__ import annotations
from fastapi.testclient import TestClient


def test_reports_protected_routes_require_auth(client: TestClient):
    # POST triggers should 401 without auth
    r = client.post("/api/v1/admin/reports/daily-sales")
    assert r.status_code == 401
    r = client.post("/api/v1/admin/reports/monthly-audit")
    assert r.status_code == 401

    # GET latest should 401 without auth
    r = client.get("/api/v1/admin/reports/daily-sales/latest")
    assert r.status_code == 401
    r = client.get("/api/v1/admin/reports/monthly-audit/latest")
    assert r.status_code == 401

    # GET report by id also protected
    r = client.get("/api/v1/reports/1")
    assert r.status_code == 401
