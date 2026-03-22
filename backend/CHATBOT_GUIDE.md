# CloudForge Chatbot - User Guide

## Overview

The CloudForge Chatbot is an AI-powered assistant that helps you analyze bugs, suggest fixes, manage workflows, and interact with the bug intelligence system using natural language and voice commands.

## Features

### 🤖 Conversational AI
- **Natural Language Understanding**: Ask questions about bugs in plain English
- **Context-Aware Responses**: Chatbot understands your workflow context
- **Multi-turn Conversations**: Maintain conversation history for better context
- **Intelligent Suggestions**: Get personalized recommendations based on your bugs

### 🎤 Voice Assistant
- **Speech-to-Text**: Speak commands and questions (uses browser Web Speech API)
- **Text-to-Speech**: Listen to responses (uses AWS Polly or browser TTS)
- **Voice Commands**: Quick commands like "analyze", "suggest", "status"
- **Multi-language Support**: English, Spanish, French, German, Chinese, Japanese

### ⚡ Quick Commands
- **analyze**: Analyze a specific bug
- **suggest**: Get fix suggestions
- **rollback**: Rollback changes
- **status**: Check workflow status
- **list**: List bugs or fixes
- **export**: Export results
- **filter**: Filter bugs by criteria
- **compare**: Compare bugs or fixes
- **apply**: Apply a fix
- **help**: Show available commands

## Getting Started

### 1. Access the Chatbot

Open your browser and navigate to:
```
http://localhost:5000/chatbot
```

### 2. Create a Session

A new chat session is automatically created when you load the page. You can:
- Start a new session anytime using the "New Session" button
- Associate the session with a workflow by entering the Workflow ID

### 3. Send Your First Message

Type a message in the input field and press Enter or click Send:
```
"What bugs were detected?"
"Analyze the critical bugs"
"Suggest fixes for the null pointer issue"
```

## Using Voice Commands

### Enable Voice Input

1. Click the 🎤 microphone button
2. Allow browser microphone access when prompted
3. Speak your command or question
4. The chatbot will transcribe and respond

### Available Voice Commands

| Command | Examples |
|---------|----------|
| **analyze** | "analyze", "what is", "explain", "tell me about" |
| **suggest** | "suggest", "fix", "how to fix", "what should i do" |
| **rollback** | "rollback", "undo", "revert", "go back" |
| **status** | "status", "how is it", "what's happening", "progress" |
| **list** | "list", "show all", "what bugs", "all bugs" |
| **export** | "export", "save", "download", "get results" |
| **help** | "help", "what can you do", "commands", "options" |
| **next** | "next", "go to next", "skip", "move on" |
| **previous** | "previous", "go back", "last one" |
| **details** | "details", "more info", "tell me more" |
| **confirm** | "yes", "confirm", "proceed", "go ahead" |
| **cancel** | "no", "cancel", "stop", "abort" |

### Voice Settings

- **Language**: Select your preferred language for voice input/output
- **Auto-speak**: Enable automatic text-to-speech for responses

## Command Examples

### Analyze a Bug

**Text Command:**
```
analyze bug_id=abc123
```

**Voice Command:**
```
"Analyze the critical bug"
```

**Response:**
```
Bug ID: abc123
File: src/main.py
Line: 42
Severity: high
Description: Potential null/None dereference
Confidence: 0.85
```

### Get Fix Suggestions

**Text Command:**
```
suggest bug_id=abc123 limit=3
```

**Voice Command:**
```
"Suggest a fix for this bug"
```

**Response:**
```
Fix 1: Add None check before method call
Safety Score: 0.95
Impact: Prevents NoneType AttributeError

Fix 2: Use optional chaining
Safety Score: 0.88
Impact: More Pythonic approach
```

### Check Workflow Status

**Text Command:**
```
status
```

**Voice Command:**
```
"What's the status?"
```

**Response:**
```
Workflow ID: wf-12345
Status: completed
Bugs Found: 15
Fixes Suggested: 12
Tests Generated: 15
Root Causes: 8
```

### List Bugs

**Text Command:**
```
list type=bugs limit=10
```

**Voice Command:**
```
"Show all bugs"
```

**Response:**
```
1. src/main.py:42 - high - Null dereference
2. src/utils.py:17 - medium - Bare except
3. src/config.py:5 - critical - Hardcoded secret
...
```

### Filter Bugs

**Text Command:**
```
filter severity=critical min_confidence=0.8
```

**Voice Command:**
```
"Show critical bugs"
```

**Response:**
```
Filtered Results: 3 bugs
1. src/config.py:5 - Hardcoded secret (0.99)
2. src/auth.py:23 - SQL injection (0.92)
3. src/api.py:45 - Command injection (0.88)
```

### Export Results

**Text Command:**
```
export format=json
```

**Voice Command:**
```
"Export the results"
```

**Response:**
```
Export to json initiated
Use /api/workflows/{workflow_id}/export endpoint
```

## Workflow Context

The chatbot can work with your current workflow. To enable context:

1. Enter your **Workflow ID** in the "Workflow Context" section
2. The chatbot will use this context for all commands
3. You'll see real-time updates of:
   - Workflow Status
   - Bugs Found
   - Fixes Suggested

## API Integration

### REST API Endpoints

#### Create Chat Session
```bash
POST /chatbot/sessions
Headers: X-API-Key: your-api-key

Response:
{
  "session_id": "uuid",
  "workflow_id": null,
  "created_at": "2024-02-19T10:30:00Z",
  "status": "active"
}
```

#### Send Message
```bash
POST /chatbot/sessions/{session_id}/messages
Headers: X-API-Key: your-api-key
Body: {
  "message": "What bugs were found?",
  "workflow_state": {"workflow_id": "wf-123"}
}

Response:
{
  "message_id": "uuid",
  "sender": "assistant",
  "content": "I found 15 bugs in your workflow...",
  "timestamp": "2024-02-19T10:30:05Z",
  "status": "success"
}
```

#### Get Chat History
```bash
GET /chatbot/sessions/{session_id}/history?limit=50
Headers: X-API-Key: your-api-key

Response:
[
  {
    "message_id": "uuid",
    "sender": "user",
    "content": "What bugs were found?",
    "timestamp": "2024-02-19T10:30:00Z"
  },
  {
    "message_id": "uuid",
    "sender": "assistant",
    "content": "I found 15 bugs...",
    "timestamp": "2024-02-19T10:30:05Z"
  }
]
```

#### Execute Command
```bash
POST /chatbot/commands
Headers: X-API-Key: your-api-key
Body: {
  "command": "analyze",
  "workflow_id": "wf-123",
  "parameters": {"bug_id": "bug-456"}
}

Response:
{
  "command": "analyze",
  "bug_id": "bug-456",
  "file_path": "src/main.py",
  "line_number": 42,
  "severity": "high",
  "description": "Potential null/None dereference",
  "status": "success"
}
```

#### Text-to-Speech
```bash
POST /chatbot/voice/text-to-speech
Headers: X-API-Key: your-api-key
Body: {"text": "Hello, this is a test"}

Response:
{
  "method": "polly",
  "audio_data": "<base64-encoded-audio>",
  "format": "mp3",
  "voice_id": "Joanna",
  "language": "en-US"
}
```

#### Parse Voice Command
```bash
POST /chatbot/voice/parse-command
Headers: X-API-Key: your-api-key
Body: {"text": "analyze the critical bug"}

Response:
{
  "command": "analyze",
  "original_text": "analyze the critical bug",
  "confidence": 0.9
}
```

### WebSocket for Real-time Chat

Connect to WebSocket for bidirectional communication:

```javascript
const ws = new WebSocket('ws://localhost:8000/chatbot/ws/session-id');

ws.onopen = () => {
  ws.send(JSON.stringify({
    message: "What bugs were found?",
    workflow_state: {workflow_id: "wf-123"}
  }));
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log(response.content);
};
```

## Advanced Features

### Multi-language Support

Change voice language:
1. Select language from "Voice Settings" dropdown
2. Voice input/output will use selected language
3. Supported: English, Spanish, French, German, Chinese, Japanese

### Auto-speak Responses

Enable automatic text-to-speech:
1. Check "Auto-speak responses" in Voice Settings
2. All chatbot responses will be spoken aloud
3. Adjust browser volume as needed

### Session Management

- **New Session**: Start fresh conversation
- **Clear History**: Remove all messages from current session
- **Session ID**: Unique identifier for conversation tracking

### Conversation Context

The chatbot maintains context across messages:
- Remembers previous bugs discussed
- Understands references like "this bug" or "that fix"
- Provides relevant suggestions based on history

## Troubleshooting

### Voice Input Not Working

1. **Check browser support**: Voice recognition requires Chrome, Edge, or Safari
2. **Allow microphone**: Grant microphone permission when prompted
3. **Check microphone**: Ensure microphone is working in browser settings
4. **Try again**: Click microphone button and speak clearly

### No Response from Chatbot

1. **Check API key**: Ensure X-API-Key header is set correctly
2. **Check workflow ID**: Verify workflow exists if using context
3. **Check logs**: Review browser console for errors
4. **Restart session**: Create a new session

### Audio Playback Issues

1. **Check volume**: Ensure browser volume is not muted
2. **Check speakers**: Test speakers with other audio
3. **Disable auto-speak**: Uncheck "Auto-speak responses"
4. **Try browser TTS**: System will fallback to browser text-to-speech

### Commands Not Recognized

1. **Check syntax**: Ensure command format is correct
2. **Check parameters**: Verify all required parameters are provided
3. **Check workflow**: Ensure workflow ID is valid
4. **Try help**: Use "help" command to see available commands

## Best Practices

### For Text Commands

1. **Be specific**: "analyze bug_id=abc123" instead of "analyze"
2. **Use parameters**: Include limit, severity, confidence filters
3. **Reference context**: Mention workflow ID for better results
4. **Ask follow-ups**: Build on previous responses

### For Voice Commands

1. **Speak clearly**: Enunciate words clearly for better recognition
2. **Use short phrases**: Keep commands concise
3. **Wait for response**: Let chatbot finish before speaking again
4. **Confirm actions**: Say "confirm" before applying fixes

### For Workflow Management

1. **Set workflow context**: Enter workflow ID at start
2. **Monitor status**: Check status regularly
3. **Review fixes**: Analyze suggested fixes before applying
4. **Export results**: Save results for documentation

## Security

### API Key Management

- Store API keys securely (environment variables, secrets manager)
- Never share API keys in code or version control
- Rotate keys regularly
- Use different keys for different environments

### Data Privacy

- Chat history is stored in session memory
- Clear sessions when done
- Don't share sensitive information in chat
- Use secure connections (HTTPS/WSS)

### Voice Data

- Voice input is processed locally by browser
- Text-to-speech uses AWS Polly (encrypted in transit)
- No voice recordings are stored
- Audio data is not logged

## Performance Tips

1. **Limit history**: Keep chat history under 100 messages
2. **Use filters**: Filter bugs before analysis for faster results
3. **Batch commands**: Group related commands together
4. **Clear sessions**: Remove old sessions to free memory

## Support

For issues or questions:
1. Check this guide for troubleshooting
2. Review API documentation
3. Check browser console for errors
4. Contact support with session ID and error details

## Examples

### Complete Workflow

```
1. User: "Create new session"
   Chatbot: Session created (id: abc123)

2. User: "Set workflow to wf-456"
   Chatbot: Workflow context set

3. User: "What bugs were found?"
   Chatbot: Found 15 bugs (3 critical, 5 high, 7 medium)

4. User: "Show critical bugs"
   Chatbot: [Lists 3 critical bugs]

5. User: "Analyze the first one"
   Chatbot: [Detailed analysis of first bug]

6. User: "Suggest fixes"
   Chatbot: [Lists 3 fix suggestions with safety scores]

7. User: "Apply the safest fix"
   Chatbot: Fix application initiated (requires confirmation)

8. User: "Export results"
   Chatbot: Export initiated (JSON format)
```

### Voice-Only Workflow

```
1. User: "Hey, analyze"
   Chatbot: "Which bug would you like me to analyze?"

2. User: "The critical one"
   Chatbot: [Speaks analysis]

3. User: "Suggest a fix"
   Chatbot: [Speaks fix suggestions]

4. User: "Apply it"
   Chatbot: "Fix application requires confirmation. Say confirm to proceed."

5. User: "Confirm"
   Chatbot: "Fix applied successfully"
```

---

**Happy bug hunting! 🐛🔍**
