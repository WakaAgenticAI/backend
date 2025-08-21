from fastapi.testclient import TestClient


def test_healthz(client: TestClient):
    r = client.get("/api/v1/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz(client: TestClient):
    r = client.get("/api/v1/readyz")
    assert r.status_code == 200
    assert r.json()["ready"] is True
