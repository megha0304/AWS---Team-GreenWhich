# CloudForge Bug Intelligence - Project Structure

This document provides an overview of the project structure and organization.

## Directory Layout

```
cloudforge-bug-intelligence/
├── backend/                          # Python backend application
│   ├── cloudforge/                   # Main Python package
│   │   ├── __init__.py
│   │   ├── agents/                   # AI agents for bug lifecycle
│   │   │   ├── __init__.py
│   │   │   ├── bug_detective.py      # Bug detection agent (Task 7)
│   │   │   ├── test_architect.py     # Test generation agent (Task 8)
│   │   │   ├── execution.py          # Test execution agent (Task 9)
│   │   │   ├── analysis.py           # Result analysis agent (Task 10)
│   │   │   └── resolution.py         # Fix generation agent (Task 11)
│   │   ├── models/                   # Pydantic data models
│   │   │   ├── __init__.py
│   │   │   ├── state.py              # AgentState and related models (Task 2) ✅
│   │   │   └── config.py             # SystemConfig model (Task 3)
│   │   ├── orchestration/            # LangGraph workflow orchestration
│   │   │   ├── __init__.py
│   │   │   ├── workflow.py           # WorkflowOrchestrator (Task 13)
│   │   │   └── state_store.py        # DynamoDB state persistence (Task 4)
│   │   ├── api/                      # FastAPI REST endpoints
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI application (Task 15)
│   │   │   ├── routes.py             # API route definitions (Task 15)
│   │   │   └── middleware.py         # Rate limiting, auth (Task 15)
│   │   ├── web/                      # Flask web dashboard ✅
│   │   │   ├── __init__.py
│   │   │   ├── app.py                # Flask application
│   │   │   ├── templates/            # HTML templates
│   │   │   │   ├── base.html
│   │   │   │   ├── index.html
│   │   │   │   ├── workflows.html
│   │   │   │   └── workflow_detail.html
│   │   │   └── static/               # CSS/JS assets
│   │   │       ├── css/
│   │   │       │   └── style.css
│   │   │       └── js/
│   │   │           └── main.js
│   │   └── utils/                    # Utility functions
│   │       ├── __init__.py
│   │       ├── retry.py              # Exponential backoff (Task 5)
│   │       ├── circuit_breaker.py    # Circuit breaker (Task 5)
│   │       ├── logging.py            # Structured logging (Task 14)
│   │       └── storage.py            # S3 utilities (Task 20)
│   ├── tests/                        # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py               # Shared fixtures
│   │   ├── unit/                     # Unit tests
│   │   │   ├── test_models.py        # Model tests ✅
│   │   │   ├── agents/
│   │   │   ├── orchestration/
│   │   │   └── api/
│   │   ├── property/                 # Property-based tests (Hypothesis)
│   │   │   ├── test_bug_detection_properties.py
│   │   │   ├── test_test_generation_properties.py
│   │   │   ├── test_execution_properties.py
│   │   │   ├── test_analysis_properties.py
│   │   │   ├── test_resolution_properties.py
│   │   │   ├── test_orchestration_properties.py
│   │   │   └── test_api_properties.py
│   │   └── integration/              # Integration tests
│   │       ├── test_workflow_execution.py
│   │       ├── test_state_persistence.py
│   │       └── test_error_recovery.py
│   ├── pyproject.toml                # Poetry configuration
│   ├── requirements.txt              # Pip dependencies ✅
│   ├── run_web.py                    # Run Flask web dashboard ✅
│   ├── .env.example                  # Example environment variables
│   ├── config.example.py             # Example configuration with API placeholders ✅
│   └── .pre-commit-config.yaml       # Pre-commit hooks
│
├── infrastructure/                   # AWS CDK infrastructure (TypeScript)
│   ├── bin/
│   │   └── cloudforge-infrastructure.ts  # CDK app entry point
│   ├── lib/
│   │   ├── cloudforge-infrastructure-stack.ts  # Main stack (Task 18)
│   │   ├── compute-stack.ts          # Lambda/ECS resources (Task 18)
│   │   ├── storage-stack.ts          # DynamoDB/S3 resources (Task 18)
│   │   └── monitoring-stack.ts       # CloudWatch resources (Task 18)
│   ├── test/
│   │   └── cloudforge-infrastructure.test.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── cdk.json
│   ├── jest.config.js
│   ├── .eslintrc.json
│   └── .prettierrc.json
│
├── .kiro/                            # Kiro spec files
│   └── specs/
│       └── cloudforge-bug-intelligence/
│           ├── requirements.md
│           ├── design.md
│           └── tasks.md
│
├── docker-compose.yml                # LocalStack for local AWS emulation
├── Makefile                          # Common development commands
├── README.md                         # Project overview
├── SETUP.md                          # Setup instructions
├── PROJECT_STRUCTURE.md              # This file
└── .gitignore
```
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .eslintrc.json
│   └── .prettierrc.json
│
├── .kiro/                            # Kiro specification files
│   └── specs/
│       └── cloudforge-bug-intelligence/
│           ├── requirements.md       # Requirements document
│           ├── design.md             # Design document
│           └── tasks.md              # Implementation tasks
│
├── .gitignore                        # Git ignore patterns
├── README.md                         # Project overview and quick start
├── SETUP.md                          # Detailed setup instructions
├── PROJECT_STRUCTURE.md              # This file
├── Makefile                          # Development commands
└── docker-compose.yml                # LocalStack for local development
```

## Key Components

### Backend (Python)

The backend is organized into several key modules:

1. **Agents** (`cloudforge/agents/`): Five specialized AI agents that handle different phases of the bug lifecycle
2. **Models** (`cloudforge/models/`): Pydantic models for data validation and serialization
3. **Orchestration** (`cloudforge/orchestration/`): LangGraph-based workflow state machine
4. **API** (`cloudforge/api/`): FastAPI REST endpoints for external access
5. **Utils** (`cloudforge/utils/`): Shared utilities for retry logic, logging, storage, etc.

### Infrastructure (TypeScript CDK)

The infrastructure code defines all AWS resources:

1. **Core Stack**: DynamoDB tables, S3 buckets, IAM roles
2. **Compute Stack**: Lambda functions and ECS clusters
3. **Monitoring Stack**: CloudWatch dashboards, alarms, and SNS topics

### Dashboard (React)

The web dashboard provides a user interface for:

1. **Workflow Monitoring**: View active and completed workflows
2. **Bug Reports**: Browse detected bugs with severity and details
3. **Test Results**: View test execution results and logs
4. **Fix Suggestions**: Review generated code patches and diffs

## Testing Strategy

### Test Organization

Tests are organized by type:

1. **Unit Tests** (`tests/unit/`): Test individual components in isolation
2. **Property Tests** (`tests/property/`): Test universal properties using Hypothesis
3. **Integration Tests** (`tests/integration/`): Test component interactions end-to-end

### Property-Based Testing

Each design property from the specification has a corresponding property test:

- Property tests use Hypothesis to generate randomized inputs
- Tests validate that properties hold across all valid inputs
- Minimum 100 iterations per property test
- Tagged with feature and property number for traceability

### Test Fixtures

Shared test fixtures are defined in `tests/conftest.py`:

- Mock AWS clients (Bedrock, Q Developer, Lambda, ECS, DynamoDB, S3)
- Sample configuration objects
- Test data factories

## Configuration Management

### Environment Variables

Configuration is loaded from multiple sources (in order of precedence):

1. Environment variables
2. `.env` file
3. AWS Secrets Manager (production)
4. Default values in `SystemConfig`

### API Integration Placeholders

All external API integrations include placeholder comments:

- **AWS Bedrock**: Configure model ID and region
- **Amazon Q Developer**: Configure API endpoint and credentials
- See `backend/config.example.py` for detailed instructions

## Development Workflow

### Local Development

1. **Start LocalStack**: `make localstack` or `docker-compose up -d`
2. **Start Backend**: `make dev-backend` or `cd backend && uvicorn cloudforge.api.main:app --reload`
3. **Start Dashboard**: `make dev-dashboard` or `cd dashboard && npm run dev`

### Running Tests

- **All tests**: `make test`
- **Backend only**: `make test-backend`
- **Infrastructure only**: `make test-infra`
- **Dashboard only**: `make test-dashboard`

### Code Quality

- **Linting**: `make lint`
- **Formatting**: `make format`
- **Type checking**: `make type-check`

## Deployment

### Infrastructure Deployment

```bash
cd infrastructure
npx cdk deploy --all
```

### Backend Deployment

Backend can be deployed as:
- AWS Lambda functions (for API endpoints)
- ECS Fargate tasks (for orchestrator)

### Dashboard Deployment

Dashboard can be deployed to:
- S3 + CloudFront (static hosting)
- Amplify Hosting
- Any static hosting service

## Task Implementation Order

The implementation follows this order (see `tasks.md` for details):

1. **Task 1**: Project structure and dependencies ✓ (Current)
2. **Task 2-3**: Core data models and configuration
3. **Task 4-5**: State store and error handling utilities
4. **Task 7-11**: Individual agents (Bug Detective → Resolution)
5. **Task 13**: LangGraph orchestrator
6. **Task 14**: Logging and monitoring
7. **Task 15-16**: FastAPI REST API
8. **Task 18**: AWS CDK infrastructure
9. **Task 19**: React web dashboard
10. **Task 21**: Integration and deployment
11. **Task 23**: Documentation and examples

## Next Steps

After completing Task 1 (project setup), proceed to:

1. **Task 2**: Implement core data models (`cloudforge/models/state.py`)
2. **Task 3**: Implement configuration management (`cloudforge/models/config.py`)
3. **Task 4**: Implement state store with DynamoDB (`cloudforge/orchestration/state_store.py`)

See `tasks.md` for detailed task descriptions and acceptance criteria.

## Additional Resources

- **Requirements**: `.kiro/specs/cloudforge-bug-intelligence/requirements.md`
- **Design**: `.kiro/specs/cloudforge-bug-intelligence/design.md`
- **Setup Guide**: `SETUP.md`
- **API Documentation**: `http://localhost:8000/docs` (when backend is running)
