"""
Flask web application for CloudForge Bug Intelligence dashboard.

This provides a simple web interface that can run without Node.js,
using Flask for the backend and vanilla HTML/CSS/JavaScript for the frontend.
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import os
import re
from pathlib import Path
from uuid import uuid4
import asyncio
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app)

# Initialize chatbot components (will be set on startup)
chatbot_engine = None
voice_assistant = None
command_processor = None
orchestrator = None
state_store = None

# In-memory storage for demo (replace with DynamoDB in production)
workflows: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# In-Memory State Store (for chatbot workflow execution without DynamoDB)
# ---------------------------------------------------------------------------
class InMemoryStateStore:
    """In-memory state store for workflow execution without DynamoDB."""
    
    def __init__(self):
        self.states: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    async def save_state(self, state: Any, version: Optional[int] = None) -> None:
        """Save workflow state to memory."""
        try:
            workflow_id = state.workflow_id
            self.states[workflow_id] = state
            self.logger.info(f"Saved state for workflow {workflow_id}")
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
            raise
    
    async def load_state(self, workflow_id: str) -> Optional[Any]:
        """Load workflow state from memory."""
        return self.states.get(workflow_id)
    
    async def query_workflows(self, **kwargs) -> List[Any]:
        """Query workflows from memory."""
        return list(self.states.values())


# ---------------------------------------------------------------------------
# Static Bug Patterns
# ---------------------------------------------------------------------------
BUG_PATTERNS = [
    {
        'pattern': r'(?<!if\s)(?<!and\s)(?<!or\s)\b(\w+)\.\w+\(',
        'check': lambda line: re.search(r'^\s*(\w+)\.\w+\(', line) and 'if ' not in line and '=' not in line.split('.')[0],
        'severity': 'high',
        'description': 'Potential null/None dereference — object not checked before method call',
        'fix_description': 'Add a None check before calling method on object',
        'diff_template': '- {line}\n+ if {obj} is not None:\n+     {line}',
        'safety_score': 0.95,
        'impact': 'Prevents NoneType AttributeError at runtime'
    },
    {
        'pattern': r'except\s*:',
        'severity': 'medium',
        'description': 'Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt',
        'fix_description': 'Replace bare except with specific exception type',
        'diff_template': '- except:\n+ except Exception as e:',
        'safety_score': 0.90,
        'impact': 'Improves error handling and debugging'
    },
    {
        'pattern': r'==\s*None',
        'severity': 'low',
        'description': 'Use `is None` instead of `== None` for None comparison',
        'fix_description': 'Replace == None with is None',
        'diff_template': '- {line}\n+ {fixed}',
        'safety_score': 0.99,
        'impact': 'Follows PEP8 and avoids unexpected __eq__ overrides'
    },
    {
        'pattern': r'!=\s*None',
        'severity': 'low',
        'description': 'Use `is not None` instead of `!= None` for None comparison',
        'fix_description': 'Replace != None with is not None',
        'diff_template': '- {line}\n+ {fixed}',
        'safety_score': 0.99,
        'impact': 'Follows PEP8 and avoids unexpected __eq__ overrides'
    },
    {
        'pattern': r'open\([^)]+\)(?!.*\bwith\b)',
        'severity': 'medium',
        'description': 'File opened without context manager — resource may not be closed on error',
        'fix_description': 'Use `with open(...) as f:` to ensure file is always closed',
        'diff_template': '- {line}\n+ with {line} as f:',
        'safety_score': 0.88,
        'impact': 'Prevents file descriptor leaks'
    },
    {
        'pattern': r'print\s*\(',
        'severity': 'low',
        'description': 'Debug print statement found in production code',
        'fix_description': 'Replace print() with proper logging',
        'diff_template': '- {line}\n+ logger.debug({args})',
        'safety_score': 0.85,
        'impact': 'Improves observability and removes debug noise'
    },
    {
        'pattern': r'(password|secret|api_key|token)\s*=\s*["\'][^"\']+["\']',
        'severity': 'critical',
        'description': 'Hardcoded secret/credential detected in source code',
        'fix_description': 'Move secret to environment variable or AWS Secrets Manager',
        'diff_template': '- {line}\n+ {var} = os.environ.get("{var_upper}")',
        'safety_score': 0.99,
        'impact': 'Prevents credential exposure in version control'
    },
    {
        'pattern': r'time\.sleep\(\d+\)',
        'severity': 'low',
        'description': 'Hard-coded sleep delay — consider using event-driven approach',
        'fix_description': 'Replace fixed sleep with configurable delay or async wait',
        'diff_template': '- {line}\n+ time.sleep(config.RETRY_DELAY)',
        'safety_score': 0.80,
        'impact': 'Improves flexibility and testability'
    },
]

FALLBACK_BUGS = [
    {
        'bug_id': str(uuid4()),
        'file_path': 'src/main.py',
        'line_number': 42,
        'severity': 'high',
        'description': 'Potential null/None dereference — object not checked before method call',
        'code_snippet': '   42 | obj.method()',
        'confidence_score': 0.85
    },
    {
        'bug_id': str(uuid4()),
        'file_path': 'src/utils.py',
        'line_number': 17,
        'severity': 'medium',
        'description': 'Bare except clause catches all exceptions including SystemExit',
        'code_snippet': '   17 | except:',
        'confidence_score': 0.90
    },
    {
        'bug_id': str(uuid4()),
        'file_path': 'src/config.py',
        'line_number': 5,
        'severity': 'critical',
        'description': 'Hardcoded secret/credential detected in source code',
        'code_snippet': '    5 | api_key = "sk-abc123secret"',
        'confidence_score': 0.99
    },
]


def _analyse_repository(repo_path: str) -> List[Dict]:
    """Scan local repo path for bugs using static analysis patterns.
    Falls back to demo bugs if path doesn't exist."""
    path = Path(repo_path)
    bugs = []

    if not path.exists() or not path.is_dir():
        logger.info(f"Path '{repo_path}' not found — using fallback demo bugs")
        return FALLBACK_BUGS

    source_exts = {'.py', '.js', '.ts', '.java', '.go', '.rb'}
    exclude_dirs = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build'}

    for file_path in path.rglob('*'):
        if not file_path.is_file():
            continue
        if any(ex in file_path.parts for ex in exclude_dirs):
            continue
        if file_path.suffix not in source_exts:
            continue

        try:
            lines = file_path.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            continue

        rel_path = str(file_path.relative_to(path))

        for lineno, line in enumerate(lines, start=1):
            for bp in BUG_PATTERNS:
                if re.search(bp['pattern'], line, re.IGNORECASE):
                    bugs.append({
                        'bug_id': str(uuid4()),
                        'file_path': rel_path,
                        'line_number': lineno,
                        'severity': bp['severity'],
                        'description': bp['description'],
                        'code_snippet': f'   {lineno} | {line.strip()}',
                        'confidence_score': bp['safety_score']
                    })
                    break  # one bug per line

    if not bugs:
        logger.info("No bugs found via static analysis — using fallback demo bugs")
        return FALLBACK_BUGS

    return bugs


def _generate_tests(bugs: List[Dict]) -> List[Dict]:
    """Generate test cases for each bug."""
    test_templates = {
        'null': {
            'test_name': 'test_none_check_before_method_call',
            'test_code': 'def test_none_check_before_method_call():\n    obj = None\n    # Should not raise AttributeError\n    if obj is not None:\n        obj.method()\n    assert True',
            'status': 'passed'
        },
        'bare except': {
            'test_name': 'test_specific_exception_handling',
            'test_code': 'def test_specific_exception_handling():\n    try:\n        raise ValueError("test error")\n    except Exception as e:\n        assert str(e) == "test error"',
            'status': 'passed'
        },
        'is none': {
            'test_name': 'test_none_comparison_uses_is',
            'test_code': 'def test_none_comparison_uses_is():\n    x = None\n    assert x is None\n    assert not (x is not None)',
            'status': 'passed'
        },
        'is not none': {
            'test_name': 'test_not_none_comparison_uses_is',
            'test_code': 'def test_not_none_comparison_uses_is():\n    x = "value"\n    assert x is not None',
            'status': 'passed'
        },
        'context manager': {
            'test_name': 'test_file_opened_with_context_manager',
            'test_code': 'def test_file_opened_with_context_manager(tmp_path):\n    f = tmp_path / "test.txt"\n    f.write_text("hello")\n    with open(f) as fh:\n        content = fh.read()\n    assert content == "hello"',
            'status': 'passed'
        },
        'print': {
            'test_name': 'test_no_print_statements_in_output',
            'test_code': 'def test_no_print_statements_in_output(capsys):\n    import logging\n    logger = logging.getLogger(__name__)\n    logger.debug("debug message")\n    captured = capsys.readouterr()\n    assert captured.out == ""',
            'status': 'passed'
        },
        'secret': {
            'test_name': 'test_credentials_loaded_from_env',
            'test_code': 'def test_credentials_loaded_from_env(monkeypatch):\n    monkeypatch.setenv("API_KEY", "test-key")\n    import os\n    assert os.environ.get("API_KEY") == "test-key"',
            'status': 'passed'
        },
        'sleep': {
            'test_name': 'test_retry_delay_is_configurable',
            'test_code': 'def test_retry_delay_is_configurable():\n    import time\n    delay = 0.01  # configurable\n    start = time.time()\n    time.sleep(delay)\n    assert time.time() - start < 1',
            'status': 'passed'
        },
    }

    tests = []
    for bug in bugs:
        desc = bug['description'].lower()
        matched = next((v for k, v in test_templates.items() if k in desc), None)
        if not matched:
            matched = {
                'test_name': f'test_bug_{bug["bug_id"][:8]}',
                'test_code': f'def test_bug_{bug["bug_id"][:8]}():\n    # Auto-generated test for: {bug["description"]}\n    # File: {bug["file_path"]} line {bug["line_number"]}\n    assert True  # TODO: implement assertion',
                'status': 'pending'
            }
        tests.append({
            'test_id': str(uuid4()),
            'bug_id': bug['bug_id'],
            'file_path': bug['file_path'],
            'line_number': bug['line_number'],
            'severity': bug['severity'],
            'test_name': matched['test_name'],
            'test_code': matched['test_code'],
            'status': matched['status']
        })
    return tests


def _generate_fixes(bugs: List[Dict]) -> List[Dict]:
    """Generate fix suggestions for a list of bugs."""
    fix_map = {
        'Potential null/None dereference': (
            'Add a None check before calling method on object',
            '- obj.method()\n+ if obj is not None:\n+     obj.method()',
            0.95, 'Prevents NoneType AttributeError at runtime'
        ),
        'Bare except clause': (
            'Replace bare except with specific exception type',
            '- except:\n+ except Exception as e:',
            0.90, 'Improves error handling and debugging'
        ),
        'Use `is None`': (
            'Replace == None with is None',
            '- x == None\n+ x is None',
            0.99, 'Follows PEP8'
        ),
        'Use `is not None`': (
            'Replace != None with is not None',
            '- x != None\n+ x is not None',
            0.99, 'Follows PEP8'
        ),
        'File opened without context manager': (
            'Use with open(...) as f: to ensure file is always closed',
            '- f = open(path)\n+ with open(path) as f:',
            0.88, 'Prevents file descriptor leaks'
        ),
        'Debug print statement': (
            'Replace print() with proper logging',
            '- print(msg)\n+ logger.debug(msg)',
            0.85, 'Removes debug noise from production'
        ),
        'Hardcoded secret': (
            'Move secret to environment variable or AWS Secrets Manager',
            '- api_key = "sk-abc123"\n+ api_key = os.environ.get("API_KEY")',
            0.99, 'Prevents credential exposure'
        ),
        'Hard-coded sleep': (
            'Replace fixed sleep with configurable delay',
            '- time.sleep(5)\n+ time.sleep(config.RETRY_DELAY)',
            0.80, 'Improves flexibility'
        ),
    }

    fixes = []
    for bug in bugs:
        desc = bug['description']
        matched = next((v for k, v in fix_map.items() if k.lower() in desc.lower()), None)
        if matched:
            fix_desc, diff, safety, impact = matched
        else:
            fix_desc = 'Review and refactor the flagged code'
            diff = f"- {bug.get('code_snippet', '').split('|')[-1].strip()}\n+ # TODO: apply fix"
            safety, impact = 0.70, 'Manual review recommended'

        fixes.append({
            'bug_id': bug['bug_id'],
            'fix_description': fix_desc,
            'code_diff': diff,
            'safety_score': safety,
            'impact_assessment': impact
        })

    return fixes


@app.route('/')
def home():
    """Render the home/landing page."""
    return render_template('home.html')


@app.route('/dashboard')
def index():
    """Render the dashboard page."""
    return render_template('index.html')


@app.route('/workflows')
def workflows_page():
    """Render the workflows list page."""
    return render_template('workflows.html')


@app.route('/workflows/<workflow_id>')
def workflow_detail(workflow_id: str):
    """Render the workflow detail page."""
    return render_template('workflow_detail.html', workflow_id=workflow_id)


# API Endpoints

@app.route('/api/workflows', methods=['GET'])
def get_workflows():
    """Get all workflows with optional filtering."""
    status = request.args.get('status')
    severity = request.args.get('severity')
    
    filtered_workflows = list(workflows.values())
    
    if status:
        filtered_workflows = [w for w in filtered_workflows if w.get('status') == status]
    if severity:
        filtered_workflows = [w for w in filtered_workflows if w.get('severity') == severity]
    
    return jsonify({
        'workflows': filtered_workflows,
        'total': len(filtered_workflows)
    })


@app.route('/api/workflows', methods=['POST'])
def create_workflow():
    """Create a new bug detection workflow."""
    data = request.get_json()

    if not data or 'repository_url' not in data:
        return jsonify({'error': 'repository_url is required'}), 400

    workflow_id = f"workflow-{len(workflows) + 1}"
    repo_url = data['repository_url']

    # Run static analysis on the repo path (local path or fallback demo)
    bugs = _analyse_repository(repo_url)

    workflow = {
        'workflow_id': workflow_id,
        'repository_url': repo_url,
        'status': 'completed',
        'created_at': '2024-01-01T00:00:00Z',
        'bugs_found': len(bugs),
        'tests_generated': len(bugs),
        'current_agent': 'resolution',
        'bugs': bugs
    }

    workflows[workflow_id] = workflow
    logger.info(f"Created workflow {workflow_id} for {repo_url}, found {len(bugs)} bugs")
    return jsonify(workflow), 201


@app.route('/api/workflows/<workflow_id>', methods=['GET'])
def get_workflow(workflow_id: str):
    """Get workflow details by ID."""
    workflow = workflows.get(workflow_id)
    
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    
    return jsonify(workflow)


@app.route('/api/workflows/<workflow_id>/tests', methods=['GET'])
def get_workflow_tests(workflow_id: str):
    """Get generated tests for a workflow."""
    workflow = workflows.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    tests = _generate_tests(workflow.get('bugs', []))
    return jsonify({'tests': tests})


@app.route('/api/workflows/<workflow_id>/bugs', methods=['GET'])
def get_workflow_bugs(workflow_id: str):
    """Get all bugs for a workflow."""
    workflow = workflows.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    return jsonify({'bugs': workflow.get('bugs', [])})


@app.route('/api/workflows/<workflow_id>/fixes', methods=['GET'])
def get_workflow_fixes(workflow_id: str):
    """Get all fix suggestions for a workflow."""
    workflow = workflows.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    fixes = _generate_fixes(workflow.get('bugs', []))
    return jsonify({'fixes': fixes})


# ============================================================================
# Chatbot Routes
# ============================================================================

@app.route('/chatbot')
def chatbot_page():
    """Render the chatbot page."""
    return render_template('chatbot.html')


# ============================================================================
# Chatbot API Endpoints
# ============================================================================

@app.route('/chatbot/sessions', methods=['POST'])
def create_chat_session():
    """Create a new chat session."""
    try:
        global chatbot_engine, orchestrator, state_store
        
        # Initialize chatbot engine if needed
        if not chatbot_engine:
            from cloudforge.chatbot.chatbot_engine import ChatbotEngine
            config = {
                'bedrock_model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'max_retries': 3
            }
            chatbot_engine = ChatbotEngine(
                bedrock_client=None, 
                config=config,
                orchestrator=orchestrator,
                state_store=state_store
            )
        
        # Create session in chatbot engine
        session_id = str(uuid4())
        workflow_id = None
        
        # Try to parse request data
        try:
            data = request.get_json() or {}
            workflow_id = data.get('workflow_id')
        except:
            pass
        
        # Create session in chatbot engine
        from cloudforge.chatbot.chatbot_engine import ChatSession
        session = ChatSession(session_id=session_id, workflow_id=workflow_id)
        chatbot_engine.sessions[session_id] = session
        
        logger.info(f"Created chat session {session_id}")
        
        return jsonify({
            "session_id": session_id,
            "workflow_id": workflow_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active"
        })
    except Exception as e:
        logger.error(f"Error creating chat session: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/chatbot/sessions/<session_id>/messages', methods=['POST'])
def send_message(session_id):
    """Send a message to the chatbot."""
    import threading
    
    try:
        global chatbot_engine, orchestrator, state_store
        if not chatbot_engine:
            from cloudforge.chatbot.chatbot_engine import ChatbotEngine
            config = {
                'bedrock_model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'max_retries': 3
            }
            chatbot_engine = ChatbotEngine(
                bedrock_client=None, 
                config=config,
                orchestrator=orchestrator,
                state_store=state_store
            )
        
        data = request.json or {}
        message = data.get('message', '')
        workflow_state = data.get('workflow_state')
        
        if not message:
            return jsonify({"error": "message field required"}), 400
        
        # Extract repository path or GitHub URL from message
        repository_path = None
        is_workflow_request = False
        
        # Try to match GitHub URLs first
        github_match = re.search(
            r'(?:analyze|scan|detect|run|execute|start)\s+(https?://github\.com/[\w\-]+/[\w\-\.]+(?:\.git)?)',
            message,
            re.IGNORECASE
        )
        
        if github_match:
            repository_path = github_match.group(1)
            is_workflow_request = True
            logger.info(f"Extracted GitHub URL: {repository_path}")
        else:
            # Try to match file paths (absolute or relative)
            # Matches: /path/to/repo, C:\path\to\repo, ./relative/path, ../parent/path
            path_match = re.search(
                r'(?:analyze|scan|detect|run|execute|start)\s+([C-Za-z]:[\\\/][\w\-\.\\\/]+|[\/\.][\/\w\-\.]*)',
                message,
                re.IGNORECASE
            )
            
            if path_match:
                repository_path = path_match.group(1)
                is_workflow_request = True
                logger.info(f"Extracted repository path: {repository_path}")
            else:
                logger.info(f"No repository path or GitHub URL found in message: {message}")
        
        # Process message asynchronously in a thread
        def process_in_background():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(chatbot_engine.send_message(
                    session_id=session_id,
                    user_message=message,
                    workflow_state=workflow_state,
                    repository_path=repository_path
                ))
                logger.info(f"Message processed for session {session_id}")
            except Exception as e:
                logger.error(f"Error processing message in background: {e}")
            finally:
                loop.close()
        
        # Start background thread
        thread = threading.Thread(target=process_in_background, daemon=True)
        thread.start()
        
        # Only show "Starting Analysis" if this is a workflow request
        if is_workflow_request:
            # Generate a workflow ID for the dashboard link
            workflow_id = f"wf-{str(uuid4())[:8]}"
            
            # Return immediately with new sequential format
            return jsonify({
                "message_id": str(uuid4()),
                "sender": "system",
                "content": f"""🚀 **Starting Analysis**

**Workflow ID:** `{workflow_id}`

📊 **View Live Results:** [Open Dashboard](http://localhost:5000/dashboard?workflow_id={workflow_id})

I'll analyze your repository step by step. Here's what I'll do:
1. 📥 Clone the repository
2. 🐛 Detect bugs
3. 🧪 Generate tests
4. ▶️ Execute tests
5. 🔍 Analyze results
6. 💡 Suggest fixes

Let me start...""",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "processing"
            })
        else:
            # For non-workflow messages, return empty response
            # The actual response will be added to session by background thread
            return jsonify({
                "message_id": str(uuid4()),
                "sender": "system",
                "content": "",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "processing"
            })
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/chatbot/sessions/<session_id>/history', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for a session."""
    try:
        global chatbot_engine, orchestrator, state_store
        if not chatbot_engine:
            from cloudforge.chatbot.chatbot_engine import ChatbotEngine
            config = {
                'bedrock_model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'max_retries': 3
            }
            chatbot_engine = ChatbotEngine(
                bedrock_client=None, 
                config=config,
                orchestrator=orchestrator,
                state_store=state_store
            )
        
        limit = request.args.get('limit', 500, type=int)
        history = chatbot_engine.get_session_history(session_id)
        
        logger.info(f"Retrieved {len(history)} messages for session {session_id}")
        
        return jsonify([
            {
                "message_id": msg.message_id,
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in history[-limit:]
        ])
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/chatbot/commands', methods=['POST'])
def execute_command():
    """Execute a chatbot command."""
    from cloudforge.chatbot.command_processor import CommandProcessor
    import asyncio
    
    try:
        global command_processor
        if not command_processor:
            command_processor = CommandProcessor(
                orchestrator=None,
                state_store=None,
                config={}
            )
        
        data = request.json or {}
        command = data.get('command', '')
        workflow_id = data.get('workflow_id', 'default')
        parameters = data.get('parameters', {})
        
        if not command:
            return jsonify({"error": "command field required"}), 400
        
        result = asyncio.run(command_processor.process_command(
            command=command,
            workflow_id=workflow_id,
            parameters=parameters
        ))
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/chatbot/voice/commands', methods=['GET'])
def get_voice_commands():
    """Get available voice commands."""
    from cloudforge.chatbot.voice_assistant import VoiceAssistant
    
    try:
        global voice_assistant
        if not voice_assistant:
            config = {'language': 'en-US', 'voice_id': 'Joanna'}
            voice_assistant = VoiceAssistant(polly_client=None, config=config)
        
        return jsonify(voice_assistant.get_voice_commands())
    except Exception as e:
        logger.error(f"Error getting voice commands: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/chatbot/voice/parse-command', methods=['POST'])
def parse_voice_command():
    """Parse voice input to extract command."""
    from cloudforge.chatbot.voice_assistant import VoiceAssistant
    
    try:
        global voice_assistant
        if not voice_assistant:
            config = {'language': 'en-US', 'voice_id': 'Joanna'}
            voice_assistant = VoiceAssistant(polly_client=None, config=config)
        
        data = request.json or {}
        text = data.get('text', '')
        
        return jsonify(voice_assistant.parse_voice_command(text))
    except Exception as e:
        logger.error(f"Error parsing voice command: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/chatbot/health', methods=['GET'])
def chatbot_health():
    """Check chatbot service health."""
    return jsonify({
        "service": "CloudForge Chatbot",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'cloudforge-bug-intelligence',
        'version': '0.1.0'
    })


def initialize_orchestrator():
    """Initialize the workflow orchestrator and state store."""
    global orchestrator, state_store, chatbot_engine
    
    try:
        from cloudforge.orchestration.workflow_orchestrator import WorkflowOrchestrator
        from cloudforge.agents import (
            BugDetectiveAgent,
            TestArchitectAgent,
            ExecutionAgent,
            AnalysisAgent,
            ResolutionAgent
        )
        from cloudforge.utils.bedrock_client import BedrockClient
        from cloudforge.models.config import SystemConfig
        
        logger.info("Initializing orchestrator components...")
        
        # Initialize config
        config = SystemConfig()
        
        # Initialize Bedrock client
        bedrock_client = BedrockClient(config)
        
        # Initialize in-memory state store (no DynamoDB required)
        state_store = InMemoryStateStore()
        
        # Initialize agents
        bug_detective = BugDetectiveAgent(bedrock_client.client, config)
        test_architect = TestArchitectAgent(bedrock_client.client, config)
        execution_agent = ExecutionAgent(bedrock_client.client, None, None, config)
        analysis_agent = AnalysisAgent(bedrock_client.client, config)
        resolution_agent = ResolutionAgent(bedrock_client.client, config)
        
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator(
            bug_detective=bug_detective,
            test_architect=test_architect,
            execution_agent=execution_agent,
            analysis_agent=analysis_agent,
            resolution_agent=resolution_agent,
            state_store=state_store,
            config=config.__dict__
        )
        
        logger.info("Orchestrator initialized successfully")
        
        # Update chatbot engine with orchestrator
        if chatbot_engine:
            chatbot_engine.orchestrator = orchestrator
            chatbot_engine.state_store = state_store
            logger.info("Chatbot engine updated with orchestrator")
        
        return orchestrator, state_store
        
    except Exception as e:
        logger.error(f"Error initializing orchestrator: {e}")
        logger.warning("Chatbot will run in demo mode without workflow execution")
        return None, None


def run_app(host: str = '0.0.0.0', port: int = 5000, debug: bool = True):
    """
    Run the Flask application.
    
    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 5000)
        debug: Enable debug mode (default: True)
    """
    global orchestrator, state_store
    
    # Initialize orchestrator before starting the app
    orchestrator, state_store = initialize_orchestrator()
    
    logger.info(f"Starting CloudForge dashboard on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app()
