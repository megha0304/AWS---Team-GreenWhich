# CloudForge Bug Intelligence

An AWS-native multi-agent platform that automates the complete bug lifecycle from detection through resolution.

## Overview

CloudForge Bug Intelligence employs five specialized AI agents orchestrated through LangGraph to:
- **Detect** bugs in code repositories using AI-powered pattern recognition
- **Generate** comprehensive test cases for detected bugs
- **Execute** tests on AWS compute infrastructure (Lambda/ECS)
- **Analyze** test results and identify root causes
- **Resolve** bugs with automated fix suggestions

The platform is designed for enterprise DevOps automation, targeting <$100/month operational costs for demonstration environments.

## Architecture

The system consists of three main components:

### 1. Backend (Python)
- **Agents**: Five specialized AI agents for bug lifecycle management
- **Orchestration**: LangGraph-based workflow state machine
- **API**: FastAPI REST endpoints for workflow management
- **Location**: `backend/`

### 2. Infrastructure (TypeScript CDK)
- AWS CDK definitions for all cloud resources
- DynamoDB, S3, Lambda, ECS, CloudWatch configuration
- IAM policies and security settings
- **Location**: `infrastructure/`

### 3. Web Dashboard (Flask)
- Python Flask-based web interface (no Node.js required!)
- Real-time workflow monitoring interface
- Bug reports and fix suggestions visualization
- Filtering and drill-down capabilities
- **Location**: `backend/cloudforge/web/`

## Prerequisites

- Python 3.11+
- AWS CLI configured with appropriate credentials
- AWS account with permissions for Lambda, ECS, DynamoDB, S3, Bedrock
- (Optional) Node.js 18+ for AWS CDK infrastructure deployment only

## Quick Start

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the Web Dashboard

```bash
python run_web.py
```

Open your browser to **http://localhost:5000**

### 3. (Optional) Run Tests

```bash
pytest tests/
```

That's it! No Node.js required for the web interface.

## Configuration

### API Keys and Credentials

The system requires configuration for external AI services. All API integrations include placeholder comments for user configuration:

1. **AWS Bedrock**: Configure model ID and region in `backend/config.py`
2. **Amazon Q Developer**: Configure API endpoint in `backend/config.py`
3. **AWS Credentials**: Load from AWS Secrets Manager or environment variables

See `backend/config.example.py` for detailed configuration options.

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
# Add your API keys here - see backend/config.example.py for details
```

## Project Structure

```
cloudforge-bug-intelligence/
├── backend/                    # Python backend
│   ├── cloudforge/
│   │   ├── agents/            # AI agents
│   │   ├── orchestration/     # LangGraph workflow
│   │   ├── api/               # FastAPI endpoints
│   │   ├── models/            # Pydantic data models
│   │   ├── web/               # Flask web dashboard
│   │   │   ├── templates/     # HTML templates
│   │   │   ├── static/        # CSS/JS assets
│   │   │   └── app.py         # Flask application
│   │   └── utils/             # Utilities and helpers
│   ├── tests/                 # Test suite
│   ├── requirements.txt       # Python dependencies
│   └── run_web.py             # Run web dashboard
├── infrastructure/            # AWS CDK (TypeScript)
│   ├── lib/                   # CDK stack definitions
│   ├── test/                  # Infrastructure tests
│   └── package.json           # Node dependencies
└── README.md                  # This file
```

## Development

### Running Tests

```bash
# Backend tests (unit + property-based)
cd backend
pytest tests/

# Infrastructure tests
cd infrastructure
npm test

# Web dashboard tests (included in backend tests)
# No separate testing needed
```

### Local Development

The system supports local development using LocalStack for AWS service emulation:

```bash
# Start LocalStack
docker-compose up -d

# Run backend with local AWS endpoints
cd backend
python -m uvicorn api.main:app --reload
```

## API Documentation

Once the backend is running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Key Features

- **Cost-Effective**: Targets <$100/month for demo environments
- **Scalable**: Automatic routing between Lambda and ECS based on resource needs
- **Resilient**: Exponential backoff, circuit breakers, and state recovery
- **Observable**: Comprehensive CloudWatch logging and metrics
- **Secure**: IAM least privilege, encryption at rest/transit, VPC isolation

## Testing Strategy

The project uses a dual testing approach:
- **Unit Tests**: Specific examples and edge cases
- **Property-Based Tests**: Universal properties across randomized inputs using Hypothesis

All design properties from the specification have corresponding property tests.

## Deployment

### Production Deployment

```bash
# Deploy infrastructure
cd infrastructure
cdk deploy --all

# Deploy backend API
cd ../backend
# Follow AWS Lambda deployment guide

# Build and deploy dashboard (Flask is deployed with backend)
# No separate dashboard deployment needed
```

### Blue-Green Deployment

The infrastructure supports blue-green deployments for zero-downtime updates:

```bash
cd infrastructure
cdk deploy --require-approval never
```

## Monitoring

Access CloudWatch dashboards for:
- Agent execution times and success rates
- API request rates and latencies
- Cost metrics and budget tracking
- Error rates and critical alerts

## Contributing

1. Create a feature branch
2. Make changes with tests
3. Ensure all tests pass: `pytest` and `npm test`
4. Submit pull request

## License

[Your License Here]

## Support

For issues and questions, please open a GitHub issue or contact the development team.
