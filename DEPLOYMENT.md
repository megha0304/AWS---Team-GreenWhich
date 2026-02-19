# CloudForge Bug Intelligence - Deployment Guide

This guide covers deploying the CloudForge Bug Intelligence platform to AWS.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Node.js** (v18+) and npm
4. **Python** (3.11+) and pip
5. **AWS CDK** installed globally: `npm install -g aws-cdk`

## Deployment Steps

### 1. Infrastructure Deployment

Deploy the AWS infrastructure using CDK:

**Linux/Mac:**
```bash
chmod +x scripts/deploy-infrastructure.sh
./scripts/deploy-infrastructure.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\deploy-infrastructure.ps1
```

This will deploy three CDK stacks:
- **CloudForgeInfrastructureStack**: DynamoDB tables, S3 buckets, IAM roles, Secrets Manager
- **CloudForgeComputeStack**: Lambda functions, ECS cluster, VPC
- **CloudForgeMonitoringStack**: CloudWatch dashboards, alarms, SNS topics

### 2. Configure API Credentials

After infrastructure deployment, configure API credentials in AWS Secrets Manager:

```bash
# Update the secret with your API credentials
aws secretsmanager update-secret \
  --secret-id cloudforge/api-credentials \
  --secret-string '{
    "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "q_developer_endpoint": "https://api.amazonq.aws.dev",
    "api_key": "your-api-key-here"
  }'
```

### 3. Deploy Backend Application

#### Option A: Deploy to Lambda (Recommended for API)

The API Lambda function is already deployed by the CDK stack. To update it:

```bash
cd backend
pip install -r requirements.txt -t lambda_package/
cp -r cloudforge lambda_package/
cd lambda_package
zip -r ../cloudforge-api.zip .
cd ..

aws lambda update-function-code \
  --function-name cloudforge-api \
  --zip-file fileb://cloudforge-api.zip
```

#### Option B: Run Locally for Development

```bash
cd backend
pip install -r requirements.txt
python -m cloudforge.web.app
```

Access the web interface at `http://localhost:5000`

### 4. Verify Deployment

Check that all resources are deployed:

```bash
# List CloudFormation stacks
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE

# Check DynamoDB tables
aws dynamodb list-tables

# Check S3 buckets
aws s3 ls | grep cloudforge

# Check Lambda functions
aws lambda list-functions | grep cloudforge
```

### 5. Access CloudWatch Dashboard

View the monitoring dashboard:

```bash
# Get dashboard URL from stack outputs
aws cloudformation describe-stacks \
  --stack-name CloudForgeMonitoringStack \
  --query 'Stacks[0].Outputs[?OutputKey==`DashboardUrl`].OutputValue' \
  --output text
```

## Configuration

### Environment Variables

Set these environment variables for local development:

```bash
export AWS_REGION=us-east-1
export WORKFLOWS_TABLE=cloudforge-workflows
export BUGS_TABLE=cloudforge-bugs
export ARTIFACTS_BUCKET=cloudforge-artifacts-<account-id>-<region>
export API_SECRET_ARN=arn:aws:secretsmanager:<region>:<account-id>:secret:cloudforge/api-credentials
export LOG_LEVEL=INFO
```

### Cost Management

The platform is designed to stay under $100/month for demonstration environments:

- DynamoDB uses on-demand billing
- S3 has lifecycle policies (30-day Glacier transition, 90-day expiration)
- Lambda functions have appropriate memory/timeout limits
- CloudWatch alarms monitor costs

Set up cost alerts:

```bash
# The monitoring stack already creates cost alarms
# Optionally, subscribe to the alert topic:
aws sns subscribe \
  --topic-arn <alert-topic-arn> \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Updating the Deployment

To update infrastructure:

```bash
cd infrastructure
npm run build
cdk diff  # Preview changes
cdk deploy --all
```

To update backend code:

```bash
# Update Lambda function
cd backend
# ... package code ...
aws lambda update-function-code \
  --function-name cloudforge-api \
  --zip-file fileb://cloudforge-api.zip
```

## Rollback

If deployment fails or you need to rollback:

```bash
# Rollback a specific stack
aws cloudformation rollback-stack --stack-name CloudForgeComputeStack

# Or delete and redeploy
cdk destroy CloudForgeMonitoringStack
cdk destroy CloudForgeComputeStack
cdk destroy CloudForgeInfrastructureStack
```

## Troubleshooting

### CDK Bootstrap Issues

If you encounter bootstrap errors:

```bash
cdk bootstrap aws://<account-id>/<region> --force
```

### Lambda Deployment Errors

Check Lambda logs:

```bash
aws logs tail /aws/lambda/cloudforge-api --follow
```

### DynamoDB Access Issues

Verify IAM roles have correct permissions:

```bash
aws iam get-role --role-name cloudforge-api-lambda-role
```

### S3 Access Issues

Check bucket policy and encryption settings:

```bash
aws s3api get-bucket-policy --bucket cloudforge-artifacts-<account-id>-<region>
```

## Security Considerations

1. **IAM Roles**: All roles follow least privilege principle
2. **Encryption**: Data encrypted at rest (KMS) and in transit (TLS 1.2+)
3. **VPC**: ECS tasks run in private subnets
4. **Secrets**: API keys stored in Secrets Manager
5. **Logging**: All actions logged to CloudWatch

## Monitoring

Access monitoring resources:

- **CloudWatch Dashboard**: View metrics and performance
- **CloudWatch Logs**: `/cloudforge/*` log groups
- **CloudWatch Alarms**: Configured for errors, failures, and costs
- **SNS Notifications**: Critical alerts sent via email

## Next Steps

After deployment:

1. Test the API endpoints
2. Run a sample workflow
3. Review CloudWatch metrics
4. Configure additional alarms if needed
5. Set up CI/CD pipeline for automated deployments

## Support

For issues or questions:
- Check CloudWatch logs for errors
- Review the design document for architecture details
- Consult AWS documentation for service-specific issues
