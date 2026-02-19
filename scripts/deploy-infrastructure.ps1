# CloudForge Bug Intelligence - Infrastructure Deployment Script (PowerShell)
# This script deploys all AWS infrastructure using CDK

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "CloudForge Bug Intelligence Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if AWS CLI is installed
try {
    aws --version | Out-Null
} catch {
    Write-Host "Error: AWS CLI is not installed. Please install it first." -ForegroundColor Red
    exit 1
}

# Check if CDK is installed
try {
    cdk --version | Out-Null
} catch {
    Write-Host "Error: AWS CDK is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "  npm install -g aws-cdk" -ForegroundColor Yellow
    exit 1
}

# Check AWS credentials
Write-Host "Checking AWS credentials..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity | ConvertFrom-Json
    $accountId = $identity.Account
} catch {
    Write-Host "Error: AWS credentials not configured. Please run 'aws configure'" -ForegroundColor Red
    exit 1
}

$region = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }

Write-Host "Deploying to AWS Account: $accountId" -ForegroundColor Green
Write-Host "Region: $region" -ForegroundColor Green
Write-Host ""

# Navigate to infrastructure directory
Set-Location infrastructure

# Install dependencies if needed
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing CDK dependencies..." -ForegroundColor Yellow
    npm install
    Write-Host ""
}

# Bootstrap CDK (if not already done)
Write-Host "Bootstrapping CDK (if needed)..." -ForegroundColor Yellow
cdk bootstrap "aws://$accountId/$region"
Write-Host ""

# Build TypeScript
Write-Host "Building CDK stacks..." -ForegroundColor Yellow
npm run build
Write-Host ""

# Deploy infrastructure
Write-Host "Deploying CloudForge infrastructure stacks..." -ForegroundColor Cyan
Write-Host ""

# Deploy core infrastructure first
Write-Host "1/3 Deploying Core Infrastructure Stack..." -ForegroundColor Yellow
cdk deploy CloudForgeInfrastructureStack --require-approval never
Write-Host ""

# Deploy compute resources
Write-Host "2/3 Deploying Compute Resources Stack..." -ForegroundColor Yellow
cdk deploy CloudForgeComputeStack --require-approval never
Write-Host ""

# Deploy monitoring
Write-Host "3/3 Deploying Monitoring Stack..." -ForegroundColor Yellow
cdk deploy CloudForgeMonitoringStack --require-approval never
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Configure API credentials in AWS Secrets Manager"
Write-Host "2. Deploy backend application"
Write-Host "3. Access CloudWatch dashboard for monitoring"
Write-Host ""
