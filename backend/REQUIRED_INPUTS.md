# Required Inputs for CloudForge Bug Intelligence

## Quick Start: What You Need to Provide

### 1. AWS Credentials (REQUIRED for Bedrock)

Choose ONE method:

**Method A: Environment Variables** (Easiest for development)
```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="wJalrXUtn..."
export AWS_REGION="us-east-1"
```

**Method B: AWS CLI Profile**
```bash
aws configure
# Enter your credentials when prompted
```

**Method C: IAM Role** (For production on AWS)
- Attach IAM role to EC2/ECS/Lambda with Bedrock permissions

---

### 2. Bedrock Model Access (REQUIRED - One-time setup)

**Action Required:**
1. Go to: https://console.aws.amazon.com/bedrock/
2. Click: **Model access** (left sidebar)
3. Click: **Modify model access** button
4. Select: **Anthropic - Claude 3 Sonnet**
5. Click: **Request model access**
6. Wait: ~30 seconds for approval

**Model ID**: `anthropic.claude-3-sonnet-20240229-v1:0`

---

### 3. IAM Permissions (REQUIRED)

Your AWS user/role needs permission to invoke Bedrock models.

**Minimum Required Permissions:**
```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel"],
  "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
}
```

---

### 4. Configuration File (OPTIONAL)

Create `backend/.env`:

```bash
# AWS Settings
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key-here
AWS_SECRET_ACCESS_KEY=your-secret-here

# Bedrock Settings
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Agent Settings (optional - has defaults)
MAX_RETRIES=3
MAX_FILES_PER_BATCH=100
```

---

## Testing Your Setup

### Quick Test Script

```python
# Save as: backend/test_bedrock_connection.py
import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

try:
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "Say hello"}]
        })
    )
    print("✓ SUCCESS: Bedrock is configured correctly!")
except Exception as e:
    print(f"✗ FAILED: {e}")
```

Run it:
```bash
cd backend
python test_bedrock_connection.py
```

---

## Cost Estimate

**Claude 3 Sonnet Pricing:**
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens

**Typical Repository Costs:**
- Small (100 files): $0.10 - $0.50
- Medium (1,000 files): $1 - $5
- Large (10,000 files): $10 - $50

---

## What Happens If You Don't Configure AWS?

The system will run in **MOCK MODE**:
- ✓ No errors - system continues to work
- ✓ Useful for testing other components
- ✗ No actual bug detection (returns empty results)
- ⚠️  Warning messages in logs

---

## Enabling Real Bedrock Integration

After AWS setup is complete:

1. **Verify connection** with test script above
2. **Edit file**: `backend/cloudforge/agents/bug_detective.py`
3. **Find method**: `_call_bedrock_for_bugs`
4. **Uncomment**: The Bedrock API call code (marked with TODO)
5. **Remove**: The placeholder return statement

---

## Summary Checklist

- [ ] AWS credentials configured (environment variables or AWS CLI)
- [ ] Bedrock model access requested and approved
- [ ] IAM permissions granted (bedrock:InvokeModel)
- [ ] Test script runs successfully
- [ ] (Optional) .env file created with configuration
- [ ] (Optional) Uncommented real Bedrock code in bug_detective.py

---

## Need Help?

**See detailed guide**: `backend/AWS_BEDROCK_SETUP.md`

**Common Issues:**
- "AccessDeniedException" → Request model access in Bedrock console
- "Could not connect" → Check AWS region and credentials
- "ValidationException" → Verify model ID is correct

**AWS Documentation:**
- Bedrock: https://docs.aws.amazon.com/bedrock/
- Claude Models: https://docs.anthropic.com/claude/docs
