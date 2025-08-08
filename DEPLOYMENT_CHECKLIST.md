# Deployment Checklist for Render

## Pre-Deployment Checklist

### ✅ Code Preparation
- [ ] All files are committed to your Git repository
- [ ] `main.py` - Main application file (updated for deployment)
- [ ] `requirements.txt` - Python dependencies (updated)
- [ ] `render.yaml` - Render configuration file
- [ ] `runtime.txt` - Python version specification
- [ ] `Procfile` - Process definition
- [ ] `README.md` - Documentation
- [ ] `.gitignore` - Git ignore rules

### ✅ Environment Variables (Set in Render Dashboard)
- [ ] `API_BEARER_TOKEN` - Your API authentication token
- [ ] `GOOGLE_API_KEY` - Your Google AI API key
- [ ] `MONGO_HOST` - MongoDB Atlas host (e.g., `cluster0.xxxxx.mongodb.net`)
- [ ] `MONGO_USER` - MongoDB Atlas username
- [ ] `MONGO_PASS` - MongoDB Atlas password

### ✅ External Services Setup
- [ ] MongoDB Atlas cluster is running and accessible
- [ ] Google AI API key is valid and has sufficient quota
- [ ] Vector search index is created in MongoDB Atlas (named `vector_index`)

## Deployment Steps

### Step 1: Connect to Render
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" and select "Web Service"
3. Connect your GitHub/GitLab repository
4. Select the repository containing this project

### Step 2: Configure Service
1. **Name**: `bajaj-finserv-llm-api` (or your preferred name)
2. **Environment**: `Python 3`
3. **Region**: Choose closest to your users
4. **Branch**: `main` (or your default branch)
5. **Root Directory**: Leave empty (if code is in root)
6. **Build Command**: `pip install -r requirements.txt`
7. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 3: Set Environment Variables
In the Render dashboard, go to your service's "Environment" tab and add:
```
API_BEARER_TOKEN=your_bearer_token_here
GOOGLE_API_KEY=your_google_api_key_here
MONGO_HOST=your_mongo_host_here
MONGO_USER=your_mongo_username_here
MONGO_PASS=your_mongo_password_here
```

### Step 4: Deploy
1. Click "Create Web Service"
2. Monitor the build logs for any issues
3. Wait for deployment to complete
4. Note the deployment URL (e.g., `https://your-app-name.onrender.com`)

## Post-Deployment Verification

### ✅ Health Check
```bash
curl https://your-app-name.onrender.com/health
```
Expected response: `{"status": "healthy", "service": "LLM System with MongoDB Atlas"}`

### ✅ API Documentation
- Visit: `https://your-app-name.onrender.com/docs`
- Should show FastAPI interactive documentation

### ✅ Root Endpoint
```bash
curl https://your-app-name.onrender.com/
```
Expected response: API information and version

### ✅ Main API Endpoint Test
```bash
curl -X POST "https://your-app-name.onrender.com/api/v1/hackrx/run" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://example.com/document.pdf",
    "questions": ["What is the main topic?"]
  }'
```

## Troubleshooting

### Common Issues
1. **Build Failures**: Check build logs in Render dashboard
2. **Environment Variables**: Ensure all required variables are set
3. **MongoDB Connection**: Verify connection string and credentials
4. **API Keys**: Ensure Google AI API key is valid
5. **Port Issues**: Ensure `$PORT` environment variable is used

### Logs
- View logs in Render dashboard under your service's "Logs" tab
- Application logs are automatically captured

## Support
- Render Documentation: https://render.com/docs
- MongoDB Atlas Documentation: https://docs.atlas.mongodb.com/
- Google AI Documentation: https://ai.google.dev/docs
