# config.py
# Vantage.AI Platform Configuration
# POC to POC Transfer: hr-analytics-demo → vantage-ai-prod (Nov 22, 2025)
# Old POC project hr-analytics-demo DECOMMISSIONED on November 22, 2025

import os

# Hybrid Authentication Setup:
# - OAuth for Vertex AI, BigQuery (application default credentials)
# - Service Account Key for URL signing (requires private key)

# Primary: Use OAuth Application Default Credentials
if os.path.exists(r"C:\Users\sovik\AppData\Roaming\gcloud\application_default_credentials.json"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\sovik\AppData\Roaming\gcloud\application_default_credentials.json"

# Service Account Key Path (used explicitly for URL signing)
SA_KEY_PATH = r"C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys.json"

# GCP Project settings
PROJECT_ID = "vantage-ai-prod"
LOCATION = "us-central1"  # Vertex AI region

# BigQuery settings
BQ_DATASET = "hr_insights"
#BQ_TABLE = "journal_summaries"
VECROR_TABLE_ID = "journal_vectors"

# ScraperAPI settings (for LinkedIn Scouting)
SCRAPERAPI_KEY = "72154411d522dc842a6917ac81175505"

# ScrapingBee settings (alternative for LinkedIn - better success rate)
SCRAPINGBEE_API_KEY = "22ab254192274c25be74971b18632bec8aae3606118"

# Scrape.do settings (recommended for LinkedIn - best success rate)
SCRAPEDO_API_KEY = "a707f76f02f94692a0dd791ad758b23248c7d187267"

# RapidAPI settings (Real-Time LinkedIn Scraper API)
RAPIDAPI_KEY = "42f6f2cc8fmsh34de4f5ad2a8598p15ed41jsnf9059c925c83"

# LinkedIn scraping configuration
# HYBRID APPROACH (Best Practice):
# - Search: ScrapingBee/Scrape.do (HTML scraping - most reliable)
# - Profile Enrichment: RapidAPI (structured data - when available)
# The system automatically uses ScrapingBee for search and RapidAPI for profiles

# Mock mode for testing/demo (bypass real LinkedIn scraping)
USE_MOCK_LINKEDIN_DATA = True  # ✅ MOCK data enabled for demo (no scraping costs)

# GCS Bucket Configuration
GCS_BUCKET = "vantage-ai-prod-pdfs"
JOURNALS_BUCKET = "vantage-ai-prod-journals"
JOURNAL_VECTORS_BUCKET = "vantage-ai-prod-journal-vectors"

IMAGE_URI="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:v1"

# Cloud Build (recommended)
#gcloud builds submit --tag "${IMAGE_URI}" .

# Add these
SENTIMENT_BUCKET = f"{PROJECT_ID}-sentiment-uploads"
# OLD: SENTIMENT_BUCKET = "hr-analytics-demo-sentiment-uploads"
# NEW (computed from PROJECT_ID): "vantage-ai-prod-sentiment-uploads"
CREATE_BUCKET_IF_MISSING = False   # set True for dev if you want code to auto-create buckets
SENTIMENT_BUCKET_LOCATION = "US-CENTRAL1"  # or your preferred region

PUBSUB_TOPIC = f"projects/{PROJECT_ID}/topics/sentiment-jobs"

GEMINI_MODEL="gemini-2.5-flash-lite"  # or another available Gemini model

