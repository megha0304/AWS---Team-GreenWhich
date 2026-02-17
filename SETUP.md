# CloudForge Bug Intelligence - Setup Guide

This guide walks you through setting up the CloudForge Bug Intelligence platform for development and deployment.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11 or higher**: [Download Python](https://www.python.org/downloads/)
- **Node.js 18 or higher**: [Download Node.js](https://nodejs.org/)
- **Poetry** (optional, for Python dependency management): `pip install poetry`
- **AWS CLI**: [Install AWS CLI](https://aws.amazon.com/cli/)
- **AWS Account** with permissions for:
  - Lambda, ECS, DynamoDB, S3, CloudWatch
  - AWS Bedrock (with Claude model access)
  - Amazon Q Developer (optional, for test generation)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd cloudforge-bug-intelligence
```

### 2. Backend Setup

#### Option A: Using Poetry (Recommended)

```bash
cd backend
poetry install
poetry shell
```

#### Option B: Using pip

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# See backend/config.example.py for detailed instructions
nano .env  # or use your preferred editor
```

**Important Configuration Steps:**

1. **AWS Bedrock Setup**:
   - Enable Bedrock in your AWS account
   - Request access to Claude models in the Bedrock console
   - Update `BEDROCK_MODEL_ID` in `.env`
   - Ensure AWS credentials have `bedrock:InvokeModel` permissions

2. **Amazon Q Developer Setup** (Optional):
   - Sign up for Amazon Q Developer access
   - Obtain API endpoint and credentials
   - Update `Q_DEVELOPER_ENDPOINT` and `Q_DEVELOPER_API_KEY` in `.env`
   - If unavailable, tests will use mock implementations

3. **AWS Credentials**:
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, and region
   ```

#### Run Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run with coverage
pytest --cov=cloudforge --cov-report=html
```

### 3. Infrastructure Setup

```bash
cd infrastructure
npm install
npm run build
npm test
```

#### Deploy to AWS (Optional)

```bash
# Bootstrap CDK (first time only)
npx cdk bootstrap

# Deploy infrastructure
npx cdk deploy

# View what will be deployed without making changes
npx cdk diff
```

### 4. Dashboard Setup

```bash
cd dashboard
npm install
npm run dev  # Start development server on http://localhost:3000
```

#### Run Dashboard Tests

```bash
npm test
```

## Development Workflow

### Backend Development

1. **Activate virtual environment**:
   ```bash
   cd backend
   source venv/bin/activate  # or: poetry shell
   ```

2. **Run linting and formatting**:
   ```bash
   ruff check .
   black .
   mypy cloudforge/
   ```

3. **Run tests continuously**:
   ```bash
   pytest --watch
   ```

4. **Start API server**:
   ```bash
   uvicorn cloudforge.api.main:app --reload
   # API docs available at http://localhost:8000/docs
   ```

### Infrastructure Development

1. **Watch for changes**:
   ```bash
   cd infrastructure
   npm run watch
   ```

2. **Run linting**:
   ```bash
   npm run lint
   ```

3. **Synthesize CloudFormation**:
   ```bash
   npx cdk synth
   ```

### Dashboard Development

1. **Start development server**:
   ```bash
   cd dashboard
   npm run dev
   ```

2. **Run linting and formatting**:
   ```bash
   npm run lint
   npm run format
   ```

3. **Build for production**:
   ```bash
   npm run build
   npm run preview  # Preview production build
   ```

## Local Development with LocalStack

For local development without AWS costs, use LocalStack to emulate AWS services:

### 1. Install LocalStack

```bash
pip install localstack
# or
brew install localstack/tap/localstack-cli
```

### 2. Start LocalStack

```bash
localstack start -d
```

### 3. Configure Backend for LocalStack

Update `.env`:

```env
AWS_ENDPOINT_URL=http://localhost:4566
ENVIRONMENT=local
```

### 4. Create Local Resources

```bash
# Create DynamoDB tables
aws dynamodb create-table \
  --table-name cloudforge-workflows \
  --attribute-definitions AttributeName=workflow_id,AttributeType=S \
  --key-schema AttributeName=workflow_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --endpoint-url http://localhost:4566

# Create S3 bucket
aws s3 mb s3://cloudforge-artifacts --endpoint-url http://localhost:4566
```

## API Integration Setup

### AWS Bedrock

1. **Enable Bedrock**:
   - Go to AWS Console → Bedrock
   - Select your region (us-east-1 recommended)
   - Request model access for Claude models

2. **Test Bedrock Access**:
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

3. **Update Configuration**:
   ```env
   BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
   BEDROCK_REGION=us-east-1
   ```

### Amazon Q Developer

1. **Sign Up**:
   - Visit [Amazon Q Developer](https://aws.amazon.com/q/developer/)
   - Request access to the API

2. **Obtain Credentials**:
   - Follow AWS documentation to get API endpoint and key
   - Store credentials in AWS Secrets Manager (recommended) or `.env`

3. **Update Configuration**:
   ```env
   Q_DEVELOPER_ENDPOINT=https://your-endpoint.amazonaws.com
   Q_DEVELOPER_API_KEY=your-api-key
   ```

4. **Alternative**: If Q Developer is unavailable, the system will use mock implementations for testing. You can also integrate alternative code generation APIs by modifying the agent implementations.

## Troubleshooting

### Python Import Errors

```bash
# Ensure you're in the virtual environment
which python  # Should point to venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### AWS Credentials Issues

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check AWS CLI configuration
aws configure list

# Use specific profile
export AWS_PROFILE=your-profile-name
```

### Bedrock Access Denied

- Ensure you've requested model access in the Bedrock console
- Verify IAM permissions include `bedrock:InvokeModel`
- Check that the model ID is correct for your region

### LocalStack Connection Issues

```bash
# Check LocalStack status
localstack status

# Restart LocalStack
localstack stop
localstack start -d

# Verify endpoint
curl http://localhost:4566/_localstack/health
```

### TypeScript Build Errors

```bash
# Clear build cache
rm -rf node_modules dist
npm install
npm run build
```

## Next Steps

1. **Review the Architecture**: See `README.md` for system architecture overview
2. **Explore the API**: Visit `http://localhost:8000/docs` for interactive API documentation
3. **Run Example Workflows**: See `examples/` directory for sample workflows
4. **Read the Design Document**: See `.kiro/specs/cloudforge-bug-intelligence/design.md`

## Getting Help

- **Issues**: Open a GitHub issue
- **Documentation**: See `README.md` and design documents in `.kiro/specs/`
- **AWS Support**: Consult AWS documentation for service-specific issues

## Security Notes

- **Never commit `.env` files** with real credentials
- **Use AWS Secrets Manager** for production credentials
- **Enable MFA** on your AWS account
- **Follow least privilege** for IAM policies
- **Rotate credentials** regularly

## Cost Management

To keep costs under $100/month:

- Use `us-east-1` region (typically lowest cost)
- Set up AWS Budget alerts
- Monitor CloudWatch metrics
- Use Lambda for short tasks (<15 min)
- Enable S3 lifecycle policies
- Delete unused resources regularly

```bash
# Set up AWS Budget alert
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget file://budget.json
```

See `docs/cost-management.md` for detailed cost optimization strategies.
