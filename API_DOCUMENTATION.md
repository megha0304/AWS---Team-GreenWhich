# CloudForge Bug Intelligence API Documentation

## Overview

The CloudForge Bug Intelligence API provides RESTful endpoints for managing bug detection workflows, retrieving results, and exporting data. The API is built with FastAPI and includes automatic OpenAPI documentation.

## Base URL

```
Development: http://localhost:8000
Production: https://api.cloudforge.example.com
```

## Authentication

All API requests require an API key passed in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8000/workflows
```

### Getting an API Key

API keys are configured in `backend/config.py` or via AWS Secrets Manager in production:

```python
# config.py
API_KEY = "your-secure-api-key"
```

For production, store in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name cloudforge/api-key \
  --secret-string '{"api_key":"your-secure-key"}'
```

## Rate Limiting

- **Limit**: 100 requests per minute per IP address
- **Headers**: Response includes rate limit information
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

### Rate Limit Exceeded Response

```json
{
  "error": "Rate limit exceeded",
  "detail": "100 per 1 minute"
}
```

**Status Code**: `429 Too Many Requests`

## Interactive Documentation

When the API is running, access interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Browse all endpoints
- View request/response schemas
- Test API calls directly from the browser
- Download OpenAPI specification

## Endpoints

### Health Check

#### GET /

Root endpoint for API health check.

**Request**:
```bash
curl http://localhost:8000/
```

**Response**:
```json
{
  "service": "CloudForge Bug Intelligence API",
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-02-19T10:30:00Z"
}
```

**Status Codes**:
- `200 OK`: API is healthy

---

#### GET /health

Dedicated health check endpoint.

**Request**:
```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-02-19T10:30:00Z"
}
```

**Status Codes**:
- `200 OK`: API is healthy

---

### Workflows

#### POST /workflows

Create a new bug detection workflow.

**Request**:
```bash
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "repository_url": "https://github.com/user/repo.git",
    "branch": "main",
    "scan_options": {
      "severity_filter": ["critical", "high"],
      "file_patterns": ["*.py", "*.js"],
      "exclude_patterns": ["tests/*", "*.test.js"]
    }
  }'
```

**Request Body**:
```json
{
  "repository_url": "string (required)",
  "branch": "string (optional, default: main)",
  "scan_options": {
    "severity_filter": ["critical", "high", "medium", "low"],
    "file_patterns": ["*.py", "*.js"],
    "exclude_patterns": ["tests/*"]
  }
}
```

**Response**:
```json
{
  "workflow_id": "wf-20240219103000",
  "status": "pending",
  "created_at": "2024-02-19T10:30:00Z",
  "updated_at": "2024-02-19T10:30:00Z",
  "repository_url": "https://github.com/user/repo.git",
  "bugs_found": 0,
  "tests_generated": 0,
  "tests_executed": 0,
  "root_causes_found": 0,
  "fixes_generated": 0
}
```

**Status Codes**:
- `201 Created`: Workflow created successfully
- `400 Bad Request`: Invalid request body
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Invalid API key
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

**Workflow Lifecycle**:
1. `pending`: Workflow created, waiting to start
2. `in_progress`: Workflow executing
3. `completed`: Workflow finished successfully
4. `failed`: Workflow encountered an error

---

#### GET /workflows/{workflow_id}

Get complete workflow status and results.

**Request**:
```bash
curl http://localhost:8000/workflows/wf-20240219103000 \
  -H "X-API-Key: your-api-key"
```

**Response**:
```json
{
  "workflow_id": "wf-20240219103000",
  "repository_url": "https://github.com/user/repo.git",
  "repository_path": "/tmp/repos/wf-20240219103000",
  "current_agent": "resolution",
  "status": "completed",
  "created_at": "2024-02-19T10:30:00Z",
  "updated_at": "2024-02-19T10:45:00Z",
  "bugs": [
    {
      "bug_id": "bug-001",
      "file_path": "src/main.py",
      "line_number": 42,
      "severity": "high",
      "description": "Potential null pointer dereference",
      "code_snippet": "def process(data):\n    return data.value  # data could be None",
      "detected_at": "2024-02-19T10:31:00Z"
    }
  ],
  "test_cases": [...],
  "test_results": [...],
  "root_causes": [...],
  "fix_suggestions": [...],
  "errors": []
}
```

**Status Codes**:
- `200 OK`: Workflow found
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Invalid API key
- `404 Not Found`: Workflow not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

#### GET /workflows

List workflows with optional filtering and pagination.

**Request**:
```bash
# List all workflows
curl http://localhost:8000/workflows \
  -H "X-API-Key: your-api-key"

# Filter by status
curl "http://localhost:8000/workflows?status_filter=completed" \
  -H "X-API-Key: your-api-key"

# Filter by severity
curl "http://localhost:8000/workflows?severity=critical" \
  -H "X-API-Key: your-api-key"

# Pagination
curl "http://localhost:8000/workflows?limit=10&offset=20" \
  -H "X-API-Key: your-api-key"

# Combined filters
curl "http://localhost:8000/workflows?status_filter=completed&severity=high&limit=25" \
  -H "X-API-Key: your-api-key"
```

**Query Parameters**:
- `status_filter` (optional): Filter by status (`pending`, `in_progress`, `completed`, `failed`)
- `severity` (optional): Filter by bug severity (`critical`, `high`, `medium`, `low`)
- `limit` (optional, default: 50): Maximum number of results to return
- `offset` (optional, default: 0): Number of results to skip

**Response**:
```json
{
  "workflows": [
    {
      "workflow_id": "wf-20240219103000",
      "status": "completed",
      "created_at": "2024-02-19T10:30:00Z",
      "updated_at": "2024-02-19T10:45:00Z",
      "repository_url": "https://github.com/user/repo.git",
      "bugs_found": 5,
      "tests_generated": 5,
      "tests_executed": 5,
      "root_causes_found": 3,
      "fixes_generated": 3
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

**Status Codes**:
- `200 OK`: Workflows retrieved successfully
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Invalid API key
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

### Bugs

#### GET /workflows/{workflow_id}/bugs

Get all bugs detected for a workflow.

**Request**:
```bash
curl http://localhost:8000/workflows/wf-20240219103000/bugs \
  -H "X-API-Key: your-api-key"
```

**Response**:
```json
[
  {
    "bug_id": "bug-001",
    "file_path": "src/main.py",
    "line_number": 42,
    "severity": "high",
    "description": "Potential null pointer dereference",
    "code_snippet": "def process(data):\n    return data.value  # data could be None",
    "detected_at": "2024-02-19T10:31:00Z"
  },
  {
    "bug_id": "bug-002",
    "file_path": "src/utils.py",
    "line_number": 15,
    "severity": "critical",
    "description": "SQL injection vulnerability",
    "code_snippet": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
    "detected_at": "2024-02-19T10:31:30Z"
  }
]
```

**Bug Severity Levels**:
- `critical`: Security vulnerabilities, data loss risks
- `high`: Crashes, major functionality issues
- `medium`: Performance issues, minor bugs
- `low`: Code quality, style issues

**Status Codes**:
- `200 OK`: Bugs retrieved successfully
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Invalid API key
- `404 Not Found`: Workflow not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

#### GET /workflows/{workflow_id}/bugs/export

Export bug reports in JSON or CSV format.

**Request**:
```bash
# Export as JSON
curl "http://localhost:8000/workflows/wf-20240219103000/bugs/export?format=json" \
  -H "X-API-Key: your-api-key" \
  -o bugs.json

# Export as CSV
curl "http://localhost:8000/workflows/wf-20240219103000/bugs/export?format=csv" \
  -H "X-API-Key: your-api-key" \
  -o bugs.csv
```

**Query Parameters**:
- `format` (optional, default: json): Export format (`json` or `csv`)

**Response** (JSON format):
```json
[
  {
    "bug_id": "bug-001",
    "file_path": "src/main.py",
    "line_number": 42,
    "severity": "high",
    "description": "Potential null pointer dereference",
    "code_snippet": "def process(data):\n    return data.value",
    "detected_at": "2024-02-19T10:31:00Z"
  }
]
```

**Response** (CSV format):
```csv
bug_id,file_path,line_number,severity,description,detected_at
bug-001,src/main.py,42,high,Potential null pointer dereference,2024-02-19T10:31:00Z
bug-002,src/utils.py,15,critical,SQL injection vulnerability,2024-02-19T10:31:30Z
```

**Status Codes**:
- `200 OK`: Export successful
- `400 Bad Request`: Invalid format parameter
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Invalid API key
- `404 Not Found`: Workflow not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

### Fixes

#### GET /workflows/{workflow_id}/fixes

Get all fix suggestions for a workflow.

**Request**:
```bash
curl http://localhost:8000/workflows/wf-20240219103000/fixes \
  -H "X-API-Key: your-api-key"
```

**Response**:
```json
[
  {
    "fix_id": "fix-001",
    "bug_id": "bug-001",
    "root_cause_id": "rc-001",
    "description": "Add null check before accessing data.value",
    "code_diff": "--- a/src/main.py\n+++ b/src/main.py\n@@ -40,2 +40,4 @@\n def process(data):\n+    if data is None:\n+        return None\n     return data.value",
    "file_path": "src/main.py",
    "safety_score": 0.95,
    "impact_score": 0.8,
    "generated_at": "2024-02-19T10:44:00Z"
  }
]
```

**Fix Fields**:
- `fix_id`: Unique identifier for the fix
- `bug_id`: Associated bug identifier
- `root_cause_id`: Associated root cause identifier
- `description`: Human-readable fix description
- `code_diff`: Unified diff format patch
- `file_path`: File to be modified
- `safety_score`: Confidence that fix won't introduce new bugs (0.0-1.0)
- `impact_score`: Estimated impact of the fix (0.0-1.0)
- `generated_at`: Timestamp when fix was generated

**Status Codes**:
- `200 OK`: Fixes retrieved successfully
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Invalid API key
- `404 Not Found`: Workflow not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

#### GET /workflows/{workflow_id}/fixes/export

Export fix suggestions in JSON or CSV format.

**Request**:
```bash
# Export as JSON
curl "http://localhost:8000/workflows/wf-20240219103000/fixes/export?format=json" \
  -H "X-API-Key: your-api-key" \
  -o fixes.json

# Export as CSV
curl "http://localhost:8000/workflows/wf-20240219103000/fixes/export?format=csv" \
  -H "X-API-Key: your-api-key" \
  -o fixes.csv
```

**Query Parameters**:
- `format` (optional, default: json): Export format (`json` or `csv`)

**Response** (JSON format):
```json
[
  {
    "fix_id": "fix-001",
    "bug_id": "bug-001",
    "root_cause_id": "rc-001",
    "description": "Add null check before accessing data.value",
    "code_diff": "...",
    "file_path": "src/main.py",
    "safety_score": 0.95,
    "impact_score": 0.8,
    "generated_at": "2024-02-19T10:44:00Z"
  }
]
```

**Response** (CSV format):
```csv
fix_id,bug_id,root_cause_id,description,file_path,safety_score,impact_score,generated_at
fix-001,bug-001,rc-001,Add null check before accessing data.value,src/main.py,0.95,0.8,2024-02-19T10:44:00Z
```

**Status Codes**:
- `200 OK`: Export successful
- `400 Bad Request`: Invalid format parameter
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Invalid API key
- `404 Not Found`: Workflow not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

#### GET /workflows/{workflow_id}/export

Export complete workflow summary in JSON format.

**Request**:
```bash
curl http://localhost:8000/workflows/wf-20240219103000/export \
  -H "X-API-Key: your-api-key" \
  -o workflow_complete.json
```

**Response**:
```json
{
  "workflow_id": "wf-20240219103000",
  "status": "completed",
  "created_at": "2024-02-19T10:30:00Z",
  "updated_at": "2024-02-19T10:45:00Z",
  "repository_url": "https://github.com/user/repo.git",
  "summary": {
    "bugs_found": 5,
    "tests_generated": 5,
    "tests_executed": 5,
    "root_causes_found": 3,
    "fixes_generated": 3,
    "errors_encountered": 0
  },
  "bugs": [...],
  "test_cases": [...],
  "test_results": [...],
  "root_causes": [...],
  "fix_suggestions": [...],
  "errors": []
}
```

**Status Codes**:
- `200 OK`: Export successful
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Invalid API key
- `404 Not Found`: Workflow not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "error": "Error Type",
  "detail": "Detailed error message"
}
```

### Common Error Codes

#### 400 Bad Request
Invalid request body or parameters.

```json
{
  "error": "Bad Request",
  "detail": "Invalid format: xyz. Must be 'json' or 'csv'"
}
```

#### 401 Unauthorized
Missing API key.

```json
{
  "error": "Unauthorized",
  "detail": "Missing API key"
}
```

#### 403 Forbidden
Invalid API key.

```json
{
  "error": "Forbidden",
  "detail": "Invalid API key"
}
```

#### 404 Not Found
Resource not found.

```json
{
  "error": "Not Found",
  "detail": "Workflow wf-123 not found"
}
```

#### 429 Too Many Requests
Rate limit exceeded.

```json
{
  "error": "Rate limit exceeded",
  "detail": "100 per 1 minute"
}
```

#### 500 Internal Server Error
Server error.

```json
{
  "error": "Internal Server Error",
  "detail": "An unexpected error occurred"
}
```

---

## Code Examples

### Python

```python
import requests

API_BASE = "http://localhost:8000"
API_KEY = "your-api-key"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Create workflow
response = requests.post(
    f"{API_BASE}/workflows",
    headers=headers,
    json={
        "repository_url": "https://github.com/user/repo.git",
        "branch": "main"
    }
)
workflow = response.json()
workflow_id = workflow["workflow_id"]

# Poll for completion
import time
while True:
    response = requests.get(
        f"{API_BASE}/workflows/{workflow_id}",
        headers=headers
    )
    status = response.json()["status"]
    
    if status in ["completed", "failed"]:
        break
    
    time.sleep(5)

# Get bugs
response = requests.get(
    f"{API_BASE}/workflows/{workflow_id}/bugs",
    headers=headers
)
bugs = response.json()

# Get fixes
response = requests.get(
    f"{API_BASE}/workflows/{workflow_id}/fixes",
    headers=headers
)
fixes = response.json()

# Export results
response = requests.get(
    f"{API_BASE}/workflows/{workflow_id}/export",
    headers=headers
)
with open("workflow_results.json", "w") as f:
    f.write(response.text)
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_BASE = 'http://localhost:8000';
const API_KEY = 'your-api-key';

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
};

async function runWorkflow() {
  // Create workflow
  const createResponse = await axios.post(
    `${API_BASE}/workflows`,
    {
      repository_url: 'https://github.com/user/repo.git',
      branch: 'main'
    },
    { headers }
  );
  
  const workflowId = createResponse.data.workflow_id;
  
  // Poll for completion
  let status = 'pending';
  while (status !== 'completed' && status !== 'failed') {
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    const statusResponse = await axios.get(
      `${API_BASE}/workflows/${workflowId}`,
      { headers }
    );
    
    status = statusResponse.data.status;
  }
  
  // Get bugs
  const bugsResponse = await axios.get(
    `${API_BASE}/workflows/${workflowId}/bugs`,
    { headers }
  );
  
  console.log('Bugs found:', bugsResponse.data.length);
  
  // Get fixes
  const fixesResponse = await axios.get(
    `${API_BASE}/workflows/${workflowId}/fixes`,
    { headers }
  );
  
  console.log('Fixes generated:', fixesResponse.data.length);
}

runWorkflow().catch(console.error);
```

### cURL

```bash
#!/bin/bash

API_BASE="http://localhost:8000"
API_KEY="your-api-key"

# Create workflow
WORKFLOW_ID=$(curl -s -X POST "$API_BASE/workflows" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/user/repo.git",
    "branch": "main"
  }' | jq -r '.workflow_id')

echo "Created workflow: $WORKFLOW_ID"

# Poll for completion
while true; do
  STATUS=$(curl -s "$API_BASE/workflows/$WORKFLOW_ID" \
    -H "X-API-Key: $API_KEY" | jq -r '.status')
  
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done

# Get bugs
curl -s "$API_BASE/workflows/$WORKFLOW_ID/bugs" \
  -H "X-API-Key: $API_KEY" | jq '.'

# Get fixes
curl -s "$API_BASE/workflows/$WORKFLOW_ID/fixes" \
  -H "X-API-Key: $API_KEY" | jq '.'

# Export complete workflow
curl -s "$API_BASE/workflows/$WORKFLOW_ID/export" \
  -H "X-API-Key: $API_KEY" \
  -o "workflow_$WORKFLOW_ID.json"
```

---

## Best Practices

### Polling for Workflow Completion

Workflows run asynchronously. Poll the workflow status endpoint with exponential backoff:

```python
import time

def wait_for_completion(workflow_id, max_wait=3600):
    """Wait for workflow to complete with exponential backoff."""
    delay = 5  # Start with 5 seconds
    max_delay = 60  # Cap at 60 seconds
    elapsed = 0
    
    while elapsed < max_wait:
        response = requests.get(
            f"{API_BASE}/workflows/{workflow_id}",
            headers=headers
        )
        status = response.json()["status"]
        
        if status in ["completed", "failed"]:
            return status
        
        time.sleep(delay)
        elapsed += delay
        delay = min(delay * 1.5, max_delay)  # Exponential backoff
    
    raise TimeoutError(f"Workflow {workflow_id} did not complete in {max_wait}s")
```

### Error Handling

Always handle API errors gracefully:

```python
try:
    response = requests.post(
        f"{API_BASE}/workflows",
        headers=headers,
        json=workflow_data
    )
    response.raise_for_status()  # Raise exception for 4xx/5xx
    workflow = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        # Rate limited - wait and retry
        time.sleep(60)
        # Retry logic here
    elif e.response.status_code == 401:
        # Invalid API key
        print("Authentication failed - check API key")
    else:
        # Other error
        print(f"API error: {e.response.json()}")
except requests.exceptions.RequestException as e:
    # Network error
    print(f"Network error: {e}")
```

### Rate Limit Handling

Respect rate limits by checking response headers:

```python
response = requests.get(f"{API_BASE}/workflows", headers=headers)

remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
reset_time = int(response.headers.get('X-RateLimit-Reset', 0))

if remaining < 10:
    # Approaching rate limit
    wait_time = reset_time - time.time()
    print(f"Approaching rate limit, waiting {wait_time}s")
    time.sleep(wait_time)
```

### Pagination

When listing workflows, use pagination for large result sets:

```python
def get_all_workflows():
    """Fetch all workflows using pagination."""
    all_workflows = []
    offset = 0
    limit = 50
    
    while True:
        response = requests.get(
            f"{API_BASE}/workflows",
            headers=headers,
            params={"limit": limit, "offset": offset}
        )
        data = response.json()
        
        all_workflows.extend(data["workflows"])
        
        if len(data["workflows"]) < limit:
            # Last page
            break
        
        offset += limit
    
    return all_workflows
```

---

## Changelog

### Version 1.0.0 (2024-02-19)
- Initial API release
- Workflow management endpoints
- Bug and fix retrieval endpoints
- Export functionality (JSON/CSV)
- Rate limiting and authentication
- OpenAPI documentation

---

## Support

For API issues or questions:
- **GitHub Issues**: https://github.com/cloudforge/bug-intelligence/issues
- **Email**: api-support@cloudforge.example.com
- **Documentation**: https://docs.cloudforge.example.com
