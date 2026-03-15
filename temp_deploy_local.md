# Local Deployment Guide — CloudForge Bug Intelligence

> Branch: `bedrock-integration` | Python 3.10+

---

## 1. Prerequisites

- Python 3.10+
- AWS CLI configured (`aws configure`) with Bedrock access
- Git
- (Optional) Docker — for LocalStack local AWS emulation

---

## 2. Clone & Setup

```bash
git clone https://github.com/megha0304/AWS---Team-GreenWhich.git
cd AWS---Team-GreenWhich
git checkout bedrock-integration
```

### Create virtual environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
pip install pydantic-settings
```

---

## 3. Environment Configuration

```bash
cp .env.example .env
```

Edit `backend/.env` — set at minimum:

```env
AWS_REGION=us-east-1
AWS_PROFILE=default
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_REGION=us-east-1
ENVIRONMENT=development
LOG_LEVEL=INFO
API_PORT=8000
```

If you want API key auth, also set:
```env
API_KEY=your-secret-key-here
```
(If `API_KEY` is unset, all requests are allowed — dev mode.)

---

## 4. Verify Setup — Run Tests

```bash
# From backend/ with venv activated
pytest tests/ -v
```

Expected: **345 passed, 0 failures**

---

## 5. Start the Services

### Option A: FastAPI REST API (port 8000)

```bash
cd backend
uvicorn cloudforge.api.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints:
- Health: `http://localhost:8000/health`
- Swagger docs: `http://localhost:8000/docs`
- Create workflow: `POST /workflows`
- List workflows: `GET /workflows`
- Get workflow: `GET /workflows/{id}`
- Get bugs: `GET /workflows/{id}/bugs`
- Get fixes: `GET /workflows/{id}/fixes`
- Export: `GET /workflows/{id}/export`

### Option B: Flask Web Dashboard (port 5000)

```bash
cd backend
python -m cloudforge.main
```

Dashboard: `http://localhost:5000`

### Option C: Both (two terminals)

Terminal 1 — API:
```bash
cd backend && source venv/bin/activate
uvicorn cloudforge.api.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 — Dashboard:
```bash
cd backend && source venv/bin/activate
python -m cloudforge.main
```

---

## 6. Quick API Test

```bash
# Health check
curl http://localhost:8000/health

# Create a workflow (no API_KEY set = dev mode, no header needed)
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"repository_url": "https://github.com/example/repo"}'

# With API key (if API_KEY is set in .env)
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{"repository_url": "https://github.com/example/repo"}'
```

---

## 7. (Optional) LocalStack for Local AWS Services

If you want DynamoDB/S3/Lambda locally without real AWS:

```bash
# From project root
docker-compose up -d localstack

# Wait ~5s, then create tables/buckets
make aws-setup
```

Then set in `backend/.env`:
```env
DYNAMODB_ENDPOINT_URL=http://localhost:4566
S3_ENDPOINT_URL=http://localhost:4566
```

---

## 8. AWS Credentials for Bedrock (Real Calls)

The agents call AWS Bedrock for real AI analysis. Ensure:

1. Your AWS account has Bedrock enabled in the target region
2. Claude model access is granted in the Bedrock console
3. Your IAM user/role has `bedrock:InvokeModel` permission
4. AWS CLI is configured: `aws configure` (or set `AWS_PROFILE` in `.env`)

Without valid Bedrock credentials, agents will fall back to local/fallback logic.

---

## Project Ports Summary

| Service | Port | Command |
|---------|------|---------|
| FastAPI REST API | 8000 | `uvicorn cloudforge.api.main:app --reload` |
| Flask Dashboard | 5000 | `python -m cloudforge.main` |
| LocalStack | 4566 | `docker-compose up -d localstack` |
