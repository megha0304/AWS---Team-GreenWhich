# CloudForge Bug Intelligence - Deployment Checklist

Use this checklist to track your deployment progress. Check off each item as you complete it.

## Phase 1: AWS Account Setup (30 minutes)

- [ ] **1.1** AWS account created and verified
- [ ] **1.2** Credit card added to AWS account
- [ ] **1.3** AWS CLI installed on your machine
- [ ] **1.4** AWS CLI configured with credentials (`aws configure`)
- [ ] **1.5** Verified AWS CLI works: `aws sts get-caller-identity`
- [ ] **1.6** Node.js 18+ installed for AWS CDK
- [ ] **1.7** Python 3.11+ installed for backend

**Verification Command**:
```bash
aws --version && node --version && python --version
```

---

## Phase 2: AWS Bedrock Setup (15 minutes)

- [ ] **2.1** Logged into AWS Console
- [ ] **2.2** Selected region: `us-east-1` (N. Virginia)
- [ ] **2.3** Navigated to AWS Bedrock service
- [ ] **2.4** Clicked "Model access" in sidebar
- [ ] **2.5** Requested access to "Anthropic Claude 3 Sonnet"
- [ ] **2.6** Waited for approval (refresh page after 30 seconds)
- [ ] **2.7** Verified status shows "Access granted"
- [ ] **2.8** Noted model ID: `anthropic.claude-3-sonnet-20240229-v1:0`

**Verification Command**:
```bash
aws bedrock list-foundation-models --region us-east-1 | grep claude
```

---

## Phase 3: IAM Permissions Setup (20 minutes)

- [ ] **3.1** Navigated to IAM in AWS Console
- [ ] **3.2** Created new IAM user: `cloudforge-admin`
- [ ] **3.3** Attached policy: `AmazonBedrockFullAccess`
- [ ] **3.4** Attached policy: `AmazonDynamoDBFullAccess`
- [ ] **3.5** Attached policy: `AmazonS3FullAccess`
- [ ] **3.6** Attached policy: `AWSLambda_FullAccess`
- [ ] **3.7** Attached policy: `AmazonECS_FullAccess`
- [ ] **3.8** Attached policy: `CloudWatchFullAccess`
- [ ] **3.9** Attached policy: `SecretsManagerReadWrite`
- [ ] **3.10** Attached policy: `IAMFullAccess`
- [ ] **3.11** Attached policy: `AmazonAPIGatewayAdministrator`
- [ ] **3.12** Created access keys for user
- [ ] **3.13** Downloaded access key CSV file
- [ ] **3.14** Configured AWS CLI profile: `aws configure --profile cloudforge`

**Verification Command**:
```bash
aws iam get-user --user-name cloudforge-admin --profile cloudforge
```

---

## Phase 4: AWS CDK Bootstrap (10 minutes)

- [ ] **4.1** Installed AWS CDK globally: `npm install -g aws-cdk`
- [ ] **4.2** Verified CDK installation: `cdk --version`
- [ ] **4.3** Got AWS account ID: `aws sts get-caller-identity --query Account --output text`
- [ ] **4.4** Noted account ID: `_________________`
- [ ] **4.5** Bootstrapped CDK: `cdk bootstrap aws://ACCOUNT-ID/us-east-1`
- [ ] **4.6** Verified bootstrap stack exists

**Verification Command**:
```bash
aws cloudformation describe-stacks --stack-name CDKToolkit --region us-east-1
```

---

## Phase 5: Project Setup (15 minutes)

- [ ] **5.1** Cloned CloudForge repository
- [ ] **5.2** Navigated to project directory
- [ ] **5.3** Installed Python dependencies: `cd backend && pip install -r requirements.txt`
- [ ] **5.4** Installed CDK dependencies: `cd infrastructure && npm install`
- [ ] **5.5** Copied config example: `cp backend/config.example.py backend/config.py`
- [ ] **5.6** Updated `backend/config.py` with AWS region and model ID
- [ ] **5.7** Built CDK project: `cd infrastructure && npm run build`

**Verification Command**:
```bash
cd infrastructure && npm run build && echo "Build successful"
```

---

## Phase 6: Infrastructure Deployment (30 minutes)

- [ ] **6.1** Navigated to infrastructure directory: `cd infrastructure`
- [ ] **6.2** Reviewed CDK stacks: `cdk list`
- [ ] **6.3** Synthesized CloudFormation: `cdk synth`
- [ ] **6.4** Deployed Core Infrastructure: `cdk deploy CloudForgeInfrastructureStack`
  - [ ] DynamoDB tables created
  - [ ] S3 buckets created
  - [ ] IAM roles created
  - [ ] KMS keys created
- [ ] **6.5** Deployed Compute Resources: `cdk deploy CloudForgeComputeStack`
  - [ ] Lambda functions created
  - [ ] ECS cluster created
  - [ ] VPC configured
- [ ] **6.6** Deployed Monitoring: `cdk deploy CloudForgeMonitoringStack`
  - [ ] CloudWatch dashboards created
  - [ ] Alarms configured
  - [ ] SNS topics created
- [ ] **6.7** Noted deployment outputs (API endpoints, bucket names, etc.)

**Verification Commands**:
```bash
aws dynamodb list-tables --region us-east-1
aws s3 ls
aws lambda list-functions --region us-east-1
aws ecs list-clusters --region us-east-1
```

---

## Phase 7: Secrets Manager Setup (10 minutes)

- [ ] **7.1** Created secret in Secrets Manager
- [ ] **7.2** Added Bedrock model ID to secret
- [ ] **7.3** Added API key to secret
- [ ] **7.4** Added Q Developer credentials (if available)
- [ ] **7.5** Noted secret ARN: `_________________`
- [ ] **7.6** Updated config to load from Secrets Manager

**Create Secret Command**:
```bash
aws secretsmanager create-secret \
  --name cloudforge/production/credentials \
  --secret-string '{
    "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "api_key": "your-secure-api-key-here"
  }' \
  --region us-east-1
```

**Verification Command**:
```bash
aws secretsmanager get-secret-value --secret-id cloudforge/production/credentials --region us-east-1
```

---

## Phase 8: Local Testing (20 minutes)

- [ ] **8.1** Set environment variables:
  ```bash
  export AWS_REGION=us-east-1
  export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
  ```
- [ ] **8.2** Started API locally: `cd backend && python -m uvicorn cloudforge.api.main:app --reload`
- [ ] **8.3** Tested health endpoint: `curl http://localhost:8000/health`
- [ ] **8.4** Tested Bedrock connection (see test script below)
- [ ] **8.5** Started web dashboard: `python run_web.py`
- [ ] **8.6** Accessed dashboard: http://localhost:5000
- [ ] **8.7** Ran unit tests: `pytest tests/unit/ -v`
- [ ] **8.8** Verified 338+ tests passing

**Bedrock Test Script**:
```python
import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

request = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Say hello!"}]
}

response = bedrock.invoke_model(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    body=json.dumps(request)
)

result = json.loads(response['body'].read())
print(result['content'][0]['text'])
```

---

## Phase 9: API Gateway & Domain Setup (30 minutes)

### Option A: Use Default API Gateway URL (Quick)

- [ ] **9A.1** Deployed API stack: `cdk deploy CloudForgeApiStack`
- [ ] **9A.2** Noted API Gateway URL from output
- [ ] **9A.3** Tested API: `curl https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/health`
- [ ] **9A.4** Updated frontend to use API URL

### Option B: Custom Domain (Professional)

- [ ] **9B.1** Registered domain name: `_________________`
- [ ] **9B.2** Requested SSL certificate in ACM for `api.yourdomain.com`
- [ ] **9B.3** Validated certificate via DNS
- [ ] **9B.4** Created custom domain in API Gateway
- [ ] **9B.5** Mapped API to custom domain
- [ ] **9B.6** Added CNAME record in DNS
- [ ] **9B.7** Waited for DNS propagation (5-30 minutes)
- [ ] **9B.8** Tested custom domain: `curl https://api.yourdomain.com/health`

---

## Phase 10: Web Dashboard Hosting (30 minutes)

### Option A: S3 + CloudFront (Static)

- [ ] **10A.1** Created S3 bucket for website
- [ ] **10A.2** Enabled static website hosting
- [ ] **10A.3** Uploaded web files to S3
- [ ] **10A.4** Created CloudFront distribution
- [ ] **10A.5** Configured SSL certificate
- [ ] **10A.6** Added custom domain to CloudFront
- [ ] **10A.7** Updated DNS with CloudFront domain
- [ ] **10A.8** Tested website: `https://app.yourdomain.com`

### Option B: Elastic Beanstalk (Dynamic)

- [ ] **10B.1** Installed EB CLI: `pip install awsebcli`
- [ ] **10B.2** Initialized EB: `eb init -p python-3.11 cloudforge-web`
- [ ] **10B.3** Created environment: `eb create cloudforge-web-prod`
- [ ] **10B.4** Deployed app: `eb deploy`
- [ ] **10B.5** Got URL: `eb status`
- [ ] **10B.6** Tested website

### Option C: Lambda + API Gateway (Serverless)

- [ ] **10C.1** Packaged Flask app for Lambda
- [ ] **10C.2** Created Lambda function
- [ ] **10C.3** Configured API Gateway integration
- [ ] **10C.4** Deployed and tested

---

## Phase 11: Monitoring Setup (15 minutes)

- [ ] **11.1** Opened CloudWatch console
- [ ] **11.2** Verified log groups exist:
  - [ ] `/aws/lambda/cloudforge-*`
  - [ ] `/aws/ecs/cloudforge-*`
  - [ ] `/aws/cloudforge/bug-intelligence`
- [ ] **11.3** Checked CloudWatch dashboards
- [ ] **11.4** Verified alarms are configured
- [ ] **11.5** Subscribed to SNS topics for alerts
- [ ] **11.6** Set up cost budget alerts
- [ ] **11.7** Configured log retention (7-30 days)

**Create Budget Command**:
```bash
aws budgets create-budget \
  --account-id YOUR-ACCOUNT-ID \
  --budget '{
    "BudgetName": "CloudForge-Monthly",
    "BudgetLimit": {"Amount": "100", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }'
```

---

## Phase 12: End-to-End Testing (30 minutes)

- [ ] **12.1** Ran example workflow: `python examples/api_examples/basic_workflow.py`
- [ ] **12.2** Verified workflow created in DynamoDB
- [ ] **12.3** Checked CloudWatch logs for agent execution
- [ ] **12.4** Verified bugs detected (or mock mode working)
- [ ] **12.5** Checked test results in S3
- [ ] **12.6** Verified API responses
- [ ] **12.7** Tested web dashboard workflow view
- [ ] **12.8** Exported results (JSON/CSV)
- [ ] **12.9** Verified all 5 agents executed
- [ ] **12.10** Checked CloudWatch metrics

---

## Phase 13: Production Readiness (20 minutes)

- [ ] **13.1** Reviewed IAM policies for least privilege
- [ ] **13.2** Enabled MFA on AWS account
- [ ] **13.3** Configured backup for DynamoDB tables
- [ ] **13.4** Set up S3 lifecycle policies
- [ ] **13.5** Enabled CloudTrail for audit logging
- [ ] **13.6** Configured VPC security groups
- [ ] **13.7** Set up WAF rules for API Gateway (optional)
- [ ] **13.8** Documented API keys and credentials
- [ ] **13.9** Created runbook for common issues
- [ ] **13.10** Set up monitoring alerts

---

## Phase 14: Documentation & Sharing (15 minutes)

- [ ] **14.1** Documented API endpoint URL
- [ ] **14.2** Documented web dashboard URL
- [ ] **14.3** Created user guide
- [ ] **14.4** Shared credentials securely with team
- [ ] **14.5** Created demo video/screenshots
- [ ] **14.6** Updated README with deployment info
- [ ] **14.7** Shared shareable links:
  - API: `_________________`
  - Dashboard: `_________________`

---

## Troubleshooting Checklist

If something doesn't work, check these:

- [ ] AWS credentials are configured correctly
- [ ] AWS region is set to `us-east-1`
- [ ] Bedrock model access is granted
- [ ] IAM permissions are correct
- [ ] CDK is bootstrapped
- [ ] All stacks deployed successfully
- [ ] Environment variables are set
- [ ] Secrets Manager secret exists
- [ ] DynamoDB tables exist
- [ ] S3 buckets exist
- [ ] Lambda functions deployed
- [ ] API Gateway configured
- [ ] CloudWatch logs are being written
- [ ] No errors in CloudWatch logs
- [ ] Cost budget not exceeded

---

## Quick Reference

### Important URLs

- AWS Console: https://console.aws.amazon.com
- Bedrock Console: https://console.aws.amazon.com/bedrock
- DynamoDB Console: https://console.aws.amazon.com/dynamodb
- CloudWatch Console: https://console.aws.amazon.com/cloudwatch
- API Gateway Console: https://console.aws.amazon.com/apigateway

### Important Commands

```bash
# Check AWS identity
aws sts get-caller-identity

# List Bedrock models
aws bedrock list-foundation-models --region us-east-1

# Deploy all CDK stacks
cd infrastructure && cdk deploy --all

# Run local API
cd backend && python -m uvicorn cloudforge.api.main:app --reload

# Run tests
cd backend && pytest tests/unit/ -v

# Check CloudWatch logs
aws logs tail /aws/lambda/cloudforge-test-executor --follow
```

### Your Deployment Info

Fill this in as you deploy:

- **AWS Account ID**: `_________________`
- **AWS Region**: `us-east-1`
- **Bedrock Model ID**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **API Gateway URL**: `_________________`
- **Custom API Domain**: `_________________`
- **Web Dashboard URL**: `_________________`
- **DynamoDB Workflows Table**: `cloudforge-workflows`
- **DynamoDB Bugs Table**: `cloudforge-bugs`
- **S3 Artifacts Bucket**: `_________________`
- **Secrets Manager Secret**: `cloudforge/production/credentials`

---

## Estimated Time

- **Minimum (using defaults)**: 2-3 hours
- **With custom domain**: 3-4 hours
- **Full production setup**: 4-6 hours

---

## Next Steps After Deployment

1. **Monitor Costs**: Check AWS Cost Explorer daily for first week
2. **Review Logs**: Check CloudWatch logs for errors
3. **Test Thoroughly**: Run multiple workflows to verify stability
4. **Optimize**: Adjust Lambda memory, ECS CPU based on actual usage
5. **Document**: Keep this checklist updated with your specific configuration
6. **Share**: Provide team members with access and documentation

---

**Congratulations!** 🎉

Once all items are checked, your CloudForge Bug Intelligence platform is fully deployed and accessible via shareable links!
