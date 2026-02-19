#!/bin/bash
# CloudForge Bug Intelligence - Infrastructure Deployment Script
# This script deploys all AWS infrastructure using CDK

set -e

echo "=========================================="
echo "CloudForge Bug Intelligence Deployment"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "Error: AWS CDK is not installed. Please install it first:"
    echo "  npm install -g aws-cdk"
    exit 1
fi

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured. Please run 'aws configure'"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_REGION:-us-east-1}

echo "Deploying to AWS Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Navigate to infrastructure directory
cd infrastructure

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing CDK dependencies..."
    npm install
    echo ""
fi

# Bootstrap CDK (if not already done)
echo "Bootstrapping CDK (if needed)..."
cdk bootstrap aws://$ACCOUNT_ID/$REGION
echo ""

# Build TypeScript
echo "Building CDK stacks..."
npm run build
echo ""

# Deploy infrastructure
echo "Deploying CloudForge infrastructure stacks..."
echo ""

# Deploy core infrastructure first
echo "1/3 Deploying Core Infrastructure Stack..."
cdk deploy CloudForgeInfrastructureStack --require-approval never
echo ""

# Deploy compute resources
echo "2/3 Deploying Compute Resources Stack..."
cdk deploy CloudForgeComputeStack --require-approval never
echo ""

# Deploy monitoring
echo "3/3 Deploying Monitoring Stack..."
cdk deploy CloudForgeMonitoringStack --require-approval never
echo ""

echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Configure API credentials in AWS Secrets Manager"
echo "2. Deploy backend application"
echo "3. Access CloudWatch dashboard for monitoring"
echo ""
