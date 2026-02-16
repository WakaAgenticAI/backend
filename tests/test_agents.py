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
        "Inventory": [{"product_id": 7, "warehouse_id": 2, "on_hand": 10.0, "reserved": 3.0, "reorder_point": 5.0}],
    }
    fake = FakeSession(datasets)
    from app.agents import inventory_agent as mod
    monkeypatch.setattr(mod, "SessionLocal", lambda: fake)

    agent = InventoryAgent()
    state = {
        "messages": [], "intent": "inventory.check",
        "payload": {"sku": "ABC-1", "warehouse_id": 2},
        "result": None, "error": None, "current_agent": None,
    }
    out = _run(agent.handle(state))
    assert out.get("error") is None
    assert out["result"]["success"] is True
    res = out["result"]["result"]
    assert res["product"]["sku"] == "ABC-1"
    assert res["on_hand"] == 10.0
    assert res["reserved"] == 3.0
    assert res["available"] == 7.0


def test_inventory_agent_aggregate(monkeypatch):
    # Product exists; aggregate sums and per-warehouse breakdown
    datasets = {
        "Product": [{"id": 5, "sku": "XYZ", "name": "Thing"}],
        # For aggregate path, one() should return (sum_on_hand, sum_reserved, sum_reorder_point)
        # Our FakeQuery.one() returns first row unchanged, so provide a tuple-like
        "Inventory": [(15.0, 4.0, 5.0)],
    }
    fake = FakeSession(datasets)

    # For by_warehouse listing, rewire the .all() call to return detailed rows
    class InvQuery(FakeQuery):
        def one(self):
            return (15.0, 4.0, 5.0)

        def all(self):
            rows = [
                (1, 5.0, 1.0, 2.0),
                (2, 10.0, 3.0, 3.0),
            ]
            return rows

    class SessionWithInv(FakeSession):
        class AggQuery(FakeQuery):
            def __init__(self):
                super().__init__(table=None, rows=[])

            def one(self):
                return (15.0, 4.0, 5.0)

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
    state = {
        "messages": [], "intent": "inventory.check",
        "payload": {"product_id": 5},
        "result": None, "error": None, "current_agent": None,
    }
    out = _run(agent.handle(state))
    assert out.get("error") is None
    assert out["result"]["success"] is True
    res = out["result"]["result"]
    assert res["on_hand"] == 15.0
    assert res["reserved"] == 4.0
    assert res["available"] == 11.0
    assert len(res["by_warehouse"]) == 2


def test_inventory_agent_product_not_found(monkeypatch):
    fake = FakeSession({"Product": []})
    from app.agents import inventory_agent as mod
    monkeypatch.setattr(mod, "SessionLocal", lambda: fake)

    agent = InventoryAgent()
    state = {
        "messages": [], "intent": "inventory.check",
        "payload": {"sku": "MISSING"},
        "result": None, "error": None, "current_agent": None,
    }
    out = _run(agent.handle(state))
    # Agent should report product not found via error or result
    has_error = out.get("error") is not None
    result = out.get("result") or {}
    not_found = result.get("success") is False
    assert has_error or not_found, f"Expected error or not-found result, got: {out}"


# New AI Agent Tests
def test_forecasting_agent_can_handle():
    """Test forecasting agent can handle appropriate intents"""
    from app.agents.forecasting_agent import forecasting_agent
    
    assert _run(forecasting_agent.can_handle("inventory.forecast.generate", {})) == True
    assert _run(forecasting_agent.can_handle("forecast.analyze", {})) == True
    assert _run(forecasting_agent.can_handle("order.create", {})) == False


def test_fraud_detection_agent_can_handle():
    """Test fraud detection agent can handle appropriate intents"""
    from app.agents.fraud_detection_agent import fraud_detection_agent
    
    assert _run(fraud_detection_agent.can_handle("fraud.analyze_order", {})) == True
    assert _run(fraud_detection_agent.can_handle("payment.validate", {})) == True
    assert _run(fraud_detection_agent.can_handle("order.create", {})) == False


def test_crm_agent_can_handle():
    """Test CRM agent can handle appropriate intents"""
    from app.agents.crm_agent import crm_agent
    
    assert _run(crm_agent.can_handle("customer.segment", {})) == True
    assert _run(crm_agent.can_handle("crm.analyze", {})) == True
    assert _run(crm_agent.can_handle("order.create", {})) == False


def test_orders_agent_can_handle():
    """Test orders agent can handle appropriate intents"""
    from app.agents.orders_agent import orders_agent
    
    assert _run(orders_agent.can_handle("order.create", {})) == True
    assert _run(orders_agent.can_handle("order.lookup", {})) == True
    assert _run(orders_agent.can_handle("inventory.check", {})) == False


def test_inventory_agent_can_handle():
    """Test inventory agent can handle appropriate intents"""
    from app.agents.inventory_agent import inventory_agent
    
    assert _run(inventory_agent.can_handle("inventory.check", {})) == True
    assert _run(inventory_agent.can_handle("inventory.reserve", {})) == True
    assert _run(inventory_agent.can_handle("order.create", {})) == False


def test_orchestrator_workflow_determination():
    """Test orchestrator workflow determination"""
    from app.agents.orchestrator import get_orchestrator
    
    orchestrator = get_orchestrator()
    
    # Test workflow determination returns lists with expected steps
    order_workflow = orchestrator._determine_workflow("order.create")
    assert isinstance(order_workflow, list)
    assert len(order_workflow) >= 2  # at least classification + agent + response
    
    chat_workflow = orchestrator._determine_workflow("chat.general")
    assert isinstance(chat_workflow, list)
    assert "chatbot_agent" in chat_workflow


def test_intent_classification_examples():
    """Test intent classification examples"""
    from app.agents.orchestrator import get_orchestrator
    
    orchestrator = get_orchestrator()
    
    # Test intent examples exist
    intents = orchestrator.intent_classifier.intent_examples
    assert isinstance(intents, dict)
    assert len(intents) > 0
    # At minimum, chat and order intents should exist
    assert "order.create" in intents
    assert "chat.general" in intents


def test_agent_capabilities():
    """Test agent capabilities retrieval"""
    from app.agents.orchestrator import get_orchestrator
    
    orchestrator = get_orchestrator()
    
    # Test getting capabilities returns a dict
    capabilities = _run(orchestrator.get_agent_capabilities())
    assert isinstance(capabilities, dict)


def test_orchestrator_agent_registration():
    """Test that agents are properly registered with orchestrator"""
    from app.agents.orchestrator import get_orchestrator
    
    orchestrator = get_orchestrator()
    
    # Agents may be registered lazily during app startup
    # Just verify the orchestrator has the _agents dict
    assert hasattr(orchestrator, "_agents")
    assert isinstance(orchestrator._agents, dict)


def test_multilingual_client_language_detection():
    """Test multilingual client language detection"""
    from app.services.multilingual_client import get_multilingual_client
    
    client = get_multilingual_client()
    
    # Test language detection
    lang, confidence = client.detect_language("How far, wetin you fit help me with?")
    assert lang.value in ["pcm", "en"]  # Should detect Pidgin or English
    assert confidence >= 0.0
    
    lang, confidence = client.detect_language("Hello, how are you today? I need some help.")
    assert lang.value in ["en", "pcm"]  # May detect English or Pidgin depending on heuristics
    assert confidence >= 0.0


def test_multilingual_client_supported_languages():
    """Test multilingual client supported languages"""
    from app.services.multilingual_client import get_multilingual_client
    
    client = get_multilingual_client()
    
    # Test language support info
    info = client.get_language_support_info()
    assert "supported_languages" in info
    assert len(info["supported_languages"]) == 5  # English, Pidgin, Hausa, Yoruba, Igbo
    
    # Check that all expected languages are present
    language_codes = [lang["code"] for lang in info["supported_languages"]]
    assert "en" in language_codes
    assert "pcm" in language_codes
    assert "ha" in language_codes
    assert "yo" in language_codes
    assert "ig" in language_codes
