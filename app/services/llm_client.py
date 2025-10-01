from __future__ import annotations
from typing import Optional, List, Dict, Any, AsyncGenerator
import os
import httpx
import json
from datetime import datetime

from app.core.config import get_settings
from app.services.ai.groq_client import GroqClient, GroqCompletionRequest
from app.kb.service import kb_query
from app.services.chroma_client import get_context, add_message
# Import will be done lazily to avoid circular imports

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")


class LLMClient:
    """Unified LLM client supporting multiple providers (Ollama, Groq, OpenAI)"""
    
    def __init__(self):
        self.settings = get_settings()
        self.groq_client = None
        self.multilingual_client = None  # Will be initialized lazily
        if self.settings.GROQ_API_KEY:
            try:
                self.groq_client = GroqClient()
            except Exception:
                pass
    
    async def complete(
        self, 
        prompt: str, 
        system: Optional[str] = None,
        session_id: Optional[int] = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """Complete a prompt with context and memory"""
        
        # Get conversation context if session_id provided
        context = []
        if session_id:
            context = get_context(session_id)
        
        # Build system prompt with context
        system_prompt = self._build_system_prompt(system, context)
        
        # Try Groq first, fallback to Ollama
        if self.groq_client and not stream:
            try:
                response = self.groq_client.complete(
                    GroqCompletionRequest(
                        prompt=prompt,
                        system=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                )
                return response
            except Exception:
                pass
        
        # Fallback to Ollama
        return await self._ollama_complete(
            prompt, system_prompt, temperature, max_tokens, stream
        )
    
    def _build_system_prompt(self, system: Optional[str], context: List[Dict]) -> str:
        """Build system prompt with conversation context"""
        base_system = system or """You are WakaAgent AI, an intelligent assistant for Nigerian distribution businesses. 
        You help with orders, inventory, customer service, and business operations. 
        Be helpful, professional, and culturally aware of Nigerian business practices.
        You can understand and respond in English, Nigerian Pidgin, Hausa, Yoruba, and Igbo.
        Always respond in the same language as the user's message, unless they specifically ask for English.
        Use appropriate cultural greetings and respect terms based on the language."""
        
        if context:
            context_str = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in context[-5:]  # Last 5 messages
            ])
            base_system += f"\n\nRecent conversation context:\n{context_str}"
        
        return base_system
    
    async def _ollama_complete(
        self, 
        prompt: str, 
        system: str, 
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> str | AsyncGenerator[str, None]:
        """Complete using Ollama API"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "model": "llama3.1:8b",  # Default model
                    "prompt": prompt,
                    "system": system,
                    "stream": stream,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                
                response = await client.post(
                    f"{OLLAMA_HOST}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                if stream:
                    return self._stream_ollama_response(response)
                else:
                    data = response.json()
                    return data.get("response", "I'm sorry, I couldn't process that request.")
                    
        except Exception as e:
            return f"I'm experiencing technical difficulties. Please try again later. Error: {str(e)}"
    
    async def _stream_ollama_response(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """Stream Ollama response"""
        async for line in response.aiter_lines():
            if line.strip():
                try:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                except json.JSONDecodeError:
                    continue
    
    async def complete_with_rag(
        self,
        prompt: str,
        collection: str = "default",
        top_k: int = 3,
        session_id: Optional[int] = None,
        **kwargs
    ) -> str:
        """Complete with RAG (Retrieval Augmented Generation)"""
        
        # Get relevant context from knowledge base
        kb_results = kb_query(collection, prompt, k=top_k)
        
        # Enhance prompt with retrieved context
        if kb_results:
            context_info = "\n\nRelevant information:\n"
            for result in kb_results:
                context_info += f"- {result['text']}\n"
            enhanced_prompt = f"{prompt}\n{context_info}"
        else:
            enhanced_prompt = prompt
        
        # Get completion
        response = await self.complete(
            enhanced_prompt, 
            session_id=session_id,
            **kwargs
        )
        
        # Store in conversation memory
        if session_id:
            add_message(session_id, "user", prompt)
            add_message(session_id, "assistant", response)
        
        return response


# Global instance
_llm_client = None

def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


# Backward compatibility
async def complete(prompt: str, session_id: int | None = None) -> str:
    """Backward compatible function"""
    client = get_llm_client()
    return await client.complete(prompt, session_id=session_id)
