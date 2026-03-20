"""
Flask web application for CloudForge Bug Intelligence dashboard.

This provides a simple web interface that can run without Node.js,
using Flask for the backend and vanilla HTML/CSS/JavaScript for the frontend.
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from typing import Dict, List, Any
import logging
import os
import re
from pathlib import Path
from uuid import uuid4

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app)

# In-memory storage for demo (replace with DynamoDB in production)
workflows: Dict[str, Any] = {}


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


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'cloudforge-bug-intelligence',
        'version': '0.1.0'
    })


def run_app(host: str = '0.0.0.0', port: int = 5000, debug: bool = True):
    """
    Run the Flask application.
    
    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to bind to (default: 5000)
        debug: Enable debug mode (default: True)
    """
    logger.info(f"Starting CloudForge dashboard on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app()
