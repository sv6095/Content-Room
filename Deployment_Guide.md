# Content Room Deployment Guide

This guide covers deploying your Frontend to Vercel, Backend to Render, and ensuring all machine learning models (Toxicity/NSFW) are correctly configured.

## 1. Handling the ML Models (Before Pushing)

Since the `nsfw.caffemodel`, `resnet_moderation.pth`, and other model weights you fetched from Git are large files, standard Git might reject them. You **must** track them using Git LFS (Large File Storage) before pushing to GitHub.

Open your terminal in the root directory and run:
```bash
git lfs install
git lfs track "*.caffemodel"
git lfs track "*.pth"
git add .gitattributes
git add Backend/ml_models/
git add Backend/models/
git commit -m "Add ML models via LFS"
git push
```

### 🚨 Critical Fix for Detoxify (Toxicity Model)
In your `Backend/main.py` (around line 8), there are two lines that force HuggingFace offline:
```python
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
```
**You must comment out or delete `os.environ["HF_HUB_OFFLINE"] = "1"`**. 
If this remains `1`, `detoxify` will crash on Render because it won't be allowed to download the initial toxicity model weights into the cloud environment. Only set it to `1` when you are 100% sure the HuggingFace cache is already populated.

---

## 2. Backend Deployment (Render)

1. Go to your Render Dashboard and click **New > Web Service**.
2. Connect your GitHub repository.
3. Configure the service:
   - **Name**: `content-room-backend` (or similar)
   - **Root Directory**: `Backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Choose an instance type (Note: Due to the ML models, a free instance might struggle with memory. If it crashes on boot, you may need a starter tier).

### Backend `.env` (Copy & Paste to Render)
In the Render dashboard for your Web Service, go to **Environment** -> **Environment Variables**. You can click **Add from .env** and paste the following snippet directly:

```env
# ========================================
# AI PROVIDERS (Required)
# ========================================
GROQ_API_KEY=gsk_your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=groq

# ========================================
# DATABASE CONFIGURATION
# ========================================
# For Render, SQLite won't persist if the instance restarts. 
# It's recommended to add a Render PostgreSQL database later, but SQLite works to start.
DATABASE_URL=sqlite:///./contentos.db

# ========================================
# SECURITY & AUTHENTICATION
# ========================================
# Run python -c "import secrets; print(secrets.token_urlsafe(32))" to make a new one
SECRET_KEY=change-this-to-a-secure-random-string-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ========================================
# CORS & FRONTEND
# ========================================
# Update this to your final Vercel URL once deployed
FRONTEND_URL=https://your-frontend-url.vercel.app
ALLOWED_ORIGINS=https://your-frontend-url.vercel.app,http://localhost:5173

# ========================================
# SYSTEM CONFIG
# ========================================
LOG_LEVEL=INFO
DEBUG_MODE=false
AUTO_RELOAD=false
RATE_LIMIT_PER_MINUTE=60
MAX_IMAGE_SIZE_MB=5
HF_HUB_DISABLE_TELEMETRY=1
```

*(Be sure to replace `GROQ_API_KEY`, `GEMINI_API_KEY`, and `FRONTEND_URL` with your actual values).*

---

## 3. Frontend Deployment (Vercel)

1. Go to your Vercel Dashboard and click **Add New... > Project**.
2. Import your GitHub repository.
3. In the Configuration screen:
   - **Framework Preset**: `Vite` (Vercel should automatically detect this)
   - **Root Directory**: Click "Edit" and choose `Frontend`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Under **Environment Variables**, add the API URL of your newly deployed Render backend:
   - **Key**: `VITE_API_URL`
   - **Value**: `https://your-render-backend-url.onrender.com/api/v1` (Replace with your actual Render URL).
5. Click **Deploy**.

Once the Frontend is live, remember to copy its live URL and update the `FRONTEND_URL` and `ALLOWED_ORIGINS` in your Render Backend's Environment Variables so CORS works correctly!
