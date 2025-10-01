import os
from typing import Any
from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def _set_api_prefix_env() -> None:
    os.environ.setdefault("API_V1_PREFIX", "/api/v1")


@pytest.fixture
def mock_llm_client(monkeypatch):
    """Mock LLM client for testing"""
    from app.services.llm_client import LLMClient
    
    mock_client = MagicMock(spec=LLMClient)
    mock_client.complete = AsyncMock(return_value="Test response")
    mock_client.complete_with_rag = AsyncMock(return_value="RAG response")
    
    def get_mock_client():
        return mock_client
    
    monkeypatch.setattr("app.services.llm_client.get_llm_client", get_mock_client)
    return mock_client


@pytest.fixture
def mock_whisper_client(monkeypatch):
    """Mock Whisper client for testing"""
    from app.services.whisper_client import WhisperClient
    
    mock_client = MagicMock(spec=WhisperClient)
    mock_client.transcribe_from_url = AsyncMock(return_value="Transcribed text")
    mock_client.transcribe_from_base64 = AsyncMock(return_value="Transcribed text")
    mock_client.get_supported_formats = MagicMock(return_value=[".mp3", ".wav", ".m4a"])
    
    def get_mock_client():
        return mock_client
    
    monkeypatch.setattr("app.services.whisper_client.get_whisper_client", get_mock_client)
    return mock_client


@pytest.fixture
def mock_multilingual_client(monkeypatch):
    """Mock Multilingual client for testing"""
    from app.services.multilingual_client import MultilingualClient
    
    mock_client = MagicMock(spec=MultilingualClient)
    mock_client.process_multilingual_message = AsyncMock(return_value={
        "original_message": "Hello",
        "detected_language": "en",
        "confidence": 0.9,
        "english_translation": "Hello",
        "response": "Hi there!",
        "response_language": "en"
    })
    mock_client.get_language_support_info = MagicMock(return_value={
        "supported_languages": [
            {"code": "en", "name": "ENGLISH", "display_name": "English"},
            {"code": "pcm", "name": "PIDGIN", "display_name": "Nigerian Pidgin"}
        ]
    })
    
    def get_mock_client():
        return mock_client
    
    monkeypatch.setattr("app.services.multilingual_client.get_multilingual_client", get_mock_client)
    return mock_client


@pytest.fixture
def mock_orchestrator(monkeypatch):
    """Mock orchestrator for testing"""
    from app.agents.orchestrator import LangGraphOrchestrator
    
    mock_orchestrator = MagicMock(spec=LangGraphOrchestrator)
    mock_orchestrator.intent_classifier = MagicMock()
    mock_orchestrator.intent_classifier.classify_intent = AsyncMock(return_value="order.create")
    mock_orchestrator.get_agent_capabilities = AsyncMock(return_value={
        "orders.management": {"description": "Order management", "tools": ["create_order"]}
    })
    
    def get_mock_orchestrator():
        return mock_orchestrator
    
    monkeypatch.setattr("app.agents.orchestrator.get_orchestrator", get_mock_orchestrator)
    return mock_orchestrator


def test_ai_complete_success(client: TestClient, mock_llm_client, monkeypatch):
    """Test successful AI completion"""
    # Mock authentication
    from app.core.deps import get_current_user
    from app.models.users import User
    
    mock_user = User(id=1, email="test@example.com", name="Test User")
    monkeypatch.setattr("app.core.deps.get_current_user", lambda: mock_user)
    
    r = client.post("/api/v1/ai/complete", json={"prompt": "Hello"})
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == "Test response"
    assert data["model"] == "llama3.1:8b"


def test_ai_complete_with_session(client: TestClient, mock_llm_client):
    """Test AI completion with session ID"""
    r = client.post("/api/v1/ai/complete", json={
        "prompt": "Hello",
        "session_id": 123,
        "temperature": 0.5
    })
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == "Test response"
    assert data["session_id"] == 123


def test_ai_complete_rag(client: TestClient, mock_llm_client):
    """Test RAG-enhanced completion"""
    r = client.post("/api/v1/ai/complete/rag", json={
        "prompt": "What products do you have?",
        "collection": "products",
        "top_k": 3
    })
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == "RAG response"


def test_ai_transcribe_audio_url(client: TestClient, mock_whisper_client):
    """Test audio transcription from URL"""
    r = client.post("/api/v1/ai/transcribe", json={
        "audio_url": "https://example.com/audio.mp3",
        "language": "en"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["text"] == "Transcribed text"
    assert data["language"] == "en"


def test_ai_transcribe_audio_base64(client: TestClient, mock_whisper_client):
    """Test audio transcription from base64"""
    r = client.post("/api/v1/ai/transcribe", json={
        "audio_data": "base64encodeddata",
        "filename": "test.mp3",
        "language": "auto"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["text"] == "Transcribed text"


def test_ai_transcribe_missing_data(client: TestClient, mock_whisper_client):
    """Test transcription with missing data"""
    r = client.post("/api/v1/ai/transcribe", json={})
    assert r.status_code == 400
    assert "required" in r.json()["detail"]


def test_ai_classify_intent(client: TestClient, mock_orchestrator):
    """Test intent classification"""
    r = client.post("/api/v1/ai/classify-intent", json={
        "message": "I want to place an order",
        "context": {"user_type": "customer"}
    })
    assert r.status_code == 200
    data = r.json()
    assert data["intent"] == "order.create"
    assert data["confidence"] == 0.9


def test_ai_multilingual_processing(client: TestClient, mock_multilingual_client):
    """Test multilingual message processing"""
    r = client.post("/api/v1/ai/multilingual", json={
        "message": "How far, wetin you fit help me with?",
        "context": "customer_service"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["original_message"] == "Hello"
    assert data["detected_language"] == "en"
    assert data["response"] == "Hi there!"


def test_ai_get_capabilities(client: TestClient, mock_llm_client, mock_whisper_client, mock_multilingual_client, mock_orchestrator):
    """Test AI capabilities endpoint"""
    r = client.get("/api/v1/ai/capabilities")
    assert r.status_code == 200
    data = r.json()
    assert "llm_models" in data
    assert "supported_languages" in data
    assert "audio_formats" in data
    assert "agents" in data
    assert "features" in data
    assert "multilingual_support" in data


def test_ai_get_languages(client: TestClient, mock_multilingual_client):
    """Test supported languages endpoint"""
    r = client.get("/api/v1/ai/languages")
    assert r.status_code == 200
    data = r.json()
    assert "supported_languages" in data
    assert len(data["supported_languages"]) > 0


def test_ai_complete_streaming_not_supported(client: TestClient, mock_llm_client):
    """Test that streaming is not supported in regular complete endpoint"""
    r = client.post("/api/v1/ai/complete", json={
        "prompt": "Hello",
        "stream": True
    })
    assert r.status_code == 400
    assert "stream" in r.json()["detail"]


def test_ai_complete_legacy_endpoint(client: TestClient, monkeypatch):
    """Test legacy AI completion endpoint"""
    # Mock Groq client for legacy endpoint
    from app.services.ai import groq_client as gc

    def fake_init(self, api_key=None, model=None):  # noqa: ANN001
        self._api_key = api_key or "test-key"
        self._model = model or "llama3-8b-8192"
        self._client = object()

    def fake_complete(_self, req):  # noqa: ANN001
        assert req.prompt == "Hello"
        return "Hi there!"

    monkeypatch.setattr(gc.GroqClient, "__init__", fake_init)
    monkeypatch.setattr(gc.GroqClient, "complete", fake_complete)

    r = client.post("/api/v1/ai/complete", json={"prompt": "Hello"})
    assert r.status_code == 200
    assert r.json()["content"] == "Hi there!"


def test_ai_error_handling(client: TestClient, mock_llm_client):
    """Test AI error handling"""
    # Make the mock raise an exception
    mock_llm_client.complete.side_effect = Exception("Test error")

    r = client.post("/api/v1/ai/complete", json={"prompt": "Hello"})
    assert r.status_code == 500
    assert "error" in r.json()["detail"]


def test_ai_whisper_error_handling(client: TestClient, mock_whisper_client):
    """Test Whisper error handling"""
    # Make the mock raise an exception
    mock_whisper_client.transcribe_from_url.side_effect = Exception("Transcription failed")
    
    r = client.post("/api/v1/ai/transcribe", json={
        "audio_url": "https://example.com/audio.mp3"
    })
    assert r.status_code == 500
    assert "error" in r.json()["detail"]
