from __future__ import annotations
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta

from app.kb.chroma import get_collection
from app.core.config import get_settings


class ConversationMemory:
    """ChromaDB-based conversation memory with semantic search capabilities"""
    
    def __init__(self):
        self.settings = get_settings()
        self.collection = get_collection("chat_memory")
        self.max_context_messages = 10
        self.max_memory_age_days = 30
    
    def add_message(
        self, 
        session_id: int, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a message to conversation memory"""
        message_id = str(uuid.uuid4())
        
        # Create document text for embedding
        doc_text = f"{role}: {content}"
        
        # Prepare metadata
        msg_metadata = {
            "session_id": str(session_id),
            "role": role,
            "timestamp": datetime.utcnow().isoformat(),
            "message_id": message_id,
            **(metadata or {})
        }
        
        # Store in ChromaDB
        self.collection.add(
            ids=[message_id],
            documents=[doc_text],
            metadatas=[msg_metadata]
        )
        
        return message_id
    
    def get_context(
        self, 
        session_id: int, 
        limit: int = 10,
        include_recent: bool = True
    ) -> List[Dict[str, Any]]:
        """Get conversation context for a session"""
        try:
            # Get recent messages for this session
            if include_recent:
                recent_messages = self._get_recent_messages(session_id, limit)
            else:
                recent_messages = []
            
            return recent_messages
            
        except Exception:
            # Fallback to empty context
            return []
    
    def search_similar_messages(
        self, 
        session_id: int, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar messages in conversation history"""
        try:
            # Search with session filter
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where={"session_id": str(session_id)}
            )
            
            messages = []
            if results["ids"] and results["ids"][0]:
                for i, msg_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    content = results["documents"][0][i]
                    
                    # Extract role and content from document
                    if ": " in content:
                        role, msg_content = content.split(": ", 1)
                    else:
                        role, msg_content = "unknown", content
                    
                    messages.append({
                        "id": msg_id,
                        "role": role,
                        "content": msg_content,
                        "metadata": metadata,
                        "similarity": results.get("distances", [[]])[0][i] if results.get("distances") else 0
                    })
            
            return messages
            
        except Exception:
            return []
    
    def get_session_summary(self, session_id: int) -> Optional[str]:
        """Get a summary of the conversation session"""
        try:
            # Get all messages for this session
            results = self.collection.get(
                where={"session_id": str(session_id)},
                limit=100  # Reasonable limit
            )
            
            if not results["ids"]:
                return None
            
            # Extract messages
            messages = []
            for i, msg_id in enumerate(results["ids"]):
                content = results["documents"][i]
                metadata = results["metadatas"][i]
                
                if ": " in content:
                    role, msg_content = content.split(": ", 1)
                else:
                    role, msg_content = "unknown", content
                
                messages.append({
                    "role": role,
                    "content": msg_content,
                    "timestamp": metadata.get("timestamp")
                })
            
            # Sort by timestamp
            messages.sort(key=lambda x: x.get("timestamp", ""))
            
            # Create summary
            if len(messages) <= 5:
                return "Short conversation with " + str(len(messages)) + " messages."
            else:
                return f"Conversation with {len(messages)} messages. Recent topics: " + \
                       ", ".join([msg["content"][:50] + "..." for msg in messages[-3:]])
                       
        except Exception:
            return None
    
    def cleanup_old_messages(self, days: int = 30) -> int:
        """Clean up old messages from memory"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            
            # Get old messages
            results = self.collection.get(
                where={"timestamp": {"$lt": cutoff_str}},
                limit=1000  # Process in batches
            )
            
            if results["ids"]:
                # Delete old messages
                self.collection.delete(ids=results["ids"])
                return len(results["ids"])
            
            return 0
            
        except Exception:
            return 0
    
    def _get_recent_messages(self, session_id: int, limit: int) -> List[Dict[str, Any]]:
        """Get recent messages for a session"""
        try:
            results = self.collection.get(
                where={"session_id": str(session_id)},
                limit=limit * 2  # Get more to sort by timestamp
            )
            
            if not results["ids"]:
                return []
            
            # Extract and sort messages
            messages = []
            for i, msg_id in enumerate(results["ids"]):
                content = results["documents"][i]
                metadata = results["metadatas"][i]
                
                if ": " in content:
                    role, msg_content = content.split(": ", 1)
                else:
                    role, msg_content = "unknown", content
                
                messages.append({
                    "id": msg_id,
                    "role": role,
                    "content": msg_content,
                    "timestamp": metadata.get("timestamp"),
                    "metadata": metadata
                })
            
            # Sort by timestamp and limit
            messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return messages[:limit]
            
        except Exception:
            return []


# Global instance
_memory_client = None

def get_memory_client() -> ConversationMemory:
    global _memory_client
    if _memory_client is None:
        _memory_client = ConversationMemory()
    return _memory_client


# Backward compatibility functions
def add_message(session_id: int, role: str, content: str) -> None:
    """Backward compatible function"""
    client = get_memory_client()
    client.add_message(session_id, role, content)


def get_context(session_id: int) -> List[Dict[str, Any]]:
    """Backward compatible function"""
    client = get_memory_client()
    return client.get_context(session_id)
