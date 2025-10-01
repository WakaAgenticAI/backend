from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from app.services.ai.groq_client import GroqClient, GroqCompletionRequest
from app.services.llm_client import get_llm_client
from app.services.whisper_client import get_whisper_client
from app.services.multilingual_client import get_multilingual_client
from app.core.deps import get_current_user

router = APIRouter()


class AICompleteIn(BaseModel):
    prompt: str
    system: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 512
    session_id: Optional[int] = None
    stream: bool = False


class AICompleteOut(BaseModel):
    content: str
    session_id: Optional[int] = None
    model: Optional[str] = None


class AICompleteStreamOut(BaseModel):
    content: str
    done: bool = False


class WhisperTranscribeIn(BaseModel):
    audio_url: Optional[str] = None
    audio_data: Optional[str] = None  # base64 encoded
    filename: Optional[str] = None
    language: Optional[str] = None


class WhisperTranscribeOut(BaseModel):
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None


class IntentClassificationIn(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class IntentClassificationOut(BaseModel):
    intent: str
    confidence: float
    explanation: Optional[str] = None


class MultilingualProcessIn(BaseModel):
    message: str
    context: Optional[str] = None


class MultilingualProcessOut(BaseModel):
    original_message: str
    detected_language: str
    confidence: float
    english_translation: str
    response: str
    response_language: str


@router.post("/complete", response_model=AICompleteOut)
async def ai_complete(
    payload: AICompleteIn, 
    user=Depends(get_current_user)
) -> AICompleteOut:
    """Complete a prompt using AI with conversation memory"""
    try:
        llm_client = get_llm_client()
        
        if payload.stream:
            raise HTTPException(
                status_code=400, 
                detail="Use /complete/stream endpoint for streaming responses"
            )
        
        response = await llm_client.complete(
            prompt=payload.prompt,
            system=payload.system,
            session_id=payload.session_id,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens
        )
        
        return AICompleteOut(
            content=response,
            session_id=payload.session_id,
            model="llama3.1:8b"  # Default model
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.post("/complete/stream")
async def ai_complete_stream(
    payload: AICompleteIn,
    user=Depends(get_current_user)
):
    """Stream AI completion response"""
    try:
        llm_client = get_llm_client()
        
        async def generate():
            try:
                async for chunk in await llm_client.complete(
                    prompt=payload.prompt,
                    system=payload.system,
                    session_id=payload.session_id,
                    temperature=payload.temperature,
                    max_tokens=payload.max_tokens,
                    stream=True
                ):
                    response_data = AICompleteStreamOut(
                        content=chunk,
                        done=False
                    )
                    yield f"data: {response_data.model_dump_json()}\n\n"
                
                # Send final done message
                final_data = AICompleteStreamOut(content="", done=True)
                yield f"data: {final_data.model_dump_json()}\n\n"
                
            except Exception as e:
                error_data = AICompleteStreamOut(
                    content=f"Error: {str(e)}",
                    done=True
                )
                yield f"data: {error_data.model_dump_json()}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming error: {str(e)}")


@router.post("/complete/rag", response_model=AICompleteOut)
async def ai_complete_rag(
    payload: AICompleteIn,
    collection: str = "default",
    top_k: int = 3,
    user=Depends(get_current_user)
) -> AICompleteOut:
    """Complete a prompt using RAG (Retrieval Augmented Generation)"""
    try:
        llm_client = get_llm_client()
        
        response = await llm_client.complete_with_rag(
            prompt=payload.prompt,
            collection=collection,
            top_k=top_k,
            session_id=payload.session_id,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens
        )
        
        return AICompleteOut(
            content=response,
            session_id=payload.session_id,
            model="llama3.1:8b"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG error: {str(e)}")


@router.post("/transcribe", response_model=WhisperTranscribeOut)
async def transcribe_audio(
    payload: WhisperTranscribeIn,
    user=Depends(get_current_user)
) -> WhisperTranscribeOut:
    """Transcribe audio using Whisper"""
    try:
        whisper_client = get_whisper_client()
        
        if payload.audio_url:
            text = await whisper_client.transcribe_from_url(
                payload.audio_url, 
                payload.language
            )
        elif payload.audio_data and payload.filename:
            text = await whisper_client.transcribe_from_base64(
                payload.audio_data,
                payload.filename,
                payload.language
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either audio_url or audio_data+filename is required"
            )
        
        if not text:
            raise HTTPException(
                status_code=400,
                detail="Failed to transcribe audio"
            )
        
        return WhisperTranscribeOut(
            text=text,
            language=payload.language or "auto"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@router.post("/classify-intent", response_model=IntentClassificationOut)
async def classify_intent(
    payload: IntentClassificationIn,
    user=Depends(get_current_user)
) -> IntentClassificationOut:
    """Classify user intent from message"""
    try:
        from app.agents.orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        intent = await orchestrator.intent_classifier.classify_intent(
            payload.message,
            payload.context or {}
        )
        
        # Calculate confidence based on intent match
        confidence = 0.9 if intent != "chat.general" else 0.5
        
        return IntentClassificationOut(
            intent=intent,
            confidence=confidence,
            explanation=f"Classified as {intent} with {confidence:.1%} confidence"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intent classification error: {str(e)}")


@router.post("/multilingual", response_model=MultilingualProcessOut)
async def process_multilingual_message(
    payload: MultilingualProcessIn,
    user=Depends(get_current_user)
) -> MultilingualProcessOut:
    """Process message with full multilingual support"""
    try:
        multilingual_client = get_multilingual_client()
        
        result = await multilingual_client.process_multilingual_message(
            payload.message,
            payload.context
        )
        
        return MultilingualProcessOut(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multilingual processing error: {str(e)}")


@router.get("/languages")
async def get_supported_languages(user=Depends(get_current_user)) -> Dict[str, Any]:
    """Get supported languages information"""
    try:
        multilingual_client = get_multilingual_client()
        return multilingual_client.get_language_support_info()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Language info error: {str(e)}")


@router.get("/capabilities")
async def get_ai_capabilities(user=Depends(get_current_user)) -> Dict[str, Any]:
    """Get AI system capabilities"""
    try:
        from app.agents.orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        agent_capabilities = await orchestrator.get_agent_capabilities()
        
        whisper_client = get_whisper_client()
        multilingual_client = get_multilingual_client()
        
        return {
            "llm_models": ["llama3.1:8b", "groq-llama3-8b-8192"],
            "supported_languages": ["en", "pcm", "ha", "yo", "ig"],
            "audio_formats": whisper_client.get_supported_formats(),
            "agents": agent_capabilities,
            "multilingual_support": multilingual_client.get_language_support_info(),
            "features": [
                "text_completion",
                "streaming",
                "rag",
                "voice_transcription",
                "intent_classification",
                "conversation_memory",
                "multilingual_support",
                "cultural_context",
                "language_detection",
                "translation"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capabilities error: {str(e)}")


@router.post("/complete", response_model=AICompleteOut)
async def ai_complete_legacy(payload: AICompleteIn) -> AICompleteOut:
    """Legacy endpoint for backward compatibility"""
    try:
        client = GroqClient()
        text = client.complete(
            GroqCompletionRequest(
                prompt=payload.prompt,
                system=payload.system,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            )
        )
        return AICompleteOut(content=text)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # fallback
        raise HTTPException(status_code=500, detail="AI service error") from e
