"""
Flask web application for CloudForge Bug Intelligence dashboard.

This provides a simple web interface that can run without Node.js,
using Flask for the backend and vanilla HTML/CSS/JavaScript for the frontend.
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from typing import Dict, List, Any
import logging

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
    
    workflow = {
        'workflow_id': workflow_id,
        'repository_url': data['repository_url'],
        'status': 'pending',
        'created_at': '2024-01-01T00:00:00Z',
        'bugs_found': 0,
        'tests_generated': 0,
        'current_agent': 'bug_detective'
    }
    
    workflows[workflow_id] = workflow
    
    logger.info(f"Created workflow {workflow_id} for {data['repository_url']}")
    
    return jsonify(workflow), 201


@app.route('/api/workflows/<workflow_id>', methods=['GET'])
def get_workflow(workflow_id: str):
    """Get workflow details by ID."""
    workflow = workflows.get(workflow_id)
    
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    
    return jsonify(workflow)


@app.route('/api/workflows/<workflow_id>/bugs', methods=['GET'])
def get_workflow_bugs(workflow_id: str):
    """Get all bugs for a workflow."""
    workflow = workflows.get(workflow_id)
    
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    
    # Demo data
    bugs = [
        {
            'bug_id': 'bug-1',
            'file_path': 'src/main.py',
            'line_number': 42,
            'severity': 'high',
            'description': 'Potential null pointer dereference',
            'confidence_score': 0.85
        }
    ]
    
    return jsonify({'bugs': bugs})


@app.route('/api/workflows/<workflow_id>/fixes', methods=['GET'])
def get_workflow_fixes(workflow_id: str):
    """Get all fix suggestions for a workflow."""
    workflow = workflows.get(workflow_id)
    
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    
    # Demo data
    fixes = [
        {
            'bug_id': 'bug-1',
            'fix_description': 'Add null check before dereferencing',
            'code_diff': '- obj.method()\n+ if obj is not None:\n+     obj.method()',
            'safety_score': 0.95,
            'impact_assessment': 'Low impact, safe to apply'
        }
    ]
    
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
