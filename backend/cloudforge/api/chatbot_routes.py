"""
FastAPI routes for chatbot functionality.

Provides REST endpoints for:
- Chat sessions and messaging
- Voice assistant integration
- Command processing
- Conversation history
"""

from fastapi import APIRouter, HTTPException, status, Request, Depends, WebSocket
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

# Global instances
chatbot_engine: Optional[Any] = None
voice_assistant: Optional[Any] = None
command_processor: Optional[Any] = None


def get_chatbot_engine() -> Any:
    """Get chatbot engine instance."""
    global chatbot_engine
    if not chatbot_engine:
        from cloudforge.chatbot.chatbot_engine import ChatbotEngine
        config = {
            'bedrock_model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'max_retries': 3
        }
        chatbot_engine = ChatbotEngine(bedrock_client=None, config=config)
    return chatbot_engine


def get_voice_assistant() -> Any:
    """Get voice assistant instance."""
    global voice_assistant
    if not voice_assistant:
        from cloudforge.chatbot.voice_assistant import VoiceAssistant
        config = {'language': 'en-US', 'voice_id': 'Joanna'}
        voice_assistant = VoiceAssistant(polly_client=None, config=config)
    return voice_assistant


def get_command_processor() -> Any:
    """Get command processor instance."""
    global command_processor
    if not command_processor:
        from cloudforge.chatbot.command_processor import CommandProcessor
        command_processor = CommandProcessor(
            orchestrator=None,
            state_store=None,
            config={}
        )
    return command_processor


# ============================================================================
# Chat Session Endpoints
# ============================================================================

@router.post("/sessions", response_model=Dict[str, Any])
async def create_chat_session(
    workflow_id: Optional[str] = None,
    engine: Any = Depends(get_chatbot_engine)
) -> Dict[str, Any]:
    """Create a new chat session."""
    try:
        session = await engine.create_session(workflow_id=workflow_id)
        return {
            "session_id": session.session_id,
            "workflow_id": session.workflow_id,
            "created_at": session.created_at.isoformat(),
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(
    session_id: str,
    engine: Any = Depends(get_chatbot_engine)
) -> Dict[str, Any]:
    """Get chat session details."""
    session = engine.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return {
        "session_id": session.session_id,
        "workflow_id": session.workflow_id,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "message_count": len(session.messages),
        "status": "active"
    }


@router.delete("/sessions/{session_id}", response_model=Dict[str, Any])
async def delete_session(
    session_id: str,
    engine: Any = Depends(get_chatbot_engine)
) -> Dict[str, Any]:
    """Delete a chat session."""
    if engine.clear_session(session_id):
        return {"status": "deleted", "session_id": session_id}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )


# ============================================================================
# Chat Message Endpoints
# ============================================================================

@router.post("/sessions/{session_id}/messages", response_model=Dict[str, Any])
async def send_message(
    session_id: str,
    message: str,
    workflow_state: Optional[Dict[str, Any]] = None,
    engine: Any = Depends(get_chatbot_engine)
) -> Dict[str, Any]:
    """Send a message to the chatbot."""
    try:
        response = await engine.send_message(
            session_id=session_id,
            user_message=message,
            workflow_state=workflow_state
        )
        
        return {
            "message_id": response.message_id,
            "sender": response.sender,
            "content": response.content,
            "timestamp": response.timestamp.isoformat(),
            "status": "success"
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions/{session_id}/history", response_model=List[Dict[str, Any]])
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    engine: Any = Depends(get_chatbot_engine)
) -> List[Dict[str, Any]]:
    """Get chat history for a session."""
    history = engine.get_session_history(session_id)
    
    return [
        {
            "message_id": msg.message_id,
            "sender": msg.sender,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in history[-limit:]
    ]


# ============================================================================
# Command Endpoints
# ============================================================================

@router.post("/commands", response_model=Dict[str, Any])
async def execute_command(
    command: str,
    workflow_id: str,
    parameters: Optional[Dict[str, Any]] = None,
    processor: CommandProcessor = Depends(get_command_processor)
) -> Dict[str, Any]:
    """Execute a chatbot command."""
    try:
        result = await processor.process_command(
            command=command,
            workflow_id=workflow_id,
            parameters=parameters or {}
        )
        return result
    
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/commands", response_model=Dict[str, Any])
async def list_commands(
    processor: CommandProcessor = Depends(get_command_processor)
) -> Dict[str, Any]:
    """Get list of available commands."""
    return {
        "commands": processor.get_available_commands(),
        "help": "Use /chatbot/commands/{command} for command-specific help"
    }


# ============================================================================
# Voice Assistant Endpoints
# ============================================================================

@router.post("/voice/text-to-speech", response_model=Dict[str, Any])
async def text_to_speech(
    text: str,
    assistant: VoiceAssistant = Depends(get_voice_assistant)
) -> Dict[str, Any]:
    """Convert text to speech."""
    try:
        result = await assistant.text_to_speech(text)
        return result
    
    except Exception as e:
        logger.error(f"Error in text-to-speech: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/voice/speech-to-text", response_model=Dict[str, Any])
async def speech_to_text(
    audio_data: bytes,
    assistant: VoiceAssistant = Depends(get_voice_assistant)
) -> Dict[str, Any]:
    """Convert speech to text."""
    try:
        result = await assistant.speech_to_text(audio_data)
        return result
    
    except Exception as e:
        logger.error(f"Error in speech-to-text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/voice/commands", response_model=Dict[str, str])
async def get_voice_commands(
    assistant: VoiceAssistant = Depends(get_voice_assistant)
) -> Dict[str, str]:
    """Get available voice commands."""
    return assistant.get_voice_commands()


@router.post("/voice/parse-command", response_model=Dict[str, Any])
async def parse_voice_command(
    text: str,
    assistant: VoiceAssistant = Depends(get_voice_assistant)
) -> Dict[str, Any]:
    """Parse voice input to extract command."""
    return assistant.parse_voice_command(text)


@router.get("/voice/languages", response_model=Dict[str, str])
async def get_supported_languages(
    assistant: VoiceAssistant = Depends(get_voice_assistant)
) -> Dict[str, str]:
    """Get supported languages for voice assistant."""
    return assistant.get_supported_languages()


@router.post("/voice/set-language", response_model=Dict[str, Any])
async def set_voice_language(
    language: str,
    assistant: VoiceAssistant = Depends(get_voice_assistant)
) -> Dict[str, Any]:
    """Set voice language."""
    try:
        lang = VoiceLanguage(language)
        assistant.set_language(lang)
        return {
            "language": language,
            "status": "updated"
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {language}"
        )


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health", response_model=Dict[str, Any])
async def chatbot_health() -> Dict[str, Any]:
    """Check chatbot service health."""
    return {
        "service": "CloudForge Chatbot",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
