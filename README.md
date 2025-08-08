# LLM System with MongoDB Atlas

An AI-powered document analysis system that uses Google's Gemini model and MongoDB Atlas for vector search capabilities.

## Features

- Document processing (PDF and DOCX)
- Vector search using MongoDB Atlas
- AI-powered question answering
- Secure API with Bearer token authentication
- Health check endpoints

## Prerequisites

- Python 3.11+
- MongoDB Atlas account
- Google AI API key
- Render account (for deployment)

## Environment Variables

The following environment variables need to be set in Render:

- `API_BEARER_TOKEN`: Your API authentication token
- `GOOGLE_API_KEY`: Your Google AI API key
- `MONGO_HOST`: MongoDB Atlas host (e.g., `cluster0.xxxxx.mongodb.net`)
- `MONGO_USER`: MongoDB Atlas username
- `MONGO_PASS`: MongoDB Atlas password

## Deployment on Render

### Step 1: Prepare Your Repository

1. Ensure your repository contains the following files:
   - `main.py` - Main application file
   - `requirements.txt` - Python dependencies
   - `render.yaml` - Render configuration
   - `runtime.txt` - Python version specification
   - `Procfile` - Process definition

### Step 2: Connect to Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" and select "Web Service"
3. Connect your GitHub/GitLab repository
4. Select the repository containing this project

### Step 3: Configure the Service

1. **Name**: `bajaj-finserv-llm-api` (or your preferred name)
2. **Environment**: `Python 3`
3. **Region**: Choose the closest to your users
4. **Branch**: `main` (or your default branch)
5. **Root Directory**: Leave empty (if code is in root)
6. **Build Command**: `pip install -r requirements.txt`
7. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 4: Set Environment Variables

In the Render dashboard, go to your service's "Environment" tab and add:

```
API_BEARER_TOKEN=your_bearer_token_here
GOOGLE_API_KEY=your_google_api_key_here
MONGO_HOST=your_mongo_host_here
MONGO_USER=your_mongo_username_here
MONGO_PASS=your_mongo_password_here
```

### Step 5: Deploy

1. Click "Create Web Service"
2. Render will automatically build and deploy your application
3. Monitor the build logs for any issues
4. Once deployed, you'll get a URL like: `https://your-app-name.onrender.com`

## API Endpoints

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation
- `POST /api/v1/hackrx/run` - Main endpoint for document analysis

## Usage

### Health Check
```bash
curl https://your-app-name.onrender.com/health
```

### Document Analysis
```bash
curl -X POST "https://your-app-name.onrender.com/api/v1/hackrx/run" \
  -H "Authorization: Bearer YOUR_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://example.com/document.pdf",
    "questions": ["What is the main topic?", "What are the key points?"]
  }'
```

## Troubleshooting

### Common Issues

1. **Build Failures**: Check the build logs in Render dashboard
2. **Environment Variables**: Ensure all required variables are set
3. **MongoDB Connection**: Verify your MongoDB Atlas connection string
4. **API Keys**: Ensure Google AI API key is valid and has sufficient quota

### Logs

- View logs in the Render dashboard under your service's "Logs" tab
- Application logs are automatically captured and displayed

## Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your environment variables
4. Run: `uvicorn main:app --reload`

## Support

For issues related to:
- Render deployment: Check Render documentation
- MongoDB Atlas: Check MongoDB documentation
- Google AI: Check Google AI documentation
