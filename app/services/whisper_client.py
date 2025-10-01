from __future__ import annotations
from typing import Optional, Dict, Any, List
import httpx
import os
import base64
import mimetypes
from urllib.parse import urlparse

WHISPER_HOST = os.getenv("WHISPER_HOST", "http://whisper:8000")


class WhisperClient:
    """Enhanced Whisper client for voice transcription with multiple input methods"""
    
    def __init__(self):
        self.whisper_host = WHISPER_HOST
        self.supported_formats = ['.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac']
        self.max_file_size = 25 * 1024 * 1024  # 25MB limit
    
    async def transcribe_from_url(self, audio_url: str, language: Optional[str] = None) -> Optional[str]:
        """Transcribe audio from URL"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                payload = {
                    "audio_url": audio_url,
                    "language": language or "auto",
                    "model": "whisper-1",
                    "response_format": "json"
                }
                
                response = await client.post(
                    f"{self.whisper_host}/transcribe",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data.get("text", "").strip()
                
        except httpx.TimeoutException:
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 413:
                return "Audio file too large. Please use a smaller file."
            return None
        except Exception:
            return None
    
    async def transcribe_from_file(self, file_path: str, language: Optional[str] = None) -> Optional[str]:
        """Transcribe audio from local file"""
        try:
            if not os.path.exists(file_path):
                return None
            
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return "Audio file too large. Please use a smaller file."
            
            # Check file format
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in self.supported_formats:
                return f"Unsupported audio format: {ext}"
            
            async with httpx.AsyncClient(timeout=60) as client:
                with open(file_path, 'rb') as f:
                    files = {
                        'file': (os.path.basename(file_path), f, mimetypes.guess_type(file_path)[0])
                    }
                    data = {
                        'language': language or 'auto',
                        'model': 'whisper-1',
                        'response_format': 'json'
                    }
                    
                    response = await client.post(
                        f"{self.whisper_host}/transcribe",
                        files=files,
                        data=data
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result.get("text", "").strip()
                    
        except Exception:
            return None
    
    async def transcribe_from_base64(self, audio_data: str, filename: str, language: Optional[str] = None) -> Optional[str]:
        """Transcribe audio from base64 encoded data"""
        try:
            # Decode base64 data
            audio_bytes = base64.b64decode(audio_data)
            
            if len(audio_bytes) > self.max_file_size:
                return "Audio file too large. Please use a smaller file."
            
            # Check file format
            _, ext = os.path.splitext(filename)
            if ext.lower() not in self.supported_formats:
                return f"Unsupported audio format: {ext}"
            
            async with httpx.AsyncClient(timeout=60) as client:
                files = {
                    'file': (filename, audio_bytes, mimetypes.guess_type(filename)[0])
                }
                data = {
                    'language': language or 'auto',
                    'model': 'whisper-1',
                    'response_format': 'json'
                }
                
                response = await client.post(
                    f"{self.whisper_host}/transcribe",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                result = response.json()
                return result.get("text", "").strip()
                
        except Exception:
            return None
    
    async def detect_language(self, audio_url: str) -> Optional[str]:
        """Detect the language of audio"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "audio_url": audio_url,
                    "model": "whisper-1",
                    "response_format": "json"
                }
                
                response = await client.post(
                    f"{self.whisper_host}/detect-language",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data.get("language")
                
        except Exception:
            return None
    
    def is_supported_format(self, filename: str) -> bool:
        """Check if audio format is supported"""
        _, ext = os.path.splitext(filename)
        return ext.lower() in self.supported_formats
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats"""
        return self.supported_formats


# Global instance
_whisper_client = None

def get_whisper_client() -> WhisperClient:
    global _whisper_client
    if _whisper_client is None:
        _whisper_client = WhisperClient()
    return _whisper_client


# Backward compatibility
async def transcribe(audio_url: str) -> Optional[str]:
    """Backward compatible function"""
    client = get_whisper_client()
    return await client.transcribe_from_url(audio_url)
