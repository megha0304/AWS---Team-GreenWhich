# Complete AWS Setup Guide for CloudForge Bug Intelligence

This guide covers **everything** you need to set up in AWS to make your CloudForge Bug Intelligence platform fully functional with a shareable hosted link.

## Table of Contents

1. [AWS Account Prerequisites](#1-aws-account-prerequisites)
2. [AWS Bedrock Setup (AI Models)](#2-aws-bedrock-setup-ai-models)
3. [IAM User & Permissions Setup](#3-iam-user--permissions-setup)
4. [AWS CDK Bootstrap](#4-aws-cdk-bootstrap)
5. [DynamoDB Tables Setup](#5-dynamodb-tables-setup)
6. [S3 Buckets Setup](#6-s3-buckets-setup)
7. [Lambda Functions Setup](#7-lambda-functions-setup)
8. [ECS Cluster Setup](#8-ecs-cluster-setup)
9. [API Gateway Setup](#9-api-gateway-setup)
10. [CloudWatch Setup](#10-cloudwatch-setup)
11. [Secrets Manager Setup](#11-secrets-manager-setup)
12. [Domain & Hosting Setup](#12-domain--hosting-setup)
13. [Cost Estimation](#13-cost-estimation)
14. [Testing Your Setup](#14-testing-your-setup)

---

## 1. AWS Account Prerequisites

### What You Need

- **AWS Account**: Sign up at https://aws.amazon.com if you don't have one
- **Credit Card**: Required for AWS account (even for free tier)
- **AWS CLI**: Install from https://aws.amazon.com/cli/
- **Node.js 18+**: For AWS CDK (install from https://nodejs.org/)
- **Python 3.11+**: For backend code

### Initial Setup

```bash
# Install AWS CLI (Windows)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Install AWS CLI (Mac)
brew install awscli

# Install AWS CLI (Linux)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

### Configure AWS CLI

```bash
# Configure your AWS credentials
aws configure

# You'll be prompted for:
# AWS Access Key ID: [Your access key]
# AWS Secret Access Key: [Your secret key]
# Default region name: us-east-1
# Default output format: json
```

---

## 2. AWS Bedrock Setup (AI Models)

AWS Bedrock provides access to Claude and other AI models. This is **critical** for bug detection and analysis.

### Step 1: Enable AWS Bedrock in Your Region

1. **Log in to AWS Console**: https://console.aws.amazon.com
2. **Select Region**: Choose `us-east-1` (N. Virginia) - Bedrock is available here
3. **Navigate to Bedrock**: Search for "Bedrock" in the AWS Console search bar

### Step 2: Request Model Access

1. **Go to Model Access**:
   - In Bedrock console, click "Model access" in the left sidebar
   - Click "Manage model access" button

2. **Request Access to Claude Models**:
   - Find "Anthropic" section
   - Check the box for: **Claude 3 Sonnet**
   - Model ID: `anthropic.claude-3-sonnet-20240229-v1:0`
   - Click "Request model access"

3. **Wait for Approval**:
   - Usually **instant** for Claude models
   - Status will change from "Pending" to "Access granted"
   - Refresh the page after 30 seconds

### Step 3: Verify Access

```bash
# Test Bedrock access via AWS CLI
aws bedrock list-foundation-models --region us-east-1

# You should see Claude models in the output
```

### Step 4: Note Your Model ID

```
Model ID: anthropic.claude-3-sonnet-20240229-v1:0
Region: us-east-1
```

You'll need this for configuration later.

### Alternative Models (Optional)

If you want to use different models:
- **Claude 3.5 Sonnet**: `anthropic.claude-3-5-sonnet-20240620-v1:0` (more powerful, more expensive)
- **Claude 3 Haiku**: `anthropic.claude-3-haiku-20240307-v1:0` (faster, cheaper)

---

## 3. IAM User & Permissions Setup

Create an IAM user with proper permissions for CloudForge.

### Step 1: Create IAM User

1. **Navigate to IAM**: AWS Console → IAM
2. **Create User**:
   - Click "Users" → "Create user"
   - Username: `cloudforge-admin`
   - Check "Provide user access to AWS Management Console" (optional)
   - Click "Next"

### Step 2: Attach Policies

Attach these managed policies:

```
✓ AmazonBedrockFullAccess
✓ AmazonDynamoDBFullAccess
✓ AmazonS3FullAccess
✓ AWSLambda_FullAccess
✓ AmazonECS_FullAccess
✓ CloudWatchFullAccess
✓ SecretsManagerReadWrite
✓ IAMFullAccess (for CDK to create roles)
✓ AmazonAPIGatewayAdministrator
```

### Step 3: Create Access Keys

1. **Go to User**: Click on `cloudforge-admin`
2. **Security Credentials Tab**: Click "Create access key"
3. **Use Case**: Select "Command Line Interface (CLI)"
4. **Download Keys**: Save the CSV file securely
5. **Configure CLI**:

```bash
aws configure --profile cloudforge
# Enter the access key ID and secret access key
```

### Step 4: Create Custom Policy (Optional - More Restrictive)

For production, create a custom policy with least privilege:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/cloudforge-workflows",
        "arn:aws:dynamodb:us-east-1:*:table/cloudforge-bugs"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::cloudforge-artifacts-*",
        "arn:aws:s3:::cloudforge-artifacts-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration"
      ],
      "Resource": "arn:aws:lambda:us-east-1:*:function:cloudforge-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask",
        "ecs:DescribeTasks",
        "ecs:StopTask"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:log-group:/aws/cloudforge/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:cloudforge/*"
    }
  ]
}
```

---

## 4. AWS CDK Bootstrap

AWS CDK needs to be bootstrapped in your account before deploying infrastructure.

### Step 1: Install AWS CDK

```bash
# Install CDK globally
npm install -g aws-cdk

# Verify installation
cdk --version
```

### Step 2: Bootstrap CDK

```bash
# Bootstrap CDK in your AWS account
cdk bootstrap aws://ACCOUNT-ID/us-east-1

# Replace ACCOUNT-ID with your AWS account ID
# Find your account ID:
aws sts get-caller-identity --query Account --output text
```

Example:
```bash
# If your account ID is 123456789012
cdk bootstrap aws://123456789012/us-east-1
```

### Step 3: Verify Bootstrap

```bash
# Check if CDK toolkit stack exists
aws cloudformation describe-stacks --stack-name CDKToolkit --region us-east-1
```

You should see a stack with status `CREATE_COMPLETE`.

---

## 5. DynamoDB Tables Setup

DynamoDB stores workflow state and bug reports.

### Option A: Manual Setup (Quick Test)

1. **Navigate to DynamoDB**: AWS Console → DynamoDB
2. **Create Workflows Table**:
   - Click "Create table"
   - Table name: `cloudforge-workflows`
   - Partition key: `workflow_id` (String)
   - Sort key: None
   - Table settings: Default settings (On-demand)
   - Click "Create table"

3. **Create Bugs Table**:
   - Click "Create table"
   - Table name: `cloudforge-bugs`
   - Partition key: `bug_id` (String)
   - Sort key: None
   - Add Global Secondary Index (GSI):
     - Index name: `workflow-index`
     - Partition key: `workflow_id` (String)
     - Sort key: `created_at` (String)
   - Click "Create table"

### Option B: CDK Deployment (Recommended)

The CDK will create these tables automatically when you deploy. See Section 7.

---

## 6. S3 Buckets Setup

S3 stores test results, artifacts, and logs.

### Option A: Manual Setup

1. **Navigate to S3**: AWS Console → S3
2. **Create Artifacts Bucket**:
   - Click "Create bucket"
   - Bucket name: `cloudforge-artifacts-YOUR-ACCOUNT-ID` (must be globally unique)
   - Region: `us-east-1`
   - Block all public access: ✓ (keep checked)
   - Bucket versioning: Enable
   - Default encryption: Enable (SSE-S3)
   - Click "Create bucket"

3. **Configure Lifecycle Policy**:
   - Go to bucket → Management tab
   - Create lifecycle rule:
     - Name: `archive-old-artifacts`
     - Scope: Apply to all objects
     - Lifecycle rule actions:
       - Transition to Glacier after 30 days
       - Delete after 90 days
     - Click "Create rule"

### Option B: CDK Deployment (Recommended)

The CDK will create this bucket automatically.

---

## 7. Lambda Functions Setup

Lambda runs short-duration tests (<15 minutes).

### Via CDK (Recommended)

The CDK will create Lambda functions automatically. You just need to deploy:

```bash
cd infrastructure
npm install
npm run build
cdk deploy CloudForgeComputeStack
```

### Manual Setup (Not Recommended)

If you want to create manually:

1. **Navigate to Lambda**: AWS Console → Lambda
2. **Create Function**:
   - Function name: `cloudforge-test-executor`
   - Runtime: Python 3.11
   - Architecture: x86_64
   - Execution role: Create new role with basic Lambda permissions
   - Click "Create function"

3. **Configure Function**:
   - Memory: 10240 MB (10 GB)
   - Timeout: 15 minutes (900 seconds)
   - Environment variables:
     - `AWS_REGION`: us-east-1
     - `DYNAMODB_TABLE`: cloudforge-workflows

---

## 8. ECS Cluster Setup

ECS runs long-duration tests (>15 minutes).

### Via CDK (Recommended)

```bash
cd infrastructure
cdk deploy CloudForgeComputeStack
```

### Manual Setup

1. **Navigate to ECS**: AWS Console → ECS
2. **Create Cluster**:
   - Cluster name: `cloudforge-cluster`
   - Infrastructure: AWS Fargate (serverless)
   - Click "Create"

3. **Create Task Definition**:
   - Task definition family: `cloudforge-test-task`
   - Launch type: Fargate
   - Operating system: Linux
   - CPU: 2 vCPU
   - Memory: 16 GB
   - Task role: Create new role with ECS task permissions
   - Container definitions:
     - Name: `test-executor`
     - Image: `python:3.11-slim`
     - Memory: 16384 MB
     - Environment variables: (same as Lambda)

---

## 9. API Gateway Setup

API Gateway provides a public HTTPS endpoint for your API.

### Step 1: Deploy API via CDK

```bash
cd infrastructure
cdk deploy CloudForgeApiStack
```

### Step 2: Get API Endpoint

```bash
# After deployment, CDK will output the API endpoint
# Example: https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod
```

### Step 3: Configure Custom Domain (Optional)

1. **Register Domain**: Use Route 53 or external registrar
2. **Request Certificate**: AWS Certificate Manager (ACM)
   - Navigate to ACM
   - Request public certificate
   - Domain name: `api.yourdomain.com`
   - Validation: DNS validation
   - Add CNAME records to your DNS

3. **Create Custom Domain in API Gateway**:
   - API Gateway → Custom domain names
   - Create custom domain name
   - Domain name: `api.yourdomain.com`
   - Certificate: Select your ACM certificate
   - Endpoint type: Regional
   - Create API mapping to your API

4. **Update DNS**:
   - Add CNAME record pointing to API Gateway domain

---

## 10. CloudWatch Setup

CloudWatch provides logging and monitoring.

### Via CDK (Automatic)

```bash
cd infrastructure
cdk deploy CloudForgeMonitoringStack
```

This creates:
- Log groups for all services
- Dashboards with key metrics
- Alarms for errors and costs
- SNS topics for notifications

### Manual Verification

1. **Navigate to CloudWatch**: AWS Console → CloudWatch
2. **Check Log Groups**:
   - `/aws/lambda/cloudforge-*`
   - `/aws/ecs/cloudforge-*`
   - `/aws/cloudforge/bug-intelligence`

3. **View Dashboards**:
   - CloudWatch → Dashboards
   - Look for `CloudForge-*` dashboards

---

## 11. Secrets Manager Setup

Store sensitive credentials securely.

### Step 1: Create Secret

```bash
# Create secret via AWS CLI
aws secretsmanager create-secret \
  --name cloudforge/production/credentials \
  --description "CloudForge API credentials" \
  --secret-string '{
    "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "api_key": "your-secure-api-key-here",
    "q_developer_endpoint": "https://your-q-endpoint.amazonaws.com",
    "q_developer_api_key": "your-q-api-key"
  }' \
  --region us-east-1
```

### Step 2: Verify Secret

```bash
# Retrieve secret to verify
aws secretsmanager get-secret-value \
  --secret-id cloudforge/production/credentials \
  --region us-east-1
```

### Step 3: Update Application Config

In your `backend/config.py`:

```python
# Load from Secrets Manager
config = SystemConfig.load_config(
    secrets_manager_secret_name="cloudforge/production/credentials"
)
```

---

## 12. Domain & Hosting Setup

Make your application accessible via a shareable link.

### Option A: Use API Gateway URL (Quick)

After deploying, you'll get a URL like:
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod
```

This works immediately but isn't pretty.

### Option B: Custom Domain (Professional)

#### For API (Backend)

1. **Register Domain**: 
   - Use Route 53: AWS Console → Route 53 → Register domain
   - Or use external registrar (GoDaddy, Namecheap, etc.)

2. **Request SSL Certificate**:
   ```bash
   # Request certificate via AWS CLI
   aws acm request-certificate \
     --domain-name api.yourdomain.com \
     --validation-method DNS \
     --region us-east-1
   ```

3. **Validate Certificate**:
   - Go to ACM console
   - Click on certificate
   - Add CNAME records to your DNS

4. **Configure API Gateway Custom Domain**:
   - See Section 9, Step 3

#### For Web Dashboard (Frontend)

**Option 1: S3 + CloudFront (Static Hosting)**

1. **Create S3 Bucket for Website**:
   ```bash
   aws s3 mb s3://cloudforge-web-yourdomain --region us-east-1
   ```

2. **Enable Static Website Hosting**:
   - S3 Console → Bucket → Properties
   - Static website hosting: Enable
   - Index document: `index.html`

3. **Upload Web Files**:
   ```bash
   cd backend/cloudforge/web
   aws s3 sync static/ s3://cloudforge-web-yourdomain/static/
   aws s3 sync templates/ s3://cloudforge-web-yourdomain/templates/
   ```

4. **Create CloudFront Distribution**:
   - CloudFront Console → Create distribution
   - Origin domain: Your S3 bucket
   - Viewer protocol policy: Redirect HTTP to HTTPS
   - Alternate domain name: `app.yourdomain.com`
   - SSL certificate: Select your ACM certificate

5. **Update DNS**:
   - Add CNAME: `app.yourdomain.com` → CloudFront domain

**Option 2: Deploy Flask App to Elastic Beanstalk**

```bash
# Install EB CLI
pip install awsebcli

# Initialize Elastic Beanstalk
cd backend
eb init -p python-3.11 cloudforge-web --region us-east-1

# Create environment
eb create cloudforge-web-prod

# Deploy
eb deploy

# Get URL
eb status
```

**Option 3: Deploy Flask App to Lambda + API Gateway**

Use AWS SAM or Serverless Framework to deploy Flask as Lambda function.

---

## 13. Cost Estimation

### Monthly Costs (Demonstration Environment)

| Service | Usage | Cost |
|---------|-------|------|
| **AWS Bedrock** | ~1000 API calls/month | $20-30 |
| **DynamoDB** | On-demand, 1GB storage | $5-10 |
| **S3** | 10GB storage + transfers | $1-5 |
| **Lambda** | 100 executions, 5min avg | $10-20 |
| **ECS Fargate** | 10 tasks, 30min avg | $20-30 |
| **CloudWatch** | Logs + metrics | $5-10 |
| **API Gateway** | 10,000 requests | $0.35 |
| **Secrets Manager** | 1 secret | $0.40 |
| **Data Transfer** | 10GB out | $0.90 |
| **Total** | | **$60-100/month** |

### Cost Optimization Tips

1. **Use On-Demand Pricing**: Start with on-demand, switch to reserved instances later
2. **Enable S3 Lifecycle Policies**: Archive old data to Glacier
3. **Use Lambda for Short Tasks**: Cheaper than ECS for <15min tasks
4. **Set CloudWatch Log Retention**: 7-30 days instead of forever
5. **Use Spot Instances for ECS**: 70% cheaper for non-critical workloads
6. **Enable Cost Alerts**: Set budget alerts at 80% of target

### Set Up Cost Alerts

```bash
# Create budget
aws budgets create-budget \
  --account-id YOUR-ACCOUNT-ID \
  --budget '{
    "BudgetName": "CloudForge-Monthly-Budget",
    "BudgetLimit": {
      "Amount": "100",
      "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {
          "SubscriptionType": "EMAIL",
          "Address": "your-email@example.com"
        }
      ]
    }
  ]'
```

---

## 14. Testing Your Setup

### Step 1: Verify AWS Services

```bash
# Test Bedrock
aws bedrock list-foundation-models --region us-east-1

# Test DynamoDB
aws dynamodb list-tables --region us-east-1

# Test S3
aws s3 ls

# Test Lambda
aws lambda list-functions --region us-east-1

# Test ECS
aws ecs list-clusters --region us-east-1
```

### Step 2: Deploy Infrastructure

```bash
cd infrastructure
npm install
npm run build

# Deploy all stacks
cdk deploy --all

# Or deploy individually
cdk deploy CloudForgeInfrastructureStack
cdk deploy CloudForgeComputeStack
cdk deploy CloudForgeMonitoringStack
```

### Step 3: Test API Locally

```bash
cd backend

# Set environment variables
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
export DYNAMODB_TABLE_WORKFLOWS=cloudforge-workflows
export S3_BUCKET_ARTIFACTS=cloudforge-artifacts-YOUR-ACCOUNT-ID

# Run API
python -m uvicorn cloudforge.api.main:app --reload --port 8000

# Test health endpoint
curl http://localhost:8000/health
```

### Step 4: Test Bedrock Integration

```bash
# Run a simple test
python - <<'EOF'
import boto3
import json

# Create Bedrock client
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# Test API call
request = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 100,
    "messages": [
        {
            "role": "user",
            "content": "Say hello!"
        }
    ]
}

response = bedrock.invoke_model(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    body=json.dumps(request)
)

result = json.loads(response['body'].read())
print(result['content'][0]['text'])
EOF
```

### Step 5: Run Full Workflow Test

```bash
# Use the example script
cd examples/api_examples
python basic_workflow.py
```

---

## Quick Start Checklist

Use this checklist to track your progress:

- [ ] AWS account created
- [ ] AWS CLI installed and configured
- [ ] AWS Bedrock access requested and approved
- [ ] IAM user created with proper permissions
- [ ] AWS CDK installed and bootstrapped
- [ ] DynamoDB tables created (or CDK deployed)
- [ ] S3 buckets created (or CDK deployed)
- [ ] Lambda functions deployed
- [ ] ECS cluster created
- [ ] API Gateway configured
- [ ] CloudWatch logging enabled
- [ ] Secrets Manager configured
- [ ] Custom domain configured (optional)
- [ ] Cost alerts set up
- [ ] Local testing successful
- [ ] Infrastructure deployed
- [ ] API accessible via public URL
- [ ] Web dashboard accessible

---

## Troubleshooting

### Issue: "Access Denied" when calling Bedrock

**Solution**:
1. Check model access in Bedrock console
2. Verify IAM permissions include `bedrock:InvokeModel`
3. Ensure you're using the correct region (us-east-1)

### Issue: CDK Bootstrap Fails

**Solution**:
```bash
# Delete existing bootstrap stack
aws cloudformation delete-stack --stack-name CDKToolkit --region us-east-1

# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name CDKToolkit --region us-east-1

# Bootstrap again
cdk bootstrap aws://ACCOUNT-ID/us-east-1
```

### Issue: DynamoDB Table Already Exists

**Solution**:
```bash
# Delete existing table
aws dynamodb delete-table --table-name cloudforge-workflows --region us-east-1

# Wait and redeploy
cdk deploy CloudForgeInfrastructureStack
```

### Issue: High Costs

**Solution**:
1. Check CloudWatch Logs retention (set to 7 days)
2. Enable S3 lifecycle policies
3. Use Lambda instead of ECS when possible
4. Set up cost alerts
5. Review CloudWatch metrics for usage patterns

---

## Next Steps

After completing this setup:

1. **Configure Application**: Update `backend/config.py` with your AWS resources
2. **Deploy Code**: Deploy your application code to Lambda/ECS
3. **Test End-to-End**: Run a complete workflow test
4. **Monitor**: Check CloudWatch dashboards
5. **Optimize**: Review costs and optimize based on usage

---

## Support Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **AWS Bedrock Docs**: https://docs.aws.amazon.com/bedrock/
- **AWS CDK Docs**: https://docs.aws.amazon.com/cdk/
- **AWS Support**: https://console.aws.amazon.com/support/
- **CloudForge Issues**: [Your GitHub repo]/issues

---

**Ready to proceed?** Start with Section 1 and work through each section in order. Each step builds on the previous one.
