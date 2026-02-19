# Get Started with CloudForge Bug Intelligence

Welcome! This guide will help you get CloudForge Bug Intelligence up and running with AWS Bedrock, proper data storage, and a shareable hosted link.

## 📚 Documentation Overview

We've created comprehensive guides for you:

### 1. **AWS_COMPLETE_SETUP_GUIDE.md** ⭐ START HERE
   - **Complete AWS setup from scratch**
   - AWS Bedrock configuration
   - DynamoDB, S3, Lambda, ECS setup
   - API Gateway and custom domain
   - CloudWatch monitoring
   - Cost estimation and optimization
   - **Time**: 3-4 hours

### 2. **DEPLOYMENT_CHECKLIST.md** ✅ TRACK PROGRESS
   - Step-by-step checklist
   - Check off items as you complete them
   - Troubleshooting tips
   - Quick reference commands
   - **Use this alongside the setup guide**

### 3. **DEPLOYMENT.md** 📖 DETAILED REFERENCE
   - Detailed deployment procedures
   - Infrastructure as Code (CDK)
   - Blue-green deployment
   - Rollback procedures
   - **Reference when deploying**

### 4. **README.md** 📘 PROJECT OVERVIEW
   - Project architecture
   - Quick start guide
   - API documentation
   - Usage examples
   - **Read for understanding the system**

## 🚀 Quick Start Path

Follow this path to get up and running:

### Step 1: Prerequisites (30 minutes)
```bash
# Install required tools
# - AWS CLI
# - Node.js 18+
# - Python 3.11+
# - AWS CDK

# Verify installations
aws --version
node --version
python --version
cdk --version
```

### Step 2: AWS Account Setup (30 minutes)
1. Create AWS account (if you don't have one)
2. Configure AWS CLI: `aws configure`
3. Request AWS Bedrock access (see AWS_COMPLETE_SETUP_GUIDE.md Section 2)
4. Create IAM user with permissions (see Section 3)

### Step 3: Deploy Infrastructure (30 minutes)
```bash
# Bootstrap CDK
cdk bootstrap aws://YOUR-ACCOUNT-ID/us-east-1

# Deploy infrastructure
cd infrastructure
npm install
npm run build
cdk deploy --all
```

### Step 4: Configure Application (15 minutes)
```bash
# Copy config
cd backend
cp config.example.py config.py

# Edit config.py with your AWS settings
# - AWS region
# - Bedrock model ID
# - DynamoDB table names
# - S3 bucket names
```

### Step 5: Test Locally (20 minutes)
```bash
# Install dependencies
pip install -r requirements.txt

# Run API
python -m uvicorn cloudforge.api.main:app --reload

# In another terminal, run web dashboard
python run_web.py

# Test
curl http://localhost:8000/health
```

### Step 6: Deploy to AWS (30 minutes)
```bash
# Deploy API to Lambda/API Gateway
# See DEPLOYMENT.md for detailed steps

# Deploy web dashboard
# Options: S3+CloudFront, Elastic Beanstalk, or Lambda
```

### Step 7: Get Your Shareable Links 🎉
After deployment, you'll have:
- **API**: `https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod`
- **Dashboard**: `https://YOUR-CLOUDFRONT-DOMAIN.cloudfront.net`
- **Custom Domain** (optional): `https://api.yourdomain.com` and `https://app.yourdomain.com`

## 📋 What You'll Need

### AWS Resources
- ✅ AWS Account with billing enabled
- ✅ AWS Bedrock access (Claude 3 Sonnet)
- ✅ IAM user with admin permissions
- ✅ DynamoDB tables for data storage
- ✅ S3 buckets for artifacts
- ✅ Lambda functions for test execution
- ✅ ECS cluster for long-running tests
- ✅ API Gateway for public API
- ✅ CloudWatch for monitoring

### Optional (for custom domain)
- 🌐 Domain name (from Route 53 or external registrar)
- 🔒 SSL certificate (from AWS Certificate Manager)

## 💰 Cost Estimate

**Demonstration Environment**: $60-100/month

Breakdown:
- AWS Bedrock (Claude): $20-30
- DynamoDB: $5-10
- S3: $1-5
- Lambda: $10-20
- ECS: $20-30
- CloudWatch: $5-10
- Other services: $5-10

**Free Tier**: Some services have free tier for first 12 months.

## 🎯 Your Goal

By the end of this setup, you'll have:

1. ✅ **Fully functional bug detection system**
   - AI-powered bug detection with AWS Bedrock
   - Automated test generation
   - Test execution on AWS infrastructure
   - Root cause analysis
   - Fix suggestions

2. ✅ **Data persistence**
   - Workflows stored in DynamoDB
   - Test results in S3
   - Logs in CloudWatch

3. ✅ **Public access**
   - REST API accessible via HTTPS
   - Web dashboard accessible via browser
   - Shareable links for demos

4. ✅ **Production-ready**
   - Monitoring and alerts
   - Cost tracking
   - Security best practices
   - Scalable infrastructure

## 📖 Recommended Reading Order

1. **First**: Read this file (GET_STARTED.md) - you're here! ✓
2. **Second**: Open AWS_COMPLETE_SETUP_GUIDE.md and start Section 1
3. **Third**: Use DEPLOYMENT_CHECKLIST.md to track your progress
4. **Reference**: Keep DEPLOYMENT.md and README.md open for details

## 🆘 Need Help?

### Common Issues

**"Access Denied" when calling Bedrock**
- Solution: Check Bedrock model access in AWS Console
- See: AWS_COMPLETE_SETUP_GUIDE.md Section 2

**"Table already exists" error**
- Solution: Delete existing table or use different name
- See: DEPLOYMENT_CHECKLIST.md Troubleshooting

**High AWS costs**
- Solution: Check CloudWatch metrics, enable lifecycle policies
- See: AWS_COMPLETE_SETUP_GUIDE.md Section 13

### Support Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **AWS Bedrock Docs**: https://docs.aws.amazon.com/bedrock/
- **Project Issues**: [Your GitHub repo]/issues
- **AWS Support**: https://console.aws.amazon.com/support/

## 🎓 Learning Path

### Beginner (Never used AWS)
1. Start with AWS_COMPLETE_SETUP_GUIDE.md
2. Follow every step carefully
3. Use DEPLOYMENT_CHECKLIST.md to track progress
4. Estimated time: 4-6 hours

### Intermediate (Familiar with AWS)
1. Skim AWS_COMPLETE_SETUP_GUIDE.md
2. Focus on Bedrock setup (Section 2)
3. Deploy infrastructure with CDK
4. Estimated time: 2-3 hours

### Advanced (AWS Expert)
1. Review DEPLOYMENT.md
2. Deploy CDK stacks: `cdk deploy --all`
3. Configure Bedrock and test
4. Estimated time: 1-2 hours

## 🔄 Development Workflow

### Local Development
```bash
# 1. Start API
cd backend
python -m uvicorn cloudforge.api.main:app --reload

# 2. Start web dashboard
python run_web.py

# 3. Run tests
pytest tests/unit/ -v

# 4. Make changes and test
```

### Deploy Changes
```bash
# 1. Update code
# 2. Run tests
pytest tests/

# 3. Deploy infrastructure changes
cd infrastructure
cdk deploy

# 4. Deploy application code
# (Lambda: update function code)
# (ECS: push new Docker image)
```

## 📊 Success Metrics

You'll know you're successful when:

- ✅ AWS Bedrock returns bug analysis (not mock data)
- ✅ Workflows are saved to DynamoDB
- ✅ Test results are stored in S3
- ✅ API is accessible via public URL
- ✅ Web dashboard shows real data
- ✅ CloudWatch shows logs and metrics
- ✅ Costs are within budget ($60-100/month)
- ✅ You can share links with others

## 🎉 Next Steps After Setup

1. **Test thoroughly**: Run multiple workflows
2. **Monitor costs**: Check AWS Cost Explorer daily
3. **Optimize**: Adjust resources based on usage
4. **Document**: Keep notes on your configuration
5. **Share**: Provide access to team members
6. **Iterate**: Add features and improvements

## 📝 Quick Commands Reference

```bash
# AWS
aws sts get-caller-identity                    # Check AWS identity
aws bedrock list-foundation-models             # List Bedrock models
aws dynamodb list-tables                       # List DynamoDB tables
aws s3 ls                                      # List S3 buckets

# CDK
cdk bootstrap                                  # Bootstrap CDK
cdk list                                       # List stacks
cdk synth                                      # Synthesize CloudFormation
cdk deploy --all                               # Deploy all stacks
cdk destroy --all                              # Delete all stacks

# Application
python -m uvicorn cloudforge.api.main:app      # Run API
python run_web.py                              # Run web dashboard
pytest tests/unit/ -v                          # Run tests
python examples/api_examples/basic_workflow.py # Run example

# Monitoring
aws logs tail /aws/lambda/cloudforge-* --follow  # Tail Lambda logs
aws cloudwatch get-metric-statistics ...         # Get metrics
```

## 🗺️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         User/Browser                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              API Gateway (Public HTTPS Endpoint)             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│                    (Lambda or ECS)                           │
└─────┬──────────────────────────────────────────────┬────────┘
      │                                               │
      ▼                                               ▼
┌──────────────────┐                        ┌──────────────────┐
│  AWS Bedrock     │                        │   DynamoDB       │
│  (Claude AI)     │                        │   (State Store)  │
│                  │                        │                  │
│  • Bug Detection │                        │  • Workflows     │
│  • Root Cause    │                        │  • Bugs          │
│    Analysis      │                        │  • Results       │
└──────────────────┘                        └──────────────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │       S3         │
                                            │   (Artifacts)    │
                                            │                  │
                                            │  • Test Results  │
                                            │  • Logs          │
                                            │  • Reports       │
                                            └──────────────────┘
```

## 🎯 Your Mission

**Get CloudForge Bug Intelligence deployed to AWS with:**
1. Real AWS Bedrock integration (not mock mode)
2. Data stored in DynamoDB and S3
3. Tests running on Lambda/ECS
4. Public API accessible via HTTPS
5. Web dashboard accessible via browser
6. Shareable links for demos

**Start here**: Open `AWS_COMPLETE_SETUP_GUIDE.md` and begin with Section 1!

---

**Good luck! 🚀 You've got this!**

Questions? Check the troubleshooting sections in each guide or open an issue.
