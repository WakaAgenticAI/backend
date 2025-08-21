"""
Agents orchestrator placeholder.

This module will host the LangGraph-based Orchestrator and domain agents (Order, CRM,
Finance, Inventory Forecast, Chatbot). For now, it exposes a minimal interface stub.
"""
from __future__ import annotations
from typing import Protocol


class Agent(Protocol):
    name: str

    async def handle(self, intent: str, payload: dict) -> dict:  # pragma: no cover - stub
        ...


class Orchestrator:
    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.name] = agent

    async def route(self, intent: str, payload: dict) -> dict:  # pragma: no cover - stub
        agent = self._agents.get(intent)
        if not agent:
            return {"handled": False, "reason": "no_agent"}
        return await agent.handle(intent, payload)
