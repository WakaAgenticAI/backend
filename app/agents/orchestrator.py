"""
LangGraph-based Orchestrator for coordinating domain agents.

This module implements a sophisticated agent orchestration system using LangGraph
for managing workflows between Order, CRM, Finance, Inventory Forecast, and Chatbot agents.
"""
from __future__ import annotations
from typing import Protocol, Dict, Any, List, Optional, TypedDict, Annotated
import json
import asyncio
from datetime import datetime

from app.services.llm_client import get_llm_client
from app.services.chroma_client import get_memory_client
from app.kb.service import kb_query


class AgentState(TypedDict):
    """State for agent workflow"""
    messages: Annotated[List[Dict[str, Any]], "List of messages in conversation"]
    intent: str
    payload: Dict[str, Any]
    current_agent: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    session_id: Optional[int]
    user_id: Optional[int]
    context: Dict[str, Any]


class Agent(Protocol):
    """Protocol for domain agents"""
    name: str
    description: str
    tools: List[str]

    async def handle(self, state: AgentState) -> AgentState:
        """Handle agent-specific logic"""
        ...

    async def can_handle(self, intent: str, payload: Dict[str, Any]) -> bool:
        """Check if agent can handle the given intent"""
        ...


class IntentClassifier:
    """Classifies user intents using LLM"""
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.intent_examples = {
            "order.create": "I want to place an order for 10 bags of rice",
            "order.lookup": "What's the status of my order #12345?",
            "order.cancel": "Cancel my order please",
            "inventory.check": "Do you have rice in stock?",
            "inventory.forecast": "When will we run out of rice?",
            "customer.update": "Update my phone number to 08012345678",
            "customer.lookup": "Show me customer details for John Doe",
            "payment.process": "Process payment for order #12345",
            "payment.refund": "I need a refund for my order",
            "report.generate": "Generate sales report for this month",
            "support.ticket": "I have a complaint about my order",
            "chat.general": "Hello, how are you today?",
            "chat.help": "What can you help me with?"
        }
    
    async def classify_intent(self, message: str, context: Dict[str, Any]) -> str:
        """Classify user intent from message"""
        try:
            # Build classification prompt
            examples = "\n".join([f"- {intent}: {example}" for intent, example in self.intent_examples.items()])
            
            prompt = f"""Classify the user's intent from their message. Choose the most appropriate intent from the list below.

Available intents:
{examples}

User message: "{message}"

Context: {json.dumps(context, indent=2)}

Respond with ONLY the intent name (e.g., "order.create") or "chat.general" if none match well."""

            response = await self.llm_client.complete(
                prompt=prompt,
                system="You are an intent classification expert. Respond with only the intent name.",
                temperature=0.1,
                max_tokens=50
            )
            
            # Clean response
            intent = response.strip().lower()
            if intent in self.intent_examples:
                return intent
            else:
                return "chat.general"
                
        except Exception:
            return "chat.general"


class LangGraphOrchestrator:
    """LangGraph-based orchestrator for agent coordination"""
    
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self.intent_classifier = IntentClassifier()
        self.llm_client = get_llm_client()
        self.memory_client = get_memory_client()
        
        # Workflow state
        self._workflows: Dict[str, List[str]] = {
            "order_flow": ["intent_classification", "order_agent", "response_generation"],
            "inventory_flow": ["intent_classification", "inventory_agent", "response_generation"],
            "customer_flow": ["intent_classification", "crm_agent", "response_generation"],
            "finance_flow": ["intent_classification", "finance_agent", "response_generation"],
            "support_flow": ["intent_classification", "support_agent", "response_generation"],
            "chat_flow": ["intent_classification", "chatbot_agent", "response_generation"]
        }
    
    def register_agent(self, agent: Agent) -> None:
        """Register a domain agent"""
        self._agents[agent.name] = agent
    
    async def route(self, intent: str, payload: Dict[str, Any], session_id: Optional[int] = None) -> Dict[str, Any]:
        """Route request through LangGraph workflow"""
        try:
            # Initialize state
            state: AgentState = {
                "messages": [],
                "intent": intent,
                "payload": payload,
                "current_agent": None,
                "result": None,
                "error": None,
                "session_id": session_id,
                "user_id": payload.get("user_id"),
                "context": {}
            }
            
            # Get conversation context if session_id provided
            if session_id:
                context = self.memory_client.get_context(session_id)
                state["messages"] = context
                state["context"]["conversation_history"] = context
            
            # Classify intent if not provided
            if not intent or intent == "auto":
                message = payload.get("message", "")
                intent = await self.intent_classifier.classify_intent(message, state["context"])
                state["intent"] = intent
            
            # Determine workflow
            workflow = self._determine_workflow(intent)
            
            # Execute workflow
            final_state = await self._execute_workflow(workflow, state)
            
            # Store conversation in memory
            if session_id and payload.get("message"):
                self.memory_client.add_message(
                    session_id, 
                    "user", 
                    payload["message"],
                    {"intent": intent, "timestamp": datetime.utcnow().isoformat()}
                )
                
                if final_state.get("result", {}).get("response"):
                    self.memory_client.add_message(
                        session_id,
                        "assistant",
                        final_state["result"]["response"],
                        {"agent": final_state.get("current_agent"), "timestamp": datetime.utcnow().isoformat()}
                    )
            
            return {
                "handled": True,
                "intent": intent,
                "agent": final_state.get("current_agent"),
                "result": final_state.get("result", {}),
                "error": final_state.get("error")
            }
            
        except Exception as e:
            return {
                "handled": False,
                "error": str(e),
                "reason": "orchestrator_error"
            }
    
    def _determine_workflow(self, intent: str) -> List[str]:
        """Determine workflow based on intent"""
        if intent.startswith("order."):
            return self._workflows["order_flow"]
        elif intent.startswith("inventory."):
            return self._workflows["inventory_flow"]
        elif intent.startswith("customer."):
            return self._workflows["customer_flow"]
        elif intent.startswith(("payment.", "report.", "debt.")):
            return self._workflows["finance_flow"]
        elif intent.startswith("support."):
            return self._workflows["support_flow"]
        else:
            return self._workflows["chat_flow"]
    
    async def _execute_workflow(self, workflow: List[str], state: AgentState) -> AgentState:
        """Execute LangGraph workflow"""
        for step in workflow:
            try:
                if step == "intent_classification":
                    state = await self._intent_classification_node(state)
                elif step == "order_agent":
                    state = await self._agent_node(state, "orders")
                elif step == "inventory_agent":
                    state = await self._agent_node(state, "inventory")
                elif step == "crm_agent":
                    state = await self._agent_node(state, "crm")
                elif step == "finance_agent":
                    state = await self._agent_node(state, "finance")
                elif step == "support_agent":
                    state = await self._agent_node(state, "support")
                elif step == "chatbot_agent":
                    state = await self._chatbot_node(state)
                elif step == "response_generation":
                    state = await self._response_generation_node(state)
                
                # Check for errors
                if state.get("error"):
                    break
                    
            except Exception as e:
                state["error"] = str(e)
                break
        
        return state
    
    async def _intent_classification_node(self, state: AgentState) -> AgentState:
        """Intent classification node"""
        # Intent already classified in route method
        return state
    
    async def _agent_node(self, state: AgentState, agent_type: str) -> AgentState:
        """Execute domain agent"""
        # Find appropriate agent
        agent = None
        for agent_name, agent_instance in self._agents.items():
            if agent_type in agent_name and await agent_instance.can_handle(state["intent"], state["payload"]):
                agent = agent_instance
                break
        
        if agent:
            state["current_agent"] = agent.name
            try:
                result = await agent.handle(state)
                state["result"] = result.get("result", {})
                state["error"] = result.get("error")
            except Exception as e:
                state["error"] = str(e)
        else:
            state["error"] = f"No agent found for {agent_type}"
        
        return state
    
    async def _chatbot_node(self, state: AgentState) -> AgentState:
        """Chatbot agent node"""
        try:
            message = state["payload"].get("message", "")
            
            # Get relevant knowledge base context
            kb_results = kb_query("default", message, k=3)
            
            # Generate response with context
            if kb_results:
                context_info = "\n".join([f"- {result['text']}" for result in kb_results])
                enhanced_message = f"{message}\n\nRelevant information:\n{context_info}"
            else:
                enhanced_message = message
            
            response = await self.llm_client.complete_with_rag(
                prompt=enhanced_message,
                session_id=state.get("session_id"),
                temperature=0.7
            )
            
            state["current_agent"] = "chatbot"
            state["result"] = {"response": response, "type": "chat"}
            
        except Exception as e:
            state["error"] = str(e)
        
        return state
    
    async def _response_generation_node(self, state: AgentState) -> AgentState:
        """Generate final response"""
        if not state.get("result"):
            # Generate fallback response
            message = state["payload"].get("message", "")
            response = await self.llm_client.complete(
                prompt=f"Respond to: {message}",
                session_id=state.get("session_id"),
                temperature=0.7
            )
            state["result"] = {"response": response, "type": "fallback"}
        
        return state
    
    async def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of all registered agents"""
        capabilities = {}
        for agent_name, agent in self._agents.items():
            capabilities[agent_name] = {
                "description": getattr(agent, "description", ""),
                "tools": getattr(agent, "tools", [])
            }
        return capabilities


# Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> LangGraphOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LangGraphOrchestrator()
    return _orchestrator


# Backward compatibility
class Orchestrator:
    """Backward compatible orchestrator"""
    
    def __init__(self) -> None:
        self._langgraph_orchestrator = get_orchestrator()

    def register(self, agent: Agent) -> None:
        self._langgraph_orchestrator.register_agent(agent)
    
    async def route(self, intent: str, payload: dict) -> dict:
        return await self._langgraph_orchestrator.route(intent, payload)
