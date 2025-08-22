from __future__ import annotations
import asyncio
import types
import typing as t

import pytest

from app.agents.orders_lookup_agent import OrdersLookupAgent
from app.agents.inventory_agent import InventoryAgent


class FakeQuery:
    def __init__(self, table, rows: list[dict]):
        self.table = table
        self._rows = rows
        self._pred = None

    def filter(self, *preds):  # accept one or many predicate expressions
        self._pred = preds
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def one(self):
        # emulate SQLAlchemy one() returning a tuple for aggregates
        return self._rows[0] if self._rows else (0, 0)

    def all(self):
        return self._rows

    def order_by(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self


class FakeSession:
    def __init__(self, datasets: dict[str, list[dict]]):
        self.datasets = datasets
        self.closed = False

    # Minimal query shim that selects a dataset by model class name
    def query(self, *models):
        model = models[0] if models else object
        name = getattr(model, "__name__", str(model))
        rows = self.datasets.get(name, [])
        # Convert dict rows into simple objects with attribute access
        objs = []
        for r in rows:
            o = types.SimpleNamespace(**r)
            objs.append(o)
        return FakeQuery(model, objs)

    def commit(self):
        pass

    def close(self):
        self.closed = True


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_orders_lookup_agent_found(monkeypatch):
    # Arrange: fake Order row
    datasets = {"Order": [{"id": 42, "status": "new", "total": 123.45, "currency": "NGN"}]}
    fake = FakeSession(datasets)

    from app import agents as _agents_pkg  # ensure module path exists
    from app.agents import orders_lookup_agent as mod

    monkeypatch.setattr(mod, "SessionLocal", lambda: fake)

    agent = OrdersLookupAgent()

    # Act
    out = _run(agent.handle("orders.lookup", {"order_id": 42}))

    # Assert
    assert out["handled"] is True
    assert out["result"]["id"] == 42
    assert out["result"]["currency"] == "NGN"


def test_orders_lookup_agent_not_found(monkeypatch):
    datasets = {"Order": []}
    fake = FakeSession(datasets)
    from app.agents import orders_lookup_agent as mod
    monkeypatch.setattr(mod, "SessionLocal", lambda: fake)

    agent = OrdersLookupAgent()
    out = _run(agent.handle("orders.lookup", {"order_id": 99}))
    assert out["handled"] is False
    assert out["reason"] == "not_found"


def test_inventory_agent_by_warehouse(monkeypatch):
    # Product resolved by sku, one inventory row for the warehouse
    datasets = {
        "Product": [{"id": 7, "sku": "ABC-1", "name": "Widget"}],
        "Inventory": [{"product_id": 7, "warehouse_id": 2, "on_hand": 10.0, "reserved": 3.0}],
    }
    fake = FakeSession(datasets)
    from app.agents import inventory_agent as mod
    monkeypatch.setattr(mod, "SessionLocal", lambda: fake)

    agent = InventoryAgent()
    out = _run(agent.handle("inventory.check", {"sku": "ABC-1", "warehouse_id": 2}))
    assert out["handled"] is True
    res = out["result"]
    assert res["product"]["sku"] == "ABC-1"
    assert res["warehouse"] == 2
    assert res["on_hand"] == 10.0
    assert res["reserved"] == 3.0
    assert res["available"] == 7.0


def test_inventory_agent_aggregate(monkeypatch):
    # Product exists; aggregate sums and per-warehouse breakdown
    datasets = {
        "Product": [{"id": 5, "sku": "XYZ", "name": "Thing"}],
        # For aggregate path, one() should return (sum_on_hand, sum_reserved)
        # Our FakeQuery.one() returns first row unchanged, so provide a tuple-like
        "Inventory": [(15.0, 4.0)],
    }
    fake = FakeSession(datasets)

    # For by_warehouse listing, rewire the .all() call to return detailed rows
    class InvQuery(FakeQuery):
        def one(self):
            return (15.0, 4.0)

        def all(self):
            rows = [
                (1, 5.0, 1.0),
                (2, 10.0, 3.0),
            ]
            return rows

    class SessionWithInv(FakeSession):
        class AggQuery(FakeQuery):
            def __init__(self):
                super().__init__(table=None, rows=[])

            def one(self):
                return (15.0, 4.0)

        def query(self, *models):
            model = models[0] if models else object
            name = getattr(model, "__name__", str(model))
            # If selecting Inventory columns (InstrumentedAttribute), detect via any model string containing 'Inventory.'
            if (
                name == "Inventory"
                or any("Inventory." in str(m) or getattr(m, "__name__", "") == "Inventory" for m in models)
            ):
                return InvQuery(model, [])
            # Aggregate call passes SQLAlchemy func expressions; return tuple for sums
            if name == "Product" or any(getattr(m, "__name__", "") == "Product" for m in models):
                return super().query(*models)
            return SessionWithInv.AggQuery()

    fake2 = SessionWithInv({"Product": datasets["Product"]})

    from app.agents import inventory_agent as mod
    monkeypatch.setattr(mod, "SessionLocal", lambda: fake2)

    agent = InventoryAgent()
    out = _run(agent.handle("inventory.check", {"product_id": 5}))
    assert out["handled"] is True
    res = out["result"]
    assert res["on_hand"] == 15.0
    assert res["reserved"] == 4.0
    assert res["available"] == 11.0
    assert len(res["by_warehouse"]) == 2


def test_inventory_agent_product_not_found(monkeypatch):
    fake = FakeSession({"Product": []})
    from app.agents import inventory_agent as mod
    monkeypatch.setattr(mod, "SessionLocal", lambda: fake)

    agent = InventoryAgent()
    out = _run(agent.handle("inventory.check", {"sku": "MISSING"}))
    assert out["handled"] is False
    assert out["reason"] == "product_not_found"
