"""
Voice Assistant - Speech-to-text and text-to-speech capabilities.

Enables voice interaction with the chatbot using:
- Web Speech API (browser-based)
- AWS Polly (cloud-based TTS)
- Optional: Whisper API for STT
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class VoiceLanguage(str, Enum):
    """Supported languages for voice assistant."""
    ENGLISH = "en-US"
    SPANISH = "es-ES"
    FRENCH = "fr-FR"
    GERMAN = "de-DE"
    CHINESE = "zh-CN"
    JAPANESE = "ja-JP"


class VoiceAssistant:
    """
    Voice assistant for speech-based interaction with chatbot.
    
    Features:
    - Speech-to-text (STT) using Web Speech API or Whisper
    - Text-to-speech (TTS) using AWS Polly or browser API
    - Voice command recognition
    - Multi-language support
    - Audio streaming and processing
    """
    
    def __init__(
        self,
        polly_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize voice assistant.
        
        Args:
            polly_client: AWS Polly client for TTS (optional)
            config: Configuration dictionary
        """
        self.polly_client = polly_client
        self.config = config or {}
        self.language = VoiceLanguage(self.config.get('language', 'en-US'))
        self.voice_id = self.config.get('voice_id', 'Joanna')  # Polly voice
        self.logger = logging.getLogger(__name__)
    
    async def text_to_speech(self, text: str) -> Dict[str, Any]:
        """
        Convert text to speech using AWS Polly.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Dictionary with audio_url and metadata
        """
        if not self.polly_client:
            self.logger.warning("Polly client not configured, using browser TTS")
            return {
                "method": "browser",
                "text": text,
                "language": self.language.value,
                "note": "Use browser Web Speech API for audio"
            }
        
        try:
            response = self.polly_client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=self.voice_id,
                Engine='neural'  # Use neural voices for better quality
            )
            
            # Get audio stream
            audio_stream = response['AudioStream'].read()
            
            self.logger.info(f"Generated speech for {len(text)} characters")
            
            return {
                "method": "polly",
                "audio_data": audio_stream,
                "format": "mp3",
                "voice_id": self.voice_id,
                "language": self.language.value
            }
        
        except Exception as e:
            self.logger.error(f"Error generating speech: {e}")
            return {
                "method": "browser",
                "text": text,
                "error": str(e),
                "fallback": True
            }
    
    async def speech_to_text(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Convert speech to text using Whisper API.
        
        Args:
            audio_data: Audio bytes to transcribe
            
        Returns:
            Dictionary with transcribed text and confidence
        """
        try:
            # This would use OpenAI Whisper API or similar
            # For now, return placeholder for browser-based STT
            return {
                "method": "browser_webspeech",
                "note": "Use browser Web Speech API for transcription",
                "language": self.language.value,
                "instructions": "Enable microphone and use browser's speech recognition"
            }
        
        except Exception as e:
            self.logger.error(f"Error transcribing speech: {e}")
            return {
                "error": str(e),
                "fallback": True
            }
    
    def get_voice_commands(self) -> Dict[str, str]:
        """Get available voice commands."""
        return {
            "analyze": "Analyze the current bug",
            "suggest": "Suggest a fix for this bug",
            "rollback": "Rollback the last change",
            "status": "Show workflow status",
            "list": "List all bugs",
            "export": "Export results",
            "help": "Show help information",
            "next": "Go to next bug",
            "previous": "Go to previous bug",
            "details": "Show detailed information",
            "confirm": "Confirm action",
            "cancel": "Cancel current action"
        }
    
    def parse_voice_command(self, text: str) -> Dict[str, Any]:
        """
        Parse voice input to extract command and parameters.
        
        Args:
            text: Transcribed voice text
            
        Returns:
            Dictionary with command and parameters
        """
        text_lower = text.lower().strip()
        
        # Command mapping
        commands = {
            "analyze": ["analyze", "what is", "explain", "tell me about"],
            "suggest": ["suggest", "fix", "how to fix", "what should i do"],
            "rollback": ["rollback", "undo", "revert", "go back"],
            "status": ["status", "how is it", "what's happening", "progress"],
            "list": ["list", "show all", "what bugs", "all bugs"],
            "export": ["export", "save", "download", "get results"],
            "help": ["help", "what can you do", "commands", "options"],
            "next": ["next", "go to next", "skip", "move on"],
            "previous": ["previous", "go back", "last one", "previous bug"],
            "details": ["details", "more info", "tell me more", "explain more"],
            "confirm": ["yes", "confirm", "proceed", "go ahead"],
            "cancel": ["no", "cancel", "stop", "abort"]
        }
        
        # Find matching command
        for command, keywords in commands.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return {
                        "command": command,
                        "original_text": text,
                        "confidence": 0.9 if keyword == text_lower else 0.7
                    }
        
        # No command found
        return {
            "command": "unknown",
            "original_text": text,
            "confidence": 0.0
        }
    
    def set_language(self, language: VoiceLanguage) -> None:
        """Set voice language."""
        self.language = language
        self.logger.info(f"Voice language set to {language.value}")
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages."""
        return {lang.name: lang.value for lang in VoiceLanguage}
