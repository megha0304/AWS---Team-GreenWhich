# Simple Deployment - Get Your Shareable Link in 30 Minutes

This guide shows you how to deploy CloudForge with a **permanent shareable link** using free/cheap hosting options.

## 🎯 Goal

Get these permanent links:
- **API**: `https://your-app.onrender.com/api` (always active)
- **Dashboard**: `https://your-app.onrender.com` (always active)

## 🆓 Free Hosting Options

### Option 1: Render.com (Recommended - Easiest)

**Pros**: Free tier, automatic HTTPS, always-on, easy setup
**Cons**: Cold starts after inactivity (15-30 seconds)
**Cost**: Free (or $7/month for always-on)

### Option 2: Railway.app

**Pros**: $5 free credit, fast, good for demos
**Cons**: Requires credit card
**Cost**: ~$5-10/month after free credit

### Option 3: Fly.io

**Pros**: Free tier, fast, global CDN
**Cons**: Requires credit card
**Cost**: Free for small apps

---

## 🚀 Quick Deploy to Render.com (30 Minutes)

### Step 1: Prepare Your Code (5 minutes)

1. **Create `render.yaml`** in project root:

```yaml
services:
  # Web Service (API + Dashboard)
  - type: web
    name: cloudforge-bug-intelligence
    env: python
    region: oregon
    plan: free
    buildCommand: "cd backend && pip install -r requirements.txt"
    startCommand: "cd backend && python -m uvicorn cloudforge.api.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: AWS_REGION
        value: us-east-1
      - key: BEDROCK_MODEL_ID
        value: anthropic.claude-3-sonnet-20240229-v1:0
      - key: AWS_ACCESS_KEY_ID
        sync: false
      - key: AWS_SECRET_ACCESS_KEY
        sync: false
      - key: MOCK_MODE
        value: false
```

2. **Create `backend/requirements-render.txt`**:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
boto3==1.29.0
python-multipart==0.0.6
slowapi==0.1.9
```

3. **Update `backend/cloudforge/api/main.py`** to serve static files:

Add this at the top:
```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Mount static files
if os.path.exists("cloudforge/web/static"):
    app.mount("/static", StaticFiles(directory="cloudforge/web/static"), name="static")

# Serve dashboard
@app.get("/")
async def serve_dashboard():
    return FileResponse("cloudforge/web/templates/index.html")
```

### Step 2: Push to GitHub (5 minutes)

```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Prepare for Render deployment"

# Create GitHub repo and push
git remote add origin https://github.com/YOUR-USERNAME/cloudforge-bug-intelligence.git
git branch -M main
git push -u origin main
```

### Step 3: Deploy on Render (10 minutes)

1. **Sign up**: Go to https://render.com and sign up (free)

2. **Connect GitHub**: 
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select your `cloudforge-bug-intelligence` repository

3. **Configure Service**:
   - **Name**: `cloudforge-bug-intelligence`
   - **Region**: Oregon (US West)
   - **Branch**: `main`
   - **Root Directory**: Leave empty
   - **Environment**: Python 3
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && python -m uvicorn cloudforge.api.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

4. **Add Environment Variables**:
   Click "Environment" tab and add:
   ```
   AWS_REGION=us-east-1
   BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   MOCK_MODE=false
   ```

5. **Deploy**: Click "Create Web Service"

### Step 4: Get Your Shareable Link (2 minutes)

After deployment completes (~5 minutes):

1. **Your Link**: `https://cloudforge-bug-intelligence.onrender.com`
2. **API Docs**: `https://cloudforge-bug-intelligence.onrender.com/docs`
3. **Health Check**: `https://cloudforge-bug-intelligence.onrender.com/health`

**Share this link with anyone!** It's permanent and always accessible.

### Step 5: Test Your Deployment (5 minutes)

```bash
# Test health endpoint
curl https://cloudforge-bug-intelligence.onrender.com/health

# Test API
curl https://cloudforge-bug-intelligence.onrender.com/docs

# Open in browser
# Visit: https://cloudforge-bug-intelligence.onrender.com
```

---

## 🔧 Alternative: Deploy to Railway.app

### Step 1: Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

### Step 2: Deploy

```bash
cd cloudforge-bug-intelligence
railway init
railway up
```

### Step 3: Add Environment Variables

```bash
railway variables set AWS_REGION=us-east-1
railway variables set BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
railway variables set AWS_ACCESS_KEY_ID=your-key
railway variables set AWS_SECRET_ACCESS_KEY=your-secret
```

### Step 4: Get Your Link

```bash
railway domain
# Your link: https://cloudforge-bug-intelligence.up.railway.app
```

---

## 🌐 Alternative: Deploy to Fly.io

### Step 1: Install Fly CLI

```bash
# Windows
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"

# Mac/Linux
curl -L https://fly.io/install.sh | sh
```

### Step 2: Login and Deploy

```bash
fly auth login
cd cloudforge-bug-intelligence/backend
fly launch --name cloudforge-bug-intelligence
```

### Step 3: Configure

Edit `fly.toml`:
```toml
app = "cloudforge-bug-intelligence"

[env]
  AWS_REGION = "us-east-1"
  BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

[http_service]
  internal_port = 8000
  force_https = true
```

### Step 4: Deploy

```bash
fly deploy
fly open
# Your link: https://cloudforge-bug-intelligence.fly.dev
```

---

## 💡 Keep Your App Always Active

### For Render.com Free Tier

Free tier apps sleep after 15 minutes of inactivity. To keep it active:

**Option 1: Upgrade to Paid ($7/month)**
- Always-on
- No cold starts
- Better performance

**Option 2: Use UptimeRobot (Free)**
1. Sign up at https://uptimerobot.com
2. Add monitor:
   - Type: HTTP(s)
   - URL: `https://your-app.onrender.com/health`
   - Interval: 5 minutes
3. This pings your app every 5 minutes to keep it awake

**Option 3: GitHub Actions (Free)**

Create `.github/workflows/keep-alive.yml`:
```yaml
name: Keep Alive

on:
  schedule:
    - cron: '*/10 * * * *'  # Every 10 minutes

jobs:
  keep-alive:
    runs-on: ubuntu-latest
    steps:
      - name: Ping app
        run: curl https://your-app.onrender.com/health
```

---

## 🎨 Custom Domain (Optional)

### Add Your Own Domain

1. **Buy domain**: Namecheap, GoDaddy, etc. (~$10/year)

2. **In Render Dashboard**:
   - Go to your service
   - Click "Settings" → "Custom Domain"
   - Add: `api.yourdomain.com`

3. **Update DNS**:
   - Add CNAME record:
     - Name: `api`
     - Value: `cloudforge-bug-intelligence.onrender.com`

4. **Wait for SSL**: Render automatically provisions SSL (5-10 minutes)

5. **Your new link**: `https://api.yourdomain.com`

---

## 📊 Monitoring Your Deployment

### Render Dashboard

- **Logs**: Real-time logs in Render dashboard
- **Metrics**: CPU, memory, request count
- **Events**: Deployment history

### Check Status

```bash
# Health check
curl https://your-app.onrender.com/health

# API docs
curl https://your-app.onrender.com/docs

# Test workflow creation
curl -X POST https://your-app.onrender.com/workflows \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"repository_url": "https://github.com/example/repo"}'
```

---

## 🐛 Troubleshooting

### App Won't Start

**Check logs in Render dashboard**:
- Build logs: Check for dependency errors
- Deploy logs: Check for startup errors

**Common fixes**:
```bash
# Update requirements.txt
cd backend
pip freeze > requirements.txt

# Test locally first
python -m uvicorn cloudforge.api.main:app --host 0.0.0.0 --port 8000
```

### AWS Credentials Not Working

1. **Check environment variables** in Render dashboard
2. **Verify AWS credentials**:
   ```bash
   aws sts get-caller-identity
   ```
3. **Check IAM permissions** (need Bedrock access)

### App Sleeping (Free Tier)

- Use UptimeRobot to ping every 5 minutes
- Or upgrade to paid plan ($7/month)

---

## 💰 Cost Comparison

| Platform | Free Tier | Paid | Always-On | Custom Domain |
|----------|-----------|------|-----------|---------------|
| **Render** | ✅ Yes | $7/mo | Paid only | ✅ Free |
| **Railway** | $5 credit | ~$5-10/mo | ✅ Yes | ✅ Free |
| **Fly.io** | ✅ Yes | ~$5/mo | ✅ Yes | ✅ Free |
| **Heroku** | ❌ No | $7/mo | ✅ Yes | ✅ Free |

**Recommendation**: Start with Render free tier + UptimeRobot

---

## ✅ Success Checklist

- [ ] Code pushed to GitHub
- [ ] Deployed to Render/Railway/Fly
- [ ] Environment variables configured
- [ ] AWS credentials added
- [ ] Deployment successful
- [ ] Health endpoint working
- [ ] API docs accessible
- [ ] Dashboard loading
- [ ] Shareable link works
- [ ] (Optional) Custom domain configured
- [ ] (Optional) Keep-alive monitor set up

---

## 🎉 Your Shareable Links

After deployment, you'll have:

**Render.com**:
- API: `https://cloudforge-bug-intelligence.onrender.com`
- Docs: `https://cloudforge-bug-intelligence.onrender.com/docs`
- Dashboard: `https://cloudforge-bug-intelligence.onrender.com`

**Railway.app**:
- API: `https://cloudforge-bug-intelligence.up.railway.app`

**Fly.io**:
- API: `https://cloudforge-bug-intelligence.fly.dev`

**Share these with anyone!** They work from anywhere, anytime.

---

## 🚀 Next Steps

1. **Test your deployment**: Visit your link
2. **Share with team**: Send them the URL
3. **Monitor usage**: Check Render dashboard
4. **Optimize**: Upgrade if needed
5. **Add custom domain**: Make it professional

**Congratulations!** 🎉 Your CloudForge Bug Intelligence is now live and shareable!
