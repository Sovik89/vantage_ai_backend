from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import config

# Import routers
# Note: Assuming these files are in a 'routers' subdirectory or root
# Adjust imports based on your actual project structure

from routers.query import router as query_router
from routers.ingest import router as ingest_router
from routers.download import router as download_router
from routers.sessions import router as sessions_router
from routers.ats_upload import router as ats_router  # NEW: ATS Router
from routers.sentiment_upload import router as sentiment_router  # NEW: Sentiment Router
from routers.dashboard import router as get_dashboard_stats  # NEW: Dashboard Router
from routers.linkedin_scout import router as linkedin_router  # NEW: LinkedIn Scout Router

# Create the FastAPI app instance
app = FastAPI(
    title="Vantage.AI Multi-Agent Platform",
    version="2.0.2",
    description="The intelligent backend for the Vantage.AI People Analytics Platform with unified agent endpoints.",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# JOURNAL / INSIGHTS (Existing)
# ==============================================================================
app.include_router(query_router, prefix="/insights", tags=["Journal Insights"])
app.include_router(ingest_router, prefix="/files", tags=["Journal Ingestion"])
app.include_router(download_router, prefix="/download", tags=["File Downloads"])
app.include_router(sessions_router, prefix="/sessions", tags=["User Sessions"])

# ==============================================================================
# ATS CHECKER (NEW - Unified Pattern)
# ==============================================================================
app.include_router(ats_router, prefix="/agents/ats", tags=["ATS Checker"])

# ==============================================================================
# SENTIMENT ANALYZER
# ==============================================================================
app.include_router(sentiment_router, prefix="/agents/sentiment", tags=["Sentiment Analyzer"])

# ==============================================================================
# LINKEDIN SCOUT (NEW)
# ==============================================================================
app.include_router(linkedin_router, prefix="/agents/linkedin", tags=["LinkedIn Scout"])

# ==============================================================================
# DASHBOARD ROUTER
# ==============================================================================
app.include_router(get_dashboard_stats, prefix="/agents/dashboard", tags=["Dashboard"])


@app.get("/", tags=["Health Check"])
async def read_root():
    """
    Health check endpoint to confirm the API is running correctly.
    """
    return {
        "status": "Vantage.AI Multi-Agent Platform is running!",
        "version": "2.0.0",
        "agents": {
            "journal": {
                "status": "active",
                "endpoints": ["/insights", "/files", "/sessions"]
            },
            "ats": {
                "status": "active",
                "endpoints": ["/agents/ats/submit", "/agents/ats/status/{id}", "/agents/ats/results/{id}", "/agents/ats/jobs"]
            },
            "sentiment": {
                "status": "active",
                "endpoints": ["/agents/sentiment/submit", "/agents/sentiment/jobs"]
            },
            "linkedin": {
                "status": "active",
                "endpoints": ["/agents/linkedin/scout", "/agents/linkedin/jobs/{job_id}", "/agents/linkedin/download/{job_id}", "/agents/linkedin/jobs"]
            }
        }
    }


@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Detailed health check for monitoring
    """
    return {
        "status": "healthy",
        "project_id": config.PROJECT_ID,
        "dataset": config.BQ_DATASET,
        "location": config.LOCATION
    }


# Instructions to run the server (from your 'vantage-api' directory):
# 1. Activate your virtual environment: .\backend_env\Scripts\activate (Windows)
# 2. Start the server: uvicorn main:app --reload --host 0.0.0.0 --port 8000
# 3. API docs: http://localhost:8000/docs