"""
CloudForge Chatbot Module - AI-powered assistant for bug analysis and resolution.

Provides conversational interface with voice support for:
- Bug analysis and explanation
- Fix suggestions and recommendations
- Workflow management and rollback
- Real-time assistance
"""

# NOTE: Imports are deferred to avoid circular dependencies and blocking on module load.
# Use lazy imports in functions that need these classes.

__all__ = ["ChatbotEngine", "VoiceAssistant", "CommandProcessor"]
