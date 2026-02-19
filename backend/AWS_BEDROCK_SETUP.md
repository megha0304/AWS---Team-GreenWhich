# AWS Bedrock Setup Guide - Quick Reference

**For complete AWS setup including hosting, see: `../AWS_COMPLETE_SETUP_GUIDE.md`**

This is a quick reference for AWS Bedrock setup only.

This guide explains how to configure AWS Bedrock for the CloudForge Bug Intelligence platform.

## Overview

The Bug Detective Agent uses AWS Bedrock with Claude 3 Sonnet to analyze code and detect bugs. This document explains what you need to set up.

## Prerequisites

- AWS Account with billing enabled
- AWS CLI installed (optional but recommended)
- Python 3.11+ with boto3 installed

## Step 1: AWS Credentials

You need AWS credentials to access Bedrock. Choose ONE of these methods:

### Option A: Environment Variables (Recommended for Development)

```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_REGION="us-east-1"  # or your preferred region
```

### Option B: AWS CLI Profile

```bash
# Configure AWS CLI
aws configure

# Or use a named profile
aws configure --profile cloudforge
export AWS_PROFILE="cloudforge"
```

### Option C: IAM Role (For Production on AWS)

If running on EC2, ECS, or Lambda, attach an IAM role with Bedrock permissions.

## Step 2: Request Bedrock Model Access

**IMPORTANT**: You must request access to Claude models before you can use them.

1. Go to AWS Console: https://console.aws.amazon.com/bedrock/
2. Navigate to: **Bedrock** > **Model access**
3. Click **"Modify model access"** or **"Request model access"**
4. Find and select: **Anthropic - Claude 3 Sonnet**
   - Model ID: `anthropic.claude-3-sonnet-20240229-v1:0`
5. Click **"Request model access"** or **"Save changes"**
6. Wait for approval (usually instant for Claude models)

### Verify Model Access

```bash
# List available models
aws bedrock list-foundation-models --region us-east-1

# Check if Claude 3 Sonnet is available
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[?contains(modelId, 'claude-3-sonnet')]"
```

## Step 3: IAM Permissions

Your AWS user/role needs these permissions:

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
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
      ]
    }
  ]
}
```

### Create IAM Policy (Optional)

```bash
# Create policy file
cat > bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
    }
  ]
}
EOF

# Create the policy
aws iam create-policy \
  --policy-name CloudForgeBedrock Access \
  --policy-document file://bedrock-policy.json

# Attach to your user (replace YOUR_USERNAME)
aws iam attach-user-policy \
  --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/CloudForgeBedrockAccess
```

## Step 4: Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
# BEDROCK_ENDPOINT_URL=https://bedrock-runtime.us-east-1.amazonaws.com  # Optional

# Agent Configuration
MAX_RETRIES=3
MAX_FILES_PER_BATCH=100
```

### Using AWS Secrets Manager (Production)

For production, store credentials in AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name cloudforge/config \
  --secret-string '{
    "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "aws_region": "us-east-1"
  }'

# Set environment variable to use Secrets Manager
export SECRETS_MANAGER_SECRET_NAME=cloudforge/config
```

## Step 5: Test Bedrock Connection

Create a test script to verify your setup:

```python
# test_bedrock.py
import boto3
import json

# Initialize Bedrock client
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

# Test request
request_body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 100,
    "messages": [
        {
            "role": "user",
            "content": "Say 'Hello from Bedrock!'"
        }
    ]
}

try:
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    print("✓ Bedrock connection successful!")
    print(f"Response: {response_body['content'][0]['text']}")
    
except Exception as e:
    print(f"✗ Bedrock connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check AWS credentials are configured")
    print("2. Verify model access is granted in Bedrock console")
    print("3. Confirm IAM permissions include bedrock:InvokeModel")
```

Run the test:

```bash
cd backend
python test_bedrock.py
```

## Step 6: Enable Real Bedrock Integration

Once your AWS setup is complete:

1. Open `backend/cloudforge/agents/bug_detective.py`
2. Find the `_call_bedrock_for_bugs` method
3. Uncomment the Bedrock API call code (marked with TODO)
4. Remove or comment out the placeholder return statement

## Cost Considerations

### Claude 3 Sonnet Pricing (as of 2024)

- Input: $3.00 per million tokens (~750,000 words)
- Output: $15.00 per million tokens (~750,000 words)

### Estimated Costs

For a typical repository:
- Small repo (100 files, 10K lines): ~$0.10 - $0.50
- Medium repo (1,000 files, 100K lines): ~$1.00 - $5.00
- Large repo (10,000 files, 1M lines): ~$10.00 - $50.00

### Cost Management

The system includes several cost management features:
- Batching for large repositories (>10,000 files)
- Configurable batch size
- Rate limiting (configured in SystemConfig)
- Token limits per request (5000 chars = ~1250 tokens)

## Troubleshooting

### Error: "Could not connect to the endpoint URL"

**Solution**: Check your AWS region and endpoint URL.

```bash
# Verify region
aws configure get region

# Test endpoint
curl https://bedrock-runtime.us-east-1.amazonaws.com
```

### Error: "AccessDeniedException"

**Solution**: Request model access in Bedrock console (Step 2).

### Error: "ValidationException: The provided model identifier is invalid"

**Solution**: Verify the model ID is correct and available in your region.

```bash
# List available models in your region
aws bedrock list-foundation-models --region us-east-1
```

### Error: "ThrottlingException"

**Solution**: You're hitting rate limits. The system will automatically retry with exponential backoff.

## Regions with Bedrock Support

Claude 3 Sonnet is available in these regions:
- us-east-1 (N. Virginia) ✓ Recommended
- us-west-2 (Oregon)
- eu-west-1 (Ireland)
- ap-southeast-1 (Singapore)
- ap-northeast-1 (Tokyo)

Check current availability: https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html

## Alternative: Use Mock Mode for Development

If you're not ready to set up AWS Bedrock yet, the agent will run in mock mode:
- Returns empty bug list
- Logs warning messages
- Useful for testing other components

To use mock mode, simply don't configure AWS credentials. The agent will detect this and use placeholder logic.

## Next Steps

After setting up Bedrock:
1. Run the test script to verify connection
2. Enable real Bedrock integration in `bug_detective.py`
3. Test with a small repository first
4. Monitor costs in AWS Cost Explorer
5. Adjust batch size and rate limits as needed

## Support

For AWS Bedrock issues:
- AWS Bedrock Documentation: https://docs.aws.amazon.com/bedrock/
- AWS Support: https://console.aws.amazon.com/support/

For CloudForge issues:
- Check application logs in `backend/logs/`
- Review CloudWatch logs (if deployed to AWS)
