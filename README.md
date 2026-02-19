# CloudForge Bug Intelligence 🤖

**AI-Powered Bug Detection & Resolution Platform**

Automatically find bugs, generate tests, and suggest fixes using AWS Bedrock AI.

---

## 🎯 **NEW USER? START HERE** 👇

📖 **[NEXT_STEPS.md](NEXT_STEPS.md)** - What to do now (choose your path)
📘 **[AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)** - Complete setup guide (1-2 hours)
📊 **[SETUP_SUMMARY.md](SETUP_SUMMARY.md)** - Project status and overview

---

## ✨ What It Does

1. **🔍 Scans your code** - Finds bugs automatically using AI
2. **🧪 Generates tests** - Creates test cases for each bug
3. **▶️ Runs tests** - Executes tests on AWS infrastructure
4. **🔬 Analyzes results** - Identifies root causes
5. **💡 Suggests fixes** - Provides code patches to fix bugs

**All automatically, powered by AWS Bedrock (Claude AI).**

## 🚀 Quick Start

### Option 1: Complete Setup with Shareable Link (1-2 hours)

**Follow the comprehensive guide**: [`AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md`](AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)

This guide walks you through:
- ✅ Setting up AWS Bedrock (Claude AI)
- ✅ Implementing real Bedrock integration
- ✅ Deploying AWS infrastructure (DynamoDB, S3)
- ✅ Getting a permanent shareable link (Render.com)

**Result**: Production-ready platform with permanent URL like `https://cloudforge-bug-intelligence.onrender.com`

### Option 2: Quick Local Test (15 minutes)

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Configure AWS credentials
aws configure
# Enter: Access Key ID, Secret Key, Region (us-east-1)

# 3. Enable Bedrock access
# Go to: https://console.aws.amazon.com/bedrock
# Click: "Model access" → Request "Claude 3 Sonnet"

# 4. Create .env file
cat > .env <<EOF
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
EOF

# 5. Run locally
python -m uvicorn cloudforge.api.main:app --reload --port 8000
# Visit: http://localhost:8000/docs
```
4. Wait 30 seconds for approval

### Step 3: Run Locally (1 minute)

```bash
# Start the API
cd backend
python -m uvicorn cloudforge.api.main:app --reload

# In another terminal, start the dashboard
python run_web.py

# Open in browser
# API: http://localhost:8000/docs
# Dashboard: http://localhost:5000
```

**That's it!** 🎉 You're running locally.

## 🌐 Get a Shareable Link (30 Minutes)

Want a permanent link that works from anywhere? Deploy to the cloud!

### Option 1: Render.com (Easiest - Free)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Ready to deploy"
   git push origin main
   ```

2. **Deploy on Render**:
   - Go to https://render.com (sign up free)
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Click "Create Web Service"

3. **Add Environment Variables** in Render dashboard:
   ```
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
   ```

4. **Get Your Link**: `https://your-app.onrender.com`

**Share this link with anyone!** It's permanent and always accessible.

📖 **Detailed deployment guide**: See `SIMPLE_DEPLOYMENT.md`

## 📚 Documentation & Guides

### 🎯 Start Here
- **[AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)** - **⭐ RECOMMENDED** - Complete setup in 1-2 hours
  - Set up AWS Bedrock (Claude AI)
  - Implement real Bedrock integration
  - Deploy infrastructure (DynamoDB, S3)
  - Get permanent shareable link

### 📖 Additional Guides
- **[SIMPLE_DEPLOYMENT.md](SIMPLE_DEPLOYMENT.md)** - Quick deployment to Render/Railway/Fly.io (30 min)
- **[AWS_COMPLETE_SETUP_GUIDE.md](AWS_COMPLETE_SETUP_GUIDE.md)** - Detailed AWS setup (all services)
- **[GET_STARTED.md](GET_STARTED.md)** - Overview and quick start path
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Track your deployment progress
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference
- **[examples/](examples/)** - Example workflows and code samples

## Architecture

The system consists of three main layers:

### 1. Backend (Python 3.11+)
- **Agents**: Five specialized AI agents for bug lifecycle management
  - `Bug Detective Agent`: Scans code using AWS Bedrock (Claude) for bug patterns
  - `Test Architect Agent`: Generates test cases using Amazon Q Developer
  - `Execution Agent`: Routes tests to Lambda or ECS based on resource needs
  - `Analysis Agent`: Performs root cause analysis using AWS Bedrock
  - `Resolution Agent`: Generates fix suggestions using Amazon Q Developer
- **Orchestration**: LangGraph-based workflow state machine with state persistence
- **API**: FastAPI REST endpoints with rate limiting and authentication
- **Web Interface**: Flask-based dashboard (no Node.js required for UI!)
- **Location**: `backend/`

### 2. Infrastructure (AWS CDK with TypeScript)
Three CDK stacks for complete AWS infrastructure:
- **Core Infrastructure Stack**: DynamoDB tables (workflows, bugs), S3 buckets, IAM roles, Secrets Manager, KMS encryption
- **Compute Resources Stack**: Lambda functions, ECS cluster/tasks, VPC with public/private subnets
- **Monitoring Stack**: CloudWatch dashboards, alarms, SNS topics, metric filters
- **Deployment**: Blue-green deployment with CodeDeploy and automatic rollback
- **Location**: `infrastructure/`

### 3. Data Flow
```
Code Repository → Bug Detective → Test Architect → Execution Agent → Analysis Agent → Resolution Agent
                       ↓              ↓                  ↓                ↓                ↓
                   DynamoDB ←────────────────── State Persistence ──────────────────→ S3
```

### AWS Services Used
- **AWS Bedrock**: AI-powered bug detection and root cause analysis
- **Amazon Q Developer**: Test generation and fix suggestions
- **AWS Lambda**: Short-running test execution (<15min, <10GB)
- **AWS ECS**: Long-running test execution (>15min or >10GB)
- **DynamoDB**: Workflow state persistence with GSIs for querying
- **S3**: Test results and artifact storage with lifecycle policies
- **CloudWatch**: Logging, metrics, dashboards, and alarms
- **Secrets Manager**: Secure API credential storage
- **KMS**: Encryption key management
- **SNS**: Critical error notifications

## Prerequisites

### Required
- **Python 3.11+**: Backend runtime
- **AWS CLI**: Configured with appropriate credentials (`aws configure`)
- **AWS Account**: With permissions for:
  - Lambda, ECS, DynamoDB, S3
  - AWS Bedrock (Claude models)
  - Amazon Q Developer API
  - CloudWatch, Secrets Manager, KMS, SNS
  - IAM role creation

### Optional
- **Node.js 18+**: Only needed for AWS CDK infrastructure deployment
- **Docker**: For local development with LocalStack
- **Git**: For repository scanning features

### AWS Bedrock Setup
AWS Bedrock requires model access to be enabled in your AWS account:
1. Navigate to AWS Bedrock console
2. Go to "Model access" in the left sidebar
3. Request access to "Anthropic Claude 3 Sonnet" model
4. Wait for approval (usually instant for most accounts)

See `backend/AWS_BEDROCK_SETUP.md` for detailed setup instructions.

## Quick Start

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd cloudforge-bug-intelligence

# Install Python dependencies
cd backend
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

```bash
# Configure AWS CLI (if not already done)
aws configure

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### 3. Set Up Configuration

```bash
# Copy example configuration
cd backend
cp config.example.py config.py

# Edit config.py with your settings:
# - AWS region
# - Bedrock model ID
# - Amazon Q Developer endpoint (if available)
# - Cost thresholds
```

### 4. Run the Web Dashboard

```bash
# From backend directory
python run_web.py
```

Open your browser to **http://localhost:5000**

### 5. (Optional) Run the REST API

```bash
# From backend directory
python -m uvicorn cloudforge.api.main:app --reload --port 8000
```

API documentation available at **http://localhost:8000/docs**

### 6. (Optional) Run Tests

```bash
# Run all tests
python -m pytest tests/unit/ -v

# Run property-based tests only
python -m pytest tests/property/ -v

# Run with coverage
python -m pytest tests/ --cov=cloudforge --cov-report=html
```

That's it! The system works in mock mode when AWS credentials are not fully configured.

## Configuration

### Configuration Files

The system uses multiple configuration sources with the following precedence:
1. Environment variables (highest priority)
2. `backend/config.py` (application configuration)
3. AWS Secrets Manager (for production credentials)
4. Default values in `backend/cloudforge/models/config.py`

### API Keys and Credentials

Create `backend/config.py` based on `backend/config.example.py`:

```python
# AWS Configuration
AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
Q_DEVELOPER_ENDPOINT = "https://your-q-endpoint.amazonaws.com"

# Cost Management
COST_BUDGET_USD = 100.0
COST_ALERT_THRESHOLD = 0.8  # Alert at 80% of budget

# Agent Configuration
MAX_RETRIES = 3
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 60

# API Configuration
API_RATE_LIMIT = "100/minute"
API_KEY = "your-api-key-here"  # For API authentication
```

### Environment Variables

Alternatively, use environment variables (recommended for production):

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
export Q_DEVELOPER_ENDPOINT=https://your-q-endpoint.amazonaws.com

# Secrets (use AWS Secrets Manager in production)
export API_KEY=your-api-key-here

# Optional: DynamoDB and S3 configuration
export DYNAMODB_TABLE_WORKFLOWS=cloudforge-workflows
export DYNAMODB_TABLE_BUGS=cloudforge-bugs
export S3_BUCKET_ARTIFACTS=cloudforge-artifacts
```

### AWS Secrets Manager (Production)

For production deployments, store sensitive credentials in AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name cloudforge/api-credentials \
  --secret-string '{"api_key":"your-key","q_endpoint":"https://..."}'

# The application will automatically load from Secrets Manager
```

### Mock Mode

The system supports mock mode for development without AWS credentials:
- Set `MOCK_MODE=true` in environment or config
- Agents will return simulated responses
- No AWS API calls will be made
- Useful for UI development and testing

See `backend/REQUIRED_INPUTS.md` for detailed input requirements and `backend/AWS_BEDROCK_SETUP.md` for Bedrock configuration.

## Project Structure

```
cloudforge-bug-intelligence/
├── backend/                           # Python backend (3.11+)
│   ├── cloudforge/
│   │   ├── agents/                   # AI agents
│   │   │   ├── bug_detective.py     # Bug detection with Bedrock
│   │   │   ├── test_architect.py    # Test generation with Q Developer
│   │   │   ├── execution.py         # Test execution on Lambda/ECS
│   │   │   ├── analysis.py          # Root cause analysis with Bedrock
│   │   │   └── resolution.py        # Fix generation with Q Developer
│   │   ├── orchestration/           # LangGraph workflow
│   │   │   ├── workflow_orchestrator.py  # Main orchestrator
│   │   │   └── state_store.py       # DynamoDB state persistence
│   │   ├── api/                     # FastAPI REST endpoints
│   │   │   └── main.py              # API routes and authentication
│   │   ├── models/                  # Pydantic data models
│   │   │   ├── state.py             # AgentState and workflow models
│   │   │   └── config.py            # Configuration models
│   │   ├── web/                     # Flask web dashboard
│   │   │   ├── templates/           # HTML templates (Jinja2)
│   │   │   ├── static/              # CSS/JS assets
│   │   │   └── app.py               # Flask application
│   │   ├── utils/                   # Utilities and helpers
│   │   │   ├── retry.py             # Exponential backoff
│   │   │   ├── circuit_breaker.py   # Circuit breaker pattern
│   │   │   ├── logging_config.py    # Structured logging
│   │   │   ├── metrics.py           # CloudWatch metrics
│   │   │   ├── notifications.py     # SNS notifications
│   │   │   ├── s3_storage.py        # S3 artifact storage
│   │   │   └── export.py            # Data export (JSON/CSV)
│   │   └── main.py                  # Application entry point
│   ├── tests/                       # Test suite
│   │   ├── unit/                    # Unit tests
│   │   └── property/                # Property-based tests (Hypothesis)
│   ├── requirements.txt             # Python dependencies
│   ├── run_web.py                   # Run web dashboard
│   ├── config.example.py            # Example configuration
│   ├── AWS_BEDROCK_SETUP.md         # Bedrock setup guide
│   └── REQUIRED_INPUTS.md           # Input requirements
├── infrastructure/                   # AWS CDK (TypeScript)
│   ├── lib/                         # CDK stack definitions
│   │   ├── cloudforge-infrastructure-stack.ts  # Core infrastructure
│   │   ├── cloudforge-compute-stack.ts         # Lambda/ECS resources
│   │   └── cloudforge-monitoring-stack.ts      # CloudWatch/SNS
│   ├── bin/
│   │   └── cloudforge-infrastructure.ts        # CDK app entry point
│   ├── test/                        # Infrastructure tests
│   ├── package.json                 # Node dependencies
│   └── cdk.json                     # CDK configuration
├── scripts/                         # Deployment scripts
│   ├── deploy-infrastructure.sh     # Linux/Mac deployment
│   └── deploy-infrastructure.ps1    # Windows deployment
├── .kiro/specs/                     # Specification documents
│   └── cloudforge-bug-intelligence/
│       ├── requirements.md          # Requirements specification
│       ├── design.md                # Design document
│       └── tasks.md                 # Implementation tasks
├── DEPLOYMENT.md                    # Deployment guide
├── PROJECT_STRUCTURE.md             # Detailed structure docs
├── SETUP.md                         # Setup instructions
├── Makefile                         # Build automation
└── README.md                        # This file
```

## Usage

### Starting a Bug Detection Workflow

#### Via Web Dashboard

1. Open http://localhost:5000
2. Click "New Workflow"
3. Enter repository path or URL
4. Configure scan options (severity filters, file patterns)
5. Click "Start Workflow"
6. Monitor progress in real-time

#### Via REST API

```bash
# Create a new workflow
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "repository_path": "/path/to/code",
    "scan_options": {
      "severity_filter": ["critical", "high"],
      "file_patterns": ["*.py", "*.js"]
    }
  }'

# Get workflow status
curl http://localhost:8000/workflows/{workflow_id} \
  -H "X-API-Key: your-api-key"

# Get detected bugs
curl http://localhost:8000/workflows/{workflow_id}/bugs \
  -H "X-API-Key: your-api-key"

# Get fix suggestions
curl http://localhost:8000/workflows/{workflow_id}/fixes \
  -H "X-API-Key: your-api-key"
```

#### Via Python SDK

```python
from cloudforge.orchestration.workflow_orchestrator import WorkflowOrchestrator
from cloudforge.models.state import AgentState

# Initialize orchestrator
orchestrator = WorkflowOrchestrator()

# Create workflow state
state = AgentState(
    workflow_id="workflow-123",
    repository_path="/path/to/code",
    current_agent="bug_detective"
)

# Execute workflow
result = await orchestrator.execute_workflow(state)

# Access results
print(f"Bugs found: {len(result.bug_reports)}")
print(f"Tests generated: {len(result.test_cases)}")
print(f"Fixes suggested: {len(result.fix_suggestions)}")
```

### Workflow Stages

1. **Bug Detection** (Bug Detective Agent)
   - Scans all source files in repository
   - Uses AWS Bedrock (Claude) for semantic analysis
   - Classifies bugs by severity
   - Generates structured bug reports

2. **Test Generation** (Test Architect Agent)
   - Creates test cases for each detected bug
   - Uses Amazon Q Developer for language-appropriate tests
   - Includes positive and negative scenarios
   - Outputs executable test code

3. **Test Execution** (Execution Agent)
   - Routes to Lambda (<15min, <10GB) or ECS (larger)
   - Captures stdout, stderr, exit codes
   - Stores results in DynamoDB
   - Handles infrastructure failover

4. **Root Cause Analysis** (Analysis Agent)
   - Processes all test outputs
   - Uses AWS Bedrock for causal analysis
   - Groups related bugs
   - Provides confidence scores

5. **Fix Generation** (Resolution Agent)
   - Generates code patches for root causes
   - Uses Amazon Q Developer
   - Ranks fixes by safety and impact
   - Outputs unified diffs

### Filtering and Querying

```bash
# Filter workflows by status
curl "http://localhost:8000/workflows?status=completed" \
  -H "X-API-Key: your-api-key"

# Filter by date range
curl "http://localhost:8000/workflows?start_date=2024-01-01&end_date=2024-12-31" \
  -H "X-API-Key: your-api-key"

# Filter by severity
curl "http://localhost:8000/workflows/{workflow_id}/bugs?severity=critical" \
  -H "X-API-Key: your-api-key"

# Export results
curl "http://localhost:8000/workflows/{workflow_id}/export?format=json" \
  -H "X-API-Key: your-api-key" > results.json

curl "http://localhost:8000/workflows/{workflow_id}/export?format=csv" \
  -H "X-API-Key: your-api-key" > results.csv
```

## Development

### Running Tests

```bash
# Backend unit tests
cd backend
python -m pytest tests/unit/ -v

# Property-based tests (Hypothesis)
python -m pytest tests/property/ -v

# Run all tests with coverage
python -m pytest tests/ --cov=cloudforge --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_bug_detective.py -v

# Run tests matching pattern
python -m pytest tests/ -k "test_retry" -v

# Infrastructure tests (requires Node.js)
cd infrastructure
npm test
```

### Local Development with LocalStack

LocalStack provides local AWS service emulation for development:

```bash
# Start LocalStack with required services
docker-compose up -d

# Configure local endpoints
export AWS_ENDPOINT_URL=http://localhost:4566
export DYNAMODB_ENDPOINT=http://localhost:4566
export S3_ENDPOINT=http://localhost:4566

# Run backend with local AWS
cd backend
python -m uvicorn cloudforge.api.main:app --reload
```

### Mock Mode for Development

Develop without AWS credentials using mock mode:

```python
# In config.py or environment
MOCK_MODE = True

# Agents will return simulated responses
# No AWS API calls will be made
# Useful for UI development and testing
```

### Code Quality Tools

```bash
# Format code with black
black backend/cloudforge backend/tests

# Lint with ruff
ruff check backend/cloudforge backend/tests

# Type checking with mypy
mypy backend/cloudforge

# Run pre-commit hooks
pre-commit run --all-files
```

### Development Workflow

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes with tests
3. Run tests: `pytest tests/`
4. Check code quality: `ruff check .`
5. Commit changes: `git commit -m "Add feature"`
6. Push and create PR: `git push origin feature/my-feature`

## Deployment

### Production Deployment

See `DEPLOYMENT.md` for comprehensive deployment guide.

#### Quick Deployment Steps

```bash
# 1. Install AWS CDK (if not already installed)
npm install -g aws-cdk

# 2. Bootstrap CDK (first time only)
cd infrastructure
cdk bootstrap

# 3. Install dependencies
npm install

# 4. Build TypeScript
npm run build

# 5. Deploy infrastructure (all stacks)
cdk deploy --all --require-approval never

# 6. Deploy backend API to Lambda
cd ../backend
# Package and deploy using AWS SAM or Serverless Framework
# See DEPLOYMENT.md for detailed instructions

# 7. Configure environment variables in Lambda
aws lambda update-function-configuration \
  --function-name cloudforge-api \
  --environment Variables="{AWS_REGION=us-east-1,BEDROCK_MODEL_ID=...}"
```

#### Deployment Scripts

Use provided scripts for automated deployment:

```bash
# Linux/Mac
./scripts/deploy-infrastructure.sh

# Windows PowerShell
.\scripts\deploy-infrastructure.ps1
```

### Blue-Green Deployment

The infrastructure supports zero-downtime deployments:

```bash
# Deploy with canary strategy (10% traffic for 5 minutes)
cd infrastructure
cdk deploy CloudForgeComputeStack

# Automatic rollback on errors
# Manual rollback if needed:
aws deploy stop-deployment \
  --deployment-id <deployment-id> \
  --auto-rollback-enabled
```

### Infrastructure Stacks

Three CDK stacks are deployed in sequence:

1. **CloudForgeInfrastructureStack**: Core resources (DynamoDB, S3, IAM, Secrets Manager)
2. **CloudForgeComputeStack**: Compute resources (Lambda, ECS, VPC)
3. **CloudForgeMonitoringStack**: Observability (CloudWatch, SNS, alarms)

### Cost Estimation

Estimated monthly costs for demonstration environment:
- **DynamoDB**: $5-10 (on-demand pricing)
- **S3**: $1-5 (with lifecycle policies)
- **Lambda**: $10-20 (based on execution time)
- **ECS**: $20-30 (Fargate spot instances)
- **Bedrock**: $20-30 (Claude API calls)
- **CloudWatch**: $5-10 (logs and metrics)
- **Total**: ~$60-100/month

Production costs scale with usage. See `DEPLOYMENT.md` for cost optimization strategies.

## API Documentation

### Interactive Documentation

Once the backend is running, access interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

#### Workflows

```
POST   /workflows              Create new workflow
GET    /workflows              List all workflows (with filters)
GET    /workflows/{id}         Get workflow details
DELETE /workflows/{id}         Delete workflow
```

#### Bugs

```
GET    /workflows/{id}/bugs    List bugs for workflow
GET    /bugs/{bug_id}          Get bug details
```

#### Fixes

```
GET    /workflows/{id}/fixes   List fix suggestions
GET    /fixes/{fix_id}         Get fix details
```

#### Export

```
GET    /workflows/{id}/export  Export results (JSON/CSV)
```

### Authentication

All API requests require an API key:

```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8000/workflows
```

### Rate Limiting

- **Limit**: 100 requests per minute per API key
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Exceeded**: Returns 429 status code

### Request/Response Examples

See `API_EXAMPLES.md` (to be created in Task 23.2) for detailed examples.

## Monitoring and Observability

### CloudWatch Dashboards

Access pre-configured dashboards in AWS CloudWatch:
- **Workflow Metrics**: Success rates, execution times, active workflows
- **Agent Performance**: Individual agent metrics and bottlenecks
- **Cost Tracking**: API call counts, compute usage, budget status
- **Error Rates**: Failures by agent, retry counts, circuit breaker states

### Logs

Structured JSON logs in CloudWatch Logs:
```json
{
  "timestamp": "2024-02-19T10:30:00Z",
  "workflow_id": "wf-123",
  "agent_name": "bug_detective",
  "action": "scan_file",
  "status": "success",
  "duration_ms": 1250,
  "context": {
    "file_path": "src/main.py",
    "bugs_found": 3
  }
}
```

### Metrics

Custom CloudWatch metrics published:
- `AgentExecutionTime`: Time taken by each agent
- `AgentSuccessRate`: Success/failure ratio per agent
- `WorkflowDuration`: End-to-end workflow time
- `BugsDetected`: Count of bugs by severity
- `TestExecutionCost`: Estimated cost per test run
- `CircuitBreakerState`: Open/closed state per service

### Alarms

Pre-configured CloudWatch alarms:
- **High Error Rate**: >5% failures in 5 minutes
- **Cost Threshold**: 80% of monthly budget reached
- **Long Execution**: Workflow exceeds 30 minutes
- **Circuit Breaker Open**: External service unavailable

### Notifications

SNS topics for critical events:
- Workflow failures
- Agent crashes
- Cost threshold alerts
- Security events

Subscribe to topics:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:cloudforge-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Testing Strategy

The project uses a comprehensive testing approach:

### Unit Tests
- Specific examples and edge cases
- Mock external dependencies
- Fast execution (<1 second per test)
- Located in `backend/tests/unit/`

### Property-Based Tests (Hypothesis)
- Universal properties across randomized inputs
- Validates correctness properties from design spec
- Discovers edge cases automatically
- Located in `backend/tests/property/`

### Integration Tests
- End-to-end workflow validation
- Real AWS service integration (with LocalStack)
- State persistence and recovery
- Located in `backend/tests/integration/`

### Test Coverage
- Target: >80% code coverage
- Current: ~85% (338/340 tests passing)
- Run: `pytest --cov=cloudforge --cov-report=html`

All design properties from `.kiro/specs/cloudforge-bug-intelligence/design.md` have corresponding property tests.

## Security

### IAM Policies
- Least privilege access for all resources
- Separate roles for each agent and service
- No wildcard permissions in production

### Encryption
- **At Rest**: All DynamoDB tables and S3 buckets encrypted with KMS
- **In Transit**: TLS 1.2+ for all API calls and data transfer
- **Secrets**: API keys stored in AWS Secrets Manager

### Network Security
- ECS tasks run in private subnets with NAT gateway
- Security groups restrict traffic to required ports only
- VPC isolation for sensitive code processing

### Data Protection
- Sensitive data sanitization in logs
- No API keys or credentials logged
- Automatic data retention policies (90 days)

### Compliance
- CloudTrail logging for audit trails
- AWS Config for compliance monitoring
- Regular security scanning with AWS Inspector

## Troubleshooting

### Common Issues

#### "Bedrock model not accessible"
```bash
# Check model access in AWS console
aws bedrock list-foundation-models --region us-east-1

# Request access if needed (see AWS_BEDROCK_SETUP.md)
```

#### "DynamoDB table not found"
```bash
# Verify tables exist
aws dynamodb list-tables

# Deploy infrastructure if missing
cd infrastructure && cdk deploy CloudForgeInfrastructureStack
```

#### "Lambda timeout on large repositories"
```bash
# System should auto-route to ECS for large jobs
# Check execution agent logs:
aws logs tail /aws/lambda/cloudforge-execution --follow
```

#### "Tests failing with 'No module named cloudforge'"
```bash
# Install in development mode
cd backend
pip install -e .
```

### Debug Mode

Enable verbose logging:
```python
# In config.py
LOG_LEVEL = "DEBUG"

# Or via environment
export LOG_LEVEL=DEBUG
```

### Getting Help

1. Check logs in CloudWatch: `/aws/lambda/cloudforge-*`
2. Review metrics in CloudWatch dashboards
3. Check SNS notifications for alerts
4. See `DEPLOYMENT.md` for deployment issues
5. Open GitHub issue with logs and error details

## Performance Optimization

### Cost Optimization
- Use S3 lifecycle policies to archive old results
- Enable DynamoDB auto-scaling for variable workloads
- Use Lambda for short tasks, ECS Spot for long tasks
- Implement caching for repeated API calls

### Speed Optimization
- Batch file scanning for large repositories
- Parallel test execution where possible
- Use DynamoDB GSIs for fast queries
- Enable CloudFront for web dashboard (optional)

### Resource Optimization
- Configure Lambda memory based on actual usage
- Use ECS task auto-scaling for peak loads
- Implement circuit breakers to fail fast
- Set appropriate timeouts for all operations

## Roadmap

### Current Version (v1.0)
- ✅ Five-agent bug lifecycle automation
- ✅ AWS Bedrock and Q Developer integration
- ✅ Lambda/ECS test execution
- ✅ Flask web dashboard
- ✅ FastAPI REST API
- ✅ Property-based testing
- ✅ CloudWatch monitoring

### Planned Features (v1.1)
- [ ] React web dashboard (enhanced UI)
- [ ] GitHub/GitLab integration
- [ ] Slack/Teams notifications
- [ ] Custom agent plugins
- [ ] Multi-repository scanning
- [ ] Historical trend analysis

### Future Enhancements (v2.0)
- [ ] Machine learning for bug prediction
- [ ] Automated fix deployment
- [ ] Integration with CI/CD pipelines
- [ ] Support for additional languages
- [ ] Enterprise SSO integration
- [ ] Advanced cost analytics

## Contributing

We welcome contributions! Please follow these guidelines:

### Getting Started
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Set up development environment (see Development section)
4. Make your changes with tests

### Code Standards
- Follow PEP 8 for Python code
- Use type hints for all functions
- Write docstrings for public APIs
- Add unit tests for new features
- Add property tests for correctness properties
- Ensure all tests pass: `pytest tests/`

### Pull Request Process
1. Update documentation for new features
2. Add tests covering your changes
3. Ensure code passes linting: `ruff check .`
4. Update CHANGELOG.md with your changes
5. Submit PR with clear description
6. Address review feedback

### Reporting Issues
- Use GitHub Issues for bug reports
- Include reproduction steps
- Attach relevant logs and error messages
- Specify environment (OS, Python version, AWS region)

## License

MIT License

Copyright (c) 2024 CloudForge Bug Intelligence

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Acknowledgments

- **AWS Bedrock**: AI-powered bug detection and analysis
- **Amazon Q Developer**: Test generation and fix suggestions
- **LangGraph**: Multi-agent orchestration framework
- **Hypothesis**: Property-based testing library
- **FastAPI**: Modern Python web framework
- **Flask**: Lightweight web interface

## Support and Contact

### Documentation
- **Setup Guide**: `SETUP.md`
- **Deployment Guide**: `DEPLOYMENT.md`
- **Project Structure**: `PROJECT_STRUCTURE.md`
- **API Examples**: See `/docs` endpoint when running
- **Specification**: `.kiro/specs/cloudforge-bug-intelligence/`

### Getting Help
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Email**: support@cloudforge.example.com (update with actual contact)
- **Documentation**: https://docs.cloudforge.example.com (update with actual URL)

### Community
- **Slack**: Join our community workspace (link TBD)
- **Twitter**: @CloudForgeDev (update with actual handle)
- **Blog**: https://blog.cloudforge.example.com (update with actual URL)

---

**Built with ❤️ for developers who want to spend less time debugging and more time building.**
