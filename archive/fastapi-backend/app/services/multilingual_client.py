"""
Multilingual Support Client for Nigerian Languages

This module provides support for Nigerian languages including Pidgin, Hausa, Yoruba, and Igbo.
It includes language detection, translation, and culturally appropriate responses.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import re
from enum import Enum

# Import will be done lazily to avoid circular imports


class NigerianLanguage(Enum):
    """Supported Nigerian languages"""
    ENGLISH = "en"
    PIDGIN = "pcm"  # Nigerian Pidgin
    HAUSA = "ha"
    YORUBA = "yo"
    IGBO = "ig"


class MultilingualClient:
    """Client for handling Nigerian languages and cultural context"""
    
    def __init__(self):
        self.llm_client = None  # Will be initialized lazily
        
        # Language patterns for detection
        self.language_patterns = {
            NigerianLanguage.PIDGIN: [
                r"\b(how far|wetin|abi|sha|o|na|dey|don|go|come|make|no|yes|wahala|guy|bro|sister)\b",
                r"\b(una|dem|we|me|you|him|her|them)\b",
                r"\b(sabi|dey|don|go|come|make|no|yes)\b",
                r"\b(how body|how you dey|how far|wetin dey happen)\b"
            ],
            NigerianLanguage.HAUSA: [
                r"\b(sannu|barka|na gode|yaya|ina|wane|me|kai|shi|ita|mu|ku|su)\b",
                r"\b(da|ta|na|za|yi|ka|ki|ya|ta|mu|ku|su)\b",
                r"\b(ina kwana|ina gajiya|yaya aiki|yaya iyali)\b"
            ],
            NigerianLanguage.YORUBA: [
                r"\b(bawo|se|ki|ni|wa|lo|de|wo|se|ki|ni|wa|lo|de|wo)\b",
                r"\b(bawo ni|se daadaa|ki lo n sele|e kaaro|e kaasan|e kaale)\b",
                r"\b(omo|iya|baba|egbon|aburo|omo|iya|baba)\b"
            ],
            NigerianLanguage.IGBO: [
                r"\b(kedu|gini|olee|nke|na|ga|ga|ga|ga|ga|ga|ga|ga)\b",
                r"\b(kedu ka i mere|gini ka i na eme|olee ebe i no|nke a bu|na|ga|ga|ga|ga|ga|ga|ga|ga)\b",
                r"\b(nna|nne|nwanne|nwa|nna|nne|nwanne|nwa)\b"
            ]
        }
        
        # Cultural context and greetings
        self.cultural_context = {
            NigerianLanguage.PIDGIN: {
                "greetings": ["how far", "how you dey", "how body", "wetin dey happen"],
                "responses": ["i dey fine", "everything dey alright", "no wahala", "i dey kampe"],
                "respect_terms": ["oga", "madam", "sir", "aunty", "uncle"],
                "business_terms": ["business dey move", "market dey hot", "customer dey plenty", "money dey flow"]
            },
            NigerianLanguage.HAUSA: {
                "greetings": ["sannu", "barka", "ina kwana", "yaya aiki"],
                "responses": ["lafiya", "na gode", "yaya", "da kyau"],
                "respect_terms": ["sarki", "hakimi", "mallam", "hajiya"],
                "business_terms": ["kasuwa", "ciniki", "riba", "kudi"]
            },
            NigerianLanguage.YORUBA: {
                "greetings": ["bawo ni", "e kaaro", "e kaasan", "e kaale"],
                "responses": ["mo wa daadaa", "e se", "a dupe", "o dara"],
                "respect_terms": ["baba", "iya", "egbon", "aburo"],
                "business_terms": ["owo", "ise", "owo-ise", "owo-owo"]
            },
            NigerianLanguage.IGBO: {
                "greetings": ["kedu", "kedu ka i mere", "gini ka i na eme"],
                "responses": ["odimma", "nke a bu", "na", "ga"],
                "respect_terms": ["nna", "nne", "nwanne", "nwa"],
                "business_terms": ["ego", "oru", "ahia", "nkwu"]
            }
        }
    
    def detect_language(self, text: str) -> Tuple[NigerianLanguage, float]:
        """Detect the primary language of the text"""
        text_lower = text.lower()
        scores = {}
        
        for language, patterns in self.language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches
            
            # Normalize score by text length
            if len(text.split()) > 0:
                scores[language] = score / len(text.split())
            else:
                scores[language] = 0
        
        # Default to English if no clear match
        if not scores or max(scores.values()) < 0.1:
            return NigerianLanguage.ENGLISH, 0.5
        
        detected_language = max(scores, key=scores.get)
        confidence = min(scores[detected_language], 1.0)
        
        return detected_language, confidence
    
    def _get_llm_client(self):
        """Get LLM client lazily to avoid circular imports"""
        if self.llm_client is None:
            from app.services.llm_client import get_llm_client
            self.llm_client = get_llm_client()
        return self.llm_client

    async def translate_to_english(self, text: str, source_language: NigerianLanguage) -> str:
        """Translate text to English"""
        if source_language == NigerianLanguage.ENGLISH:
            return text
        
        try:
            llm_client = self._get_llm_client()
            language_name = source_language.value
            prompt = f"""
            Translate this {language_name} text to English. Provide only the translation, no explanations.
            
            Text: {text}
            """
            
            response = await llm_client.complete(
                prompt=prompt,
                system="You are a professional translator specializing in Nigerian languages. Translate accurately and naturally.",
                temperature=0.1,
                max_tokens=200
            )
            
            return response.strip()
            
        except Exception:
            return text  # Return original if translation fails
    
    async def translate_to_language(self, text: str, target_language: NigerianLanguage) -> str:
        """Translate text to target Nigerian language"""
        if target_language == NigerianLanguage.ENGLISH:
            return text
        
        try:
            llm_client = self._get_llm_client()
            language_name = target_language.value
            prompt = f"""
            Translate this English text to {language_name}. Use natural, conversational language appropriate for Nigerian business context.
            
            Text: {text}
            """
            
            response = await llm_client.complete(
                prompt=prompt,
                system="You are a professional translator specializing in Nigerian languages. Translate naturally and culturally appropriately.",
                temperature=0.3,
                max_tokens=200
            )
            
            return response.strip()
            
        except Exception:
            return text  # Return original if translation fails
    
    async def generate_culturally_appropriate_response(
        self, 
        message: str, 
        context: str,
        target_language: NigerianLanguage = NigerianLanguage.ENGLISH
    ) -> str:
        """Generate a culturally appropriate response"""
        try:
            llm_client = self._get_llm_client()
            # Get cultural context for the language
            cultural_info = self.cultural_context.get(target_language, {})
            
            # Build context-aware prompt
            context_prompt = f"""
            Respond to this message in a culturally appropriate way for Nigerian business context.
            Use respectful, professional language that shows understanding of Nigerian business culture.
            
            Message: {message}
            Context: {context}
            
            Guidelines:
            - Be respectful and professional
            - Use appropriate greetings and honorifics
            - Show understanding of Nigerian business practices
            - Be helpful and solution-oriented
            """
            
            if target_language != NigerianLanguage.ENGLISH:
                language_name = target_language.value
                context_prompt += f"\n- Respond in {language_name} language"
                
                # Add cultural context
                if cultural_info:
                    greetings = cultural_info.get("greetings", [])
                    respect_terms = cultural_info.get("respect_terms", [])
                    if greetings:
                        context_prompt += f"\n- Use appropriate greetings like: {', '.join(greetings[:3])}"
                    if respect_terms:
                        context_prompt += f"\n- Use respectful terms like: {', '.join(respect_terms[:3])}"
            
            response = await llm_client.complete(
                prompt=context_prompt,
                system="You are a helpful Nigerian business assistant. Respond with cultural sensitivity and professionalism.",
                temperature=0.7,
                max_tokens=300
            )
            
            return response.strip()
            
        except Exception:
            return "I understand your request. How can I help you today?"
    
    def get_language_support_info(self) -> Dict[str, any]:
        """Get information about supported languages"""
        return {
            "supported_languages": [
                {
                    "code": lang.value,
                    "name": lang.name,
                    "display_name": self._get_display_name(lang)
                }
                for lang in NigerianLanguage
            ],
            "detection_confidence_threshold": 0.1,
            "cultural_context_available": True,
            "translation_supported": True
        }
    
    def _get_display_name(self, language: NigerianLanguage) -> str:
        """Get display name for language"""
        display_names = {
            NigerianLanguage.ENGLISH: "English",
            NigerianLanguage.PIDGIN: "Nigerian Pidgin",
            NigerianLanguage.HAUSA: "Hausa",
            NigerianLanguage.YORUBA: "Yoruba",
            NigerianLanguage.IGBO: "Igbo"
        }
        return display_names.get(language, language.name)
    
    async def process_multilingual_message(
        self, 
        message: str, 
        context: Optional[str] = None
    ) -> Dict[str, any]:
        """Process a message with full multilingual support"""
        # Detect language
        detected_lang, confidence = self.detect_language(message)
        
        # Translate to English for processing
        english_message = await self.translate_to_english(message, detected_lang)
        
        # Generate response in detected language
        response = await self.generate_culturally_appropriate_response(
            english_message, 
            context or "", 
            detected_lang
        )
        
        return {
            "original_message": message,
            "detected_language": detected_lang.value,
            "confidence": confidence,
            "english_translation": english_message,
            "response": response,
            "response_language": detected_lang.value
        }


# Global instance
_multilingual_client = None

def get_multilingual_client() -> MultilingualClient:
    global _multilingual_client
    if _multilingual_client is None:
        _multilingual_client = MultilingualClient()
    return _multilingual_client
