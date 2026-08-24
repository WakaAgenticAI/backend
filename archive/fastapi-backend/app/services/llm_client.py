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

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


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
        max_tokens: int = 150,
        stream: bool = False,
        target_language: Optional[str] = None
    ) -> str | AsyncGenerator[str, None]:
        """Complete a prompt with context and memory"""
        
        # Get conversation context if session_id provided
        context = []
        if session_id:
            context = get_context(session_id)
        
        # Build system prompt with context and language
        system_prompt = self._build_system_prompt(system, context, target_language)
        
        # Try Groq first (for both streaming and non-streaming)
        if self.groq_client:
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
            except Exception as e:
                # Log Groq error but continue to fallback
                print(f"Groq API error: {str(e)}")
        
        # Try Ollama fallback
        try:
            return await self._ollama_complete(
                prompt, system_prompt, temperature, max_tokens, stream
            )
        except Exception as e:
            # If both fail, provide a simple rule-based response
            print(f"Ollama fallback error: {str(e)}")
            return self._simple_fallback_response(prompt)
    
    def _build_system_prompt(self, system: Optional[str], context: List[Dict], target_language: Optional[str] = None) -> str:
        """Build system prompt with conversation context and target language"""
        
        # Language-specific instructions
        language_instructions = {
            'en': 'Respond in English.',
            'pcm': 'Respond in Nigerian Pidgin (e.g., "How far?", "Wetin dey happen?", "I dey fine").',
            'ha': 'Respond in Hausa (e.g., "Sannu", "Yaya aiki?", "Lafiya lau").',
            'yo': 'Respond in Yoruba (e.g., "Bawo ni", "Se daadaa", "E kaaro").',
            'ig': 'Respond in Igbo (e.g., "Kedu", "Odimma", "Kedu ka i mere").'
        }
        
        lang_instruction = language_instructions.get(target_language or 'en', language_instructions['en'])
        
        base_system = system or f"""You are WakaAgent AI for Nigerian distribution businesses. Be brief and direct.
        {lang_instruction}
        Keep answers under 2-3 sentences."""
        
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
        """Complete using Ollama API - raises exception if unavailable"""
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
    
    def _simple_fallback_response(self, prompt: str) -> str:
        """Provide a simple rule-based response when LLM services are unavailable"""
        prompt_lower = prompt.lower()
        
        # Greetings
        if any(word in prompt_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            return "Hello! I'm WakaAgent AI. How can I assist you with your business operations today?"
        
        # Order-related queries
        if any(word in prompt_lower for word in ['order', 'purchase', 'buy']):
            return "I can help you with orders. To create an order, please use the orders section or provide customer and product details."
        
        # Inventory queries
        if any(word in prompt_lower for word in ['inventory', 'stock', 'warehouse']):
            return "I can help you check inventory levels and manage stock. Please specify which product or warehouse you'd like to inquire about."
        
        # Help queries
        if any(word in prompt_lower for word in ['help', 'assist', 'support']):
            return "I'm WakaAgent AI, your business assistant. I can help with:\n- Order management\n- Inventory tracking\n- Customer inquiries\n- Reports and analytics\n\nWhat would you like help with?"
        
        # Default response
        return f"I received your message: '{prompt}'. I'm currently operating in limited mode as the AI service is temporarily unavailable. I can still help with basic queries about orders, inventory, and business operations. Please try rephrasing your question or contact support for immediate assistance."
    
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
