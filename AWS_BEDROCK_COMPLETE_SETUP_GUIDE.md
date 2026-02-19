# AWS Bedrock Complete Setup & Integration Guide

## 🎯 Quick Overview

This guide will help you:
1. **Set up AWS Bedrock** - Enable Claude AI for bug detection
2. **Implement real Bedrock calls** - Replace placeholder code with actual API calls
3. **Deploy infrastructure** - Set up DynamoDB, S3, Lambda, ECS
4. **Get a shareable link** - Deploy to Render.com for permanent hosting

**Time to complete**: 1-2 hours for full setup

---

## Part 1: AWS Bedrock Setup (15 minutes)

### Step 1: Enable AWS Bedrock Access

1. **Log in to AWS Console**: https://console.aws.amazon.com
2. **Select Region**: Choose `us-east-1` (N. Virginia)
3. **Navigate to Bedrock**: Search for "Bedrock" in the search bar
4. **Request Model Access**:
   - Click "Model access" in left sidebar
   - Click "Manage model access" button
   - Find "Anthropic" section
   - Check: **Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`)
   - Click "Request model access"
   - Wait ~30 seconds for approval (usually instant)

### Step 2: Create AWS Credentials

1. **Navigate to IAM**: AWS Console → IAM
2. **Create User**:
   - Click "Users" → "Create user"
   - Username: `cloudforge-admin`
   - Click "Next"
3. **Attach Policies**:
   - Select "Attach policies directly"
   - Search and select:
     - `AmazonBedrockFullAccess`
     - `AmazonDynamoDBFullAccess`
     - `AmazonS3FullAccess`
   - Click "Next" → "Create user"
4. **Create Access Keys**:
   - Click on `cloudforge-admin` user
   - Go to "Security credentials" tab
   - Click "Create access key"
   - Select "Command Line Interface (CLI)"
   - Click "Next" → "Create access key"
   - **SAVE THESE CREDENTIALS** (you'll need them later):
     - Access Key ID: `AKIA...`
     - Secret Access Key: `wJalr...`

### Step 3: Configure Local Environment

Create `.env` file in `backend/` directory:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your-access-key-id-here
AWS_SECRET_ACCESS_KEY=your-secret-access-key-here
AWS_REGION=us-east-1

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Agent Configuration
MAX_RETRIES=3
MAX_FILES_PER_BATCH=100
```

### Step 4: Test Bedrock Connection

```bash
cd backend
python -c "
import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv()

bedrock = boto3.client(
    'bedrock-runtime',
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

request = {
    'anthropic_version': 'bedrock-2023-05-31',
    'max_tokens': 100,
    'messages': [{'role': 'user', 'content': 'Say hello!'}]
}

try:
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        body=json.dumps(request)
    )
    result = json.loads(response['body'].read())
    print('✓ Bedrock connection successful!')
    print(f'Response: {result[\"content\"][0][\"text\"]}')
except Exception as e:
    print(f'✗ Connection failed: {e}')
"
```

---

## Part 2: Implement Real Bedrock Integration (30 minutes)

The agents currently have placeholder code. Here's what needs to be updated:

### Files to Update

1. `backend/cloudforge/agents/bug_detective.py` - Line ~200-250
2. `backend/cloudforge/agents/analysis.py` - Line ~150-200
3. `backend/cloudforge/agents/resolution.py` - (if using Bedrock for fixes)

### Option A: Use the BedrockClient Utility (Recommended)

The system already has a `BedrockClient` utility that handles all Bedrock calls. Update the agents to use it:

**Update `bug_detective.py`**:

```python
# In __init__ method, add:
from cloudforge.utils.bedrock_client import BedrockClient

self.bedrock_helper = BedrockClient(config)

# Replace _call_bedrock_for_bugs method with:
async def _call_bedrock_for_bugs(
    self,
    file_path: str,
    code_content: str
) -> List[BugReport]:
    """Call AWS Bedrock API to analyze code and detect bugs."""
    try:
        # Use BedrockClient utility
        bugs_data = await self.bedrock_helper.analyze_code_for_bugs(
            file_path=file_path,
            code_content=code_content
        )
        
        # Convert to BugReport objects
        bugs = []
        for bug_data in bugs_data:
            bug = BugReport(
                bug_id=str(uuid4()),
                file_path=file_path,
                line_number=bug_data['line_number'],
                severity=bug_data['severity'],
                description=bug_data['description'],
                code_snippet=self._extract_code_snippet(
                    code_content,
                    bug_data['line_number']
                ),
                confidence_score=bug_data.get('confidence', 0.8)
            )
            bugs.append(bug)
        
        return bugs
        
    except Exception as e:
        self.logger.error(f"Bedrock analysis failed: {e}")
        return []  # Return empty list on failure
```

**Update `analysis.py`**:

```python
# In __init__ method, add:
from cloudforge.utils.bedrock_client import BedrockClient

self.bedrock_helper = BedrockClient(config)

# Replace _analyze_failure method with:
async def _analyze_failure(
    self,
    test_result: TestResult,
    bug: BugReport,
    workflow_id: str
) -> RootCause:
    """Analyze test failure using Bedrock."""
    try:
        # Use BedrockClient utility
        analysis = await self.bedrock_helper.analyze_root_cause(
            bug_description=bug.description,
            code_snippet=bug.code_snippet,
            test_output=f"{test_result.stdout}\n{test_result.stderr}",
            file_path=bug.file_path
        )
        
        # Create root cause
        root_cause = RootCause(
            bug_id=bug.bug_id,
            cause_description=analysis['cause_description'],
            related_bugs=[],
            confidence_score=analysis['confidence_score']
        )
        
        return root_cause
        
    except Exception as e:
        self.logger.error(f"Root cause analysis failed: {e}")
        # Return low-confidence fallback
        return RootCause(
            bug_id=bug.bug_id,
            cause_description=f"Analysis failed: {str(e)}",
            related_bugs=[],
            confidence_score=0.0
        )
```

### Option B: Implement Direct Bedrock Calls

If you prefer to implement the calls directly in the agents, uncomment the code blocks marked with `TODO` in:
- `backend/cloudforge/agents/bug_detective.py` (line ~200-250)
- `backend/cloudforge/agents/analysis.py` (line ~150-200)

---

## Part 3: Set Up AWS Infrastructure (30 minutes)

### Option A: Manual Setup (Quick Test)

**Create DynamoDB Tables**:

```bash
# Workflows table
aws dynamodb create-table \
  --table-name cloudforge-workflows \
  --attribute-definitions \
    AttributeName=workflow_id,AttributeType=S \
  --key-schema \
    AttributeName=workflow_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Bugs table
aws dynamodb create-table \
  --table-name cloudforge-bugs \
  --attribute-definitions \
    AttributeName=bug_id,AttributeType=S \
    AttributeName=workflow_id,AttributeType=S \
  --key-schema \
    AttributeName=bug_id,KeyType=HASH \
  --global-secondary-indexes \
    "IndexName=workflow-index,KeySchema=[{AttributeName=workflow_id,KeyType=HASH}],Projection={ProjectionType=ALL}" \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

**Create S3 Bucket**:

```bash
# Replace YOUR-ACCOUNT-ID with your AWS account ID
aws s3 mb s3://cloudforge-artifacts-YOUR-ACCOUNT-ID --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket cloudforge-artifacts-YOUR-ACCOUNT-ID \
  --versioning-configuration Status=Enabled
```

**Update `.env` file**:

```bash
# Add to backend/.env
DYNAMODB_TABLE_WORKFLOWS=cloudforge-workflows
DYNAMODB_TABLE_BUGS=cloudforge-bugs
S3_BUCKET_ARTIFACTS=cloudforge-artifacts-YOUR-ACCOUNT-ID
```

### Option B: AWS CDK Deployment (Production)

```bash
# Install AWS CDK
npm install -g aws-cdk

# Bootstrap CDK (one-time setup)
cdk bootstrap aws://YOUR-ACCOUNT-ID/us-east-1

# Deploy infrastructure
cd infrastructure
npm install
npm run build
cdk deploy --all
```

---

## Part 4: Deploy for Shareable Link (30 minutes)

### Deploy to Render.com (Free, Always-On Link)

**Step 1: Prepare for Deployment**

Create `render.yaml` in project root:

```yaml
services:
  - type: web
    name: cloudforge-bug-intelligence
    env: python
    region: oregon
    plan: free
    buildCommand: "cd backend && pip install -r requirements.txt"
    startCommand: "cd backend && python -m uvicorn cloudforge.api.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: AWS_REGION
        value: us-east-1
      - key: AWS_ACCESS_KEY_ID
        sync: false
      - key: AWS_SECRET_ACCESS_KEY
        sync: false
      - key: BEDROCK_MODEL_ID
        value: anthropic.claude-3-sonnet-20240229-v1:0
      - key: DYNAMODB_TABLE_WORKFLOWS
        value: cloudforge-workflows
      - key: DYNAMODB_TABLE_BUGS
        value: cloudforge-bugs
      - key: S3_BUCKET_ARTIFACTS
        value: cloudforge-artifacts-YOUR-ACCOUNT-ID
```

**Step 2: Push to GitHub**

```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

**Step 3: Deploy on Render**

1. Go to https://render.com and sign up (free)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Render will auto-detect `render.yaml`
5. Add environment variables:
   - `AWS_ACCESS_KEY_ID`: Your AWS access key
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
6. Click "Create Web Service"
7. Wait 5-10 minutes for deployment

**Step 4: Get Your Shareable Link**

After deployment:
- **API**: `https://cloudforge-bug-intelligence.onrender.com`
- **Docs**: `https://cloudforge-bug-intelligence.onrender.com/docs`
- **Health**: `https://cloudforge-bug-intelligence.onrender.com/health`

**This link is permanent and always accessible!**

---

## Part 5: Test End-to-End (15 minutes)

### Test Locally First

```bash
cd backend

# Set environment variables
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Run API
python -m uvicorn cloudforge.api.main:app --reload --port 8000

# In another terminal, test:
curl http://localhost:8000/health
```

### Test Deployed API

```bash
# Test health endpoint
curl https://cloudforge-bug-intelligence.onrender.com/health

# Create a workflow
curl -X POST https://cloudforge-bug-intelligence.onrender.com/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/example/repo",
    "branch": "main"
  }'

# Check workflow status (replace WORKFLOW_ID)
curl https://cloudforge-bug-intelligence.onrender.com/workflows/WORKFLOW_ID
```

---

## 📊 Cost Estimate

### AWS Costs (Monthly)

| Service | Usage | Cost |
|---------|-------|------|
| **Bedrock** | 1000 API calls | $20-30 |
| **DynamoDB** | 1GB storage | $5-10 |
| **S3** | 10GB storage | $1-5 |
| **Total** | | **$25-45/month** |

### Render.com Costs

- **Free Tier**: $0/month (sleeps after 15min inactivity)
- **Paid Tier**: $7/month (always-on, no sleep)

**Total Monthly Cost**: $25-52/month

---

## ✅ Completion Checklist

- [ ] AWS Bedrock access granted for Claude 3 Sonnet
- [ ] AWS credentials created and saved
- [ ] `.env` file configured with credentials
- [ ] Bedrock connection test successful
- [ ] Bedrock integration code updated in agents
- [ ] DynamoDB tables created
- [ ] S3 bucket created
- [ ] Local API test successful
- [ ] Code pushed to GitHub
- [ ] Deployed to Render.com
- [ ] Shareable link working
- [ ] End-to-end workflow test successful

---

## 🐛 Troubleshooting

### "AccessDeniedException" from Bedrock

**Solution**: Request model access in Bedrock console (Part 1, Step 1)

### "ResourceNotFoundException" for DynamoDB

**Solution**: Create tables manually or deploy CDK stack (Part 3)

### Render deployment fails

**Solution**: Check build logs in Render dashboard. Common issues:
- Missing dependencies in `requirements.txt`
- Environment variables not set
- Python version mismatch

### API returns 500 errors

**Solution**: Check logs for AWS credential issues. Verify:
- AWS credentials are set in Render environment variables
- IAM permissions include Bedrock, DynamoDB, S3 access
- Region is correct (us-east-1)

---

## 🚀 Next Steps

After completing this setup:

1. **Test with real repository**: Use the example in `examples/sample_repository/`
2. **Monitor costs**: Check AWS Cost Explorer daily
3. **Optimize**: Adjust batch sizes and rate limits based on usage
4. **Scale**: Upgrade Render plan if needed ($7/month for always-on)
5. **Custom domain**: Add your own domain in Render settings (optional)

---

## 📚 Additional Resources

- **Complete AWS Setup**: See `AWS_COMPLETE_SETUP_GUIDE.md` for advanced setup
- **Simple Deployment**: See `SIMPLE_DEPLOYMENT.md` for alternative hosting options
- **API Documentation**: See `API_DOCUMENTATION.md` for API reference
- **Examples**: See `examples/` directory for usage examples

---

## 🎉 Success!

Once you complete this guide, you'll have:
- ✅ Real AWS Bedrock integration (not placeholders)
- ✅ AWS infrastructure (DynamoDB, S3)
- ✅ Permanent shareable link
- ✅ Production-ready bug detection platform

**Your shareable link**: `https://cloudforge-bug-intelligence.onrender.com`

Share this link with anyone to demonstrate your CloudForge Bug Intelligence platform!
