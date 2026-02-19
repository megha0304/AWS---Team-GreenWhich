# CloudForge Bug Intelligence - Quick Reference Card

## 🎯 I Want To...

### Get Started
- **Set up everything** → [`AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md`](AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)
- **Understand what to do** → [`NEXT_STEPS.md`](NEXT_STEPS.md)
- **See project status** → [`SETUP_SUMMARY.md`](SETUP_SUMMARY.md)

### Deploy
- **Get a shareable link** → [`SIMPLE_DEPLOYMENT.md`](SIMPLE_DEPLOYMENT.md)
- **Deploy to AWS** → [`AWS_COMPLETE_SETUP_GUIDE.md`](AWS_COMPLETE_SETUP_GUIDE.md)
- **Track deployment progress** → [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md)

### Use the API
- **API documentation** → [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md)
- **Example workflows** → [`examples/README.md`](examples/README.md)
- **Basic API usage** → [`examples/api_examples/basic_workflow.py`](examples/api_examples/basic_workflow.py)

### Understand the System
- **Architecture overview** → [`GET_STARTED.md`](GET_STARTED.md)
- **How it works** → [`README.md`](README.md)
- **Project structure** → [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)

---

## ⚡ Quick Commands

### Local Development
```bash
# Install
cd backend && pip install -r requirements.txt

# Run API
python -m uvicorn cloudforge.api.main:app --reload --port 8000

# Run tests
pytest

# Check code
ruff check . && black --check .
```

### AWS Setup
```bash
# Configure
aws configure

# Test Bedrock
aws bedrock list-foundation-models --region us-east-1

# Create tables
aws dynamodb create-table --table-name cloudforge-workflows ...
```

### Deployment
```bash
# CDK
cd infrastructure && cdk deploy --all

# Render
git push origin main

# Railway
railway up
```

---

## 📊 Project Status

| Component | Status |
|-----------|--------|
| Core Models | ✅ Complete |
| Agents | ✅ Complete (needs AWS config) |
| API | ✅ Complete |
| Web Dashboard | ✅ Complete |
| Infrastructure Code | ✅ Complete |
| Tests | ✅ 338/340 passing (99.4%) |
| Documentation | ✅ Complete |
| AWS Bedrock Integration | ⚠️ Needs configuration |
| AWS Infrastructure | ⚠️ Needs deployment |
| Shareable Link | ⚠️ Needs deployment |

---

## 💰 Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| AWS Bedrock | $20-30 |
| DynamoDB | $5-10 |
| S3 | $1-5 |
| Lambda | $10-20 |
| ECS | $20-30 |
| CloudWatch | $5-10 |
| **Total AWS** | **$60-100** |
| Render.com (free) | $0 |
| Render.com (paid) | $7 |
| **Grand Total** | **$60-110/month** |

---

## 🔑 Key Files

### Configuration
- `backend/.env` - Environment variables
- `backend/config.example.py` - Config example
- `render.yaml` - Render deployment

### Agents (Need Bedrock Integration)
- `backend/cloudforge/agents/bug_detective.py` - Bug detection
- `backend/cloudforge/agents/analysis.py` - Root cause analysis

### API
- `backend/cloudforge/api/main.py` - REST API
- `backend/cloudforge/web/app.py` - Web dashboard

### Infrastructure
- `infrastructure/lib/cloudforge-infrastructure-stack.ts` - Core
- `infrastructure/lib/cloudforge-compute-stack.ts` - Compute
- `infrastructure/lib/cloudforge-monitoring-stack.ts` - Monitoring

---

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| AccessDeniedException | Request Bedrock access in AWS console |
| ResourceNotFoundException | Create DynamoDB tables |
| Module not found | Run `pip install -r requirements.txt` |
| Deployment fails | Check environment variables |
| API returns 500 | Check AWS credentials |

---

## 📚 All Documentation

1. **[NEXT_STEPS.md](NEXT_STEPS.md)** - What to do now
2. **[AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)** - Complete setup
3. **[SIMPLE_DEPLOYMENT.md](SIMPLE_DEPLOYMENT.md)** - Quick deployment
4. **[AWS_COMPLETE_SETUP_GUIDE.md](AWS_COMPLETE_SETUP_GUIDE.md)** - Detailed AWS
5. **[GET_STARTED.md](GET_STARTED.md)** - Overview
6. **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Progress tracking
7. **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - API reference
8. **[SETUP_SUMMARY.md](SETUP_SUMMARY.md)** - Project status
9. **[README.md](README.md)** - Main readme

---

## ✅ Success Checklist

- [ ] AWS Bedrock access granted
- [ ] AWS credentials configured
- [ ] Bedrock integration implemented
- [ ] DynamoDB tables created
- [ ] S3 bucket created
- [ ] Local test successful
- [ ] Deployed to hosting
- [ ] Shareable link working
- [ ] End-to-end test passed

---

## 🎯 Recommended Path

1. Read [`NEXT_STEPS.md`](NEXT_STEPS.md) (5 min)
2. Follow [`AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md`](AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md) (1-2 hours)
3. Test with [`examples/api_examples/basic_workflow.py`](examples/api_examples/basic_workflow.py)
4. Share your link! 🎉

---

**Need help?** Check the troubleshooting section in any guide or review the logs in `backend/logs/`.
