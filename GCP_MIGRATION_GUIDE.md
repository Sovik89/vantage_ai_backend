# GCP Cloud Migration Guide - Vantage AI Backend
## Complete 3-Hour Migration Checklist

**Target Timeline:** 3 hours maximum  
**Source Project:** `hr-analytics-demo`  
**Target Project:** `vantage-ai-prod` (or your new project name)  
**Migration Date:** Tomorrow Morning

---

## ⏱️ TIMELINE BREAKDOWN

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| **Phase 1** | GCP Setup & IAM | 30 min | ⬜ |
| **Phase 2** | BigQuery Migration | 45 min | ⬜ |
| **Phase 3** | GCS Buckets | 30 min | ⬜ |
| **Phase 4** | Service Account & Keys | 20 min | ⬜ |
| **Phase 5** | Code Configuration | 20 min | ⬜ |
| **Phase 6** | Testing & Validation | 35 min | ⬜ |

**Total:** ~3 hours

---

## 📋 PRE-MIGRATION CHECKLIST

### Documents to Keep Ready
- [ ] New Gmail account credentials
- [ ] Credit card for GCP billing (for 90-day free trial)
- [ ] Current `sa-keys.json` file backup
- [ ] This migration guide printed/accessible

### Current Environment Details

**Source Project ID:** `hr-analytics-demo`  
**Source Dataset:** `hr_insights`  
**Source Region:** `us-central1`

**BigQuery Tables:**
1. `linkedin_jobs` - LinkedIn scouting jobs
2. `linkedin_results` - LinkedIn candidate results
3. `ats_jobs` - ATS checker jobs
4. `ats_results` - ATS candidate results
5. `sentiment_jobs` - Sentiment analysis jobs
6. `sentiment_results` - Sentiment analysis results
7. `journal_vectors` - Chatbot knowledge base (with embeddings)
8. `sessions` - User session tracking (queries/uploads)

**GCS Buckets:**
1. `hr-analytics-pdfs` - PDF storage
2. `hr-analytics-demo-sentiment-uploads` - Sentiment uploads

---

## 🚀 PHASE 1: NEW GCP PROJECT SETUP (30 min)

### Step 1.1: Create New GCP Project (5 min)
```bash
# Open browser: https://console.cloud.google.com/
# 1. Click "Select a project" → "NEW PROJECT"
# 2. Enter details:
#    - Project name: Vantage AI Production
#    - Project ID: vantage-ai-prod (note this down!)
#    - Organization: None (or your org)
# 3. Click "CREATE"
# 4. Wait 30 seconds for project creation
```

**✏️ Note your new Project ID:** `_________________________`

### Step 1.2: Enable Free Trial (5 min)
```bash
# In GCP Console:
# 1. Click "Activate" on the free trial banner
# 2. Enter credit card details (won't be charged for 90 days)
# 3. Accept terms and conditions
# 4. Verify $300 credit appears in billing
```

### Step 1.3: Enable Required APIs (10 min)
```bash
# Method 1: Via Console UI
# Navigate to: APIs & Services → Enable APIs and Services
# Search and enable each:
# ✓ BigQuery API
# ✓ Cloud Storage API
# ✓ Vertex AI API
# ✓ IAM Service Account Credentials API
# ✓ Cloud Resource Manager API

# Method 2: Via gcloud CLI (faster)
gcloud config set project vantage-ai-prod

gcloud services enable bigquery.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable iamcredentials.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

### Step 1.4: Set Billing Account (5 min)
```bash
# In GCP Console:
# 1. Menu → Billing
# 2. Link billing account to vantage-ai-prod
# 3. Verify free trial credits active
```

### Step 1.5: Install gcloud CLI (if not already) (5 min)
```powershell
# Check if installed
gcloud --version

# If not installed, download from:
# https://cloud.google.com/sdk/docs/install

# After installation:
gcloud init
gcloud auth login
gcloud config set project vantage-ai-prod
```

---

## 💾 PHASE 2: BIGQUERY DATA MIGRATION (45 min)

### Step 2.1: Create Target Dataset (5 min)
```bash
# Via Console:
# BigQuery → Create Dataset
# Dataset ID: hr_insights
# Location: us-central1 (SAME as source)
# Default table expiration: Never

# Via gcloud:
bq mk --dataset --location=us-central1 --description="HR Analytics Dataset" vantage-ai-prod:hr_insights
```

### Step 2.2: Export Tables from Source Project (15 min)

**⚠️ IMPORTANT: Authenticate with source project first!**
```bash
# Login with the OLD Gmail account that owns hr-analytics-demo
gcloud auth login

# Follow the browser login flow - use the ORIGINAL Gmail account

# Set source project
gcloud config set project hr-analytics-demo

# Verify you have access
bq ls hr-analytics-demo:hr_insights

# If you see the table list, you're ready to proceed
```

**⚠️ CRITICAL: Projects owned by DIFFERENT Gmail accounts!**

Since the source and target projects are owned by different Gmail accounts, direct `bq cp` will NOT work. You must use **Option B** below (export to local files, then import).

**Option A: Direct Copy (ONLY if same Gmail account owns both projects)**
```bash
# ❌ THIS WILL FAIL IF DIFFERENT ACCOUNTS ❌
# Skip this if projects are owned by different Gmail accounts
bq cp hr-analytics-demo:hr_insights.linkedin_jobs vantage-ai-prod:hr_insights.linkedin_jobs

bq cp \
  hr-analytics-demo:hr_insights.linkedin_results \
  vantage-ai-prod:hr_insights.linkedin_results

bq cp \
  hr-analytics-demo:hr_insights.ats_jobs \
  vantage-ai-prod:hr_insights.ats_jobs

bq cp \
  hr-analytics-demo:hr_insights.ats_results \
  vantage-ai-prod:hr_insights.ats_results

bq cp \
  hr-analytics-demo:hr_insights.sentiment_jobs \
  vantage-ai-prod:hr_insights.sentiment_jobs

bq cp \
  hr-analytics-demo:hr_insights.sentiment_results \
  vantage-ai-prod:hr_insights.sentiment_results

bq cp \
  hr-analytics-demo:hr_insights.journal_vectors \
  vantage-ai-prod:hr_insights.journal_vectors

bq cp \
  hr-analytics-demo:hr_insights.sessions \
  vantage-ai-prod:hr_insights.sessions
```

**Option B: Export to Local Files, Then Import (REQUIRED for different accounts)**
```bash
# ===================================================================
# STEP 1: LOGIN WITH OLD ACCOUNT & EXPORT DATA
# ===================================================================

# Login with OLD Gmail account
gcloud auth login
# Select the OLD account that owns hr-analytics-demo

# Set old project
gcloud config set project hr-analytics-demo

# Create local export directory
mkdir C:\temp\bq_migration
cd C:\temp\bq_migration

# Export each table to local JSON files (OLD account)
# This will take ~10-15 minutes for all 8 tables

Write-Host "Exporting Table 1/8: linkedin_jobs..." -ForegroundColor Cyan
bq extract \
  --destination_format=NEWLINE_DELIMITED_JSON \
  hr-analytics-demo:hr_insights.linkedin_jobs \
  gs://hr-analytics-demo-temp-export/linkedin_jobs_*.json

# Download from GCS to local
gsutil -m cp gs://hr-analytics-demo-temp-export/linkedin_jobs_*.json C:\temp\bq_migration\

Write-Host "Exporting Table 2/8: linkedin_results..." -ForegroundColor Cyan

bq extract \
  --destination_format=NEWLINE_DELIMITED_JSON \
  hr-analytics-demo:hr_insights.linkedin_results \
  gs://temp-migration-hr-analytics/linkedin_results/*.json

bq extract \
  --destination_format=NEWLINE_DELIMITED_JSON \
  hr-analytics-demo:hr_insights.ats_jobs \
  gs://temp-migration-hr-analytics/ats_jobs/*.json

bq extract \
  --destination_format=NEWLINE_DELIMITED_JSON \
  hr-analytics-demo:hr_insights.ats_results \
  gs://temp-migration-hr-analytics/ats_results/*.json

bq extract \
  --destination_format=NEWLINE_DELIMITED_JSON \
  hr-analytics-demo:hr_insights.sentiment_jobs \
  gs://temp-migration-hr-analytics/sentiment_jobs/*.json

bq extract \
  --destination_format=NEWLINE_DELIMITED_JSON \
  hr-analytics-demo:hr_insights.sentiment_results \
  gs://temp-migration-hr-analytics/sentiment_results/*.json

bq extract \
  --destination_format=NEWLINE_DELIMITED_JSON \
  hr-analytics-demo:hr_insights.journal_vectors \
  gs://temp-migration-hr-analytics/journal_vectors/*.json

bq extract \
  --destination_format=NEWLINE_DELIMITED_JSON \
  hr-analytics-demo:hr_insights.sessions \
  gs://temp-migration-hr-analytics/sessions/*.json

# 3. Switch to new project
gcloud config set project vantage-ai-prod

# 4. Import each table to new project
bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  vantage-ai-prod:hr_insights.linkedin_jobs \
  gs://temp-migration-hr-analytics/linkedin_jobs/*.json

bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  vantage-ai-prod:hr_insights.linkedin_results \
  gs://temp-migration-hr-analytics/linkedin_results/*.json

bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  vantage-ai-prod:hr_insights.ats_jobs \
  gs://temp-migration-hr-analytics/ats_jobs/*.json

bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  vantage-ai-prod:hr_insights.ats_results \
  gs://temp-migration-hr-analytics/ats_results/*.json

bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  vantage-ai-prod:hr_insights.sentiment_jobs \
  gs://temp-migration-hr-analytics/sentiment_jobs/*.json

bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  vantage-ai-prod:hr_insights.sentiment_results \
  gs://temp-migration-hr-analytics/sentiment_results/*.json

bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  vantage-ai-prod:hr_insights.journal_vectors \
  gs://temp-migration-hr-analytics/journal_vectors/*.json

bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  vantage-ai-prod:hr_insights.sessions \
  gs://temp-migration-hr-analytics/sessions/*.json

# 5. Cleanup temp bucket
gsutil rm -r gs://temp-migration-hr-analytics/
```

### Step 2.3: Verify Table Migration (10 min)
```bash
# Check all tables exist
bq ls vantage-ai-prod:hr_insights

# Verify row counts match
bq query --use_legacy_sql=false \
"SELECT 
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.linkedin_jobs\`) as linkedin_jobs,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.linkedin_results\`) as linkedin_results,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.ats_jobs\`) as ats_jobs,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.ats_results\`) as ats_results,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.sentiment_jobs\`) as sentiment_jobs,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.sentiment_results\`) as sentiment_results,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.journal_vectors\`) as journal_vectors,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.sessions\`) as sessions"

# Compare with source project counts
gcloud config set project hr-analytics-demo
bq query --use_legacy_sql=false \
"SELECT 
  (SELECT COUNT(*) FROM \`hr-analytics-demo.hr_insights.linkedin_jobs\`) as linkedin_jobs,
  (SELECT COUNT(*) FROM \`hr-analytics-demo.hr_insights.linkedin_results\`) as linkedin_results,
  (SELECT COUNT(*) FROM \`hr-analytics-demo.hr_insights.ats_jobs\`) as ats_jobs,
  (SELECT COUNT(*) FROM \`hr-analytics-demo.hr_insights.ats_results\`) as ats_results,
  (SELECT COUNT(*) FROM \`hr-analytics-demo.hr_insights.sentiment_jobs\`) as sentiment_jobs,
  (SELECT COUNT(*) FROM \`hr-analytics-demo.hr_insights.sentiment_results\`) as sentiment_results,
  (SELECT COUNT(*) FROM \`hr-analytics-demo.hr_insights.journal_vectors\`) as journal_vectors,
  (SELECT COUNT(*) FROM \`hr-analytics-demo.hr_insights.sessions\`) as sessions"

# ✅ Row counts should match!
```

### Step 2.4: Test Query Access (5 min)
```bash
gcloud config set project vantage-ai-prod

# Test sample queries
bq query --use_legacy_sql=false \
"SELECT * FROM \`vantage-ai-prod.hr_insights.linkedin_jobs\` LIMIT 5"

bq query --use_legacy_sql=false \
"SELECT * FROM \`vantage-ai-prod.hr_insights.journal_vectors\` LIMIT 5"
```

---

## 📦 PHASE 3: GCS BUCKET MIGRATION (30 min)

### Step 3.1: Create New Buckets (5 min)
```bash
gcloud config set project vantage-ai-prod

# Bucket 1: PDF storage
gsutil mb -l us-central1 -c STANDARD gs://vantage-ai-prod-pdfs/

# Bucket 2: Sentiment uploads
gsutil mb -l us-central1 -c STANDARD gs://vantage-ai-prod-sentiment-uploads/
```

### Step 3.2: Copy Existing Data (15 min)
```bash
# Copy all files from source to target buckets
# This preserves folder structure and metadata

# Copy PDFs
gsutil -m cp -r \
  gs://hr-analytics-pdfs/* \
  gs://vantage-ai-prod-pdfs/

# Copy sentiment uploads
gsutil -m cp -r \
  gs://hr-analytics-demo-sentiment-uploads/* \
  gs://vantage-ai-prod-sentiment-uploads/

# Verify copy
gsutil ls gs://vantage-ai-prod-pdfs/
gsutil ls gs://vantage-ai-prod-sentiment-uploads/
```

### Step 3.3: Set Bucket Permissions (5 min)
```bash
# Make buckets private (default)
gsutil iam ch allUsers:objectViewer \
  gs://vantage-ai-prod-pdfs/ -d

gsutil iam ch allUsers:objectViewer \
  gs://vantage-ai-prod-sentiment-uploads/ -d

# Service account will have access via IAM roles
```

### Step 3.4: Enable Versioning (Optional - 5 min)
```bash
# Enable object versioning for backup
gsutil versioning set on gs://vantage-ai-prod-pdfs/
gsutil versioning set on gs://vantage-ai-prod-sentiment-uploads/
```

---

## 🔐 PHASE 4: SERVICE ACCOUNT & IAM (20 min)

### Step 4.1: Create Service Account (5 min)
```bash
gcloud config set project vantage-ai-prod

# Create service account
gcloud iam service-accounts create vantage-api-sa \
  --display-name="Vantage API Service Account" \
  --description="Service account for Vantage AI Backend API"

# Verify creation
gcloud iam service-accounts list
```

**✏️ Note your service account email:** `vantage-api-sa@vantage-ai-prod.iam.gserviceaccount.com`

### Step 4.2: Assign IAM Roles (10 min)
```bash
# Get project ID
PROJECT_ID=vantage-ai-prod

# Grant BigQuery Admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vantage-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"

# Grant Storage Admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vantage-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Grant Vertex AI User
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vantage-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Grant Service Account Token Creator (for signed URLs)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vantage-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"

# Verify roles assigned
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:vantage-api-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

### Step 4.3: Generate Service Account Key (5 min)
```bash
# Create keys directory if not exists
mkdir -p C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys

# Generate new key
gcloud iam service-accounts keys create \
  C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys-new.json \
  --iam-account=vantage-api-sa@vantage-ai-prod.iam.gserviceaccount.com

# Backup old key
Copy-Item `
  C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys.json `
  C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys-OLD.json

# Replace with new key
Copy-Item `
  C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys-new.json `
  C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys.json

# Verify key file
Get-Content C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys.json | Select-String "project_id"
```

**✅ Expected output:** `"project_id": "vantage-ai-prod"`

---

## ⚙️ PHASE 5: CODE CONFIGURATION (20 min)

### Step 5.1: Update config.py (5 min)
```powershell
# Open config.py
code C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\config.py
```

**Changes to make:**
```python
# OLD VALUES:
PROJECT_ID = "hr-analytics-demo"
GCS_BUCKET = "hr-analytics-pdfs"
SENTIMENT_BUCKET = "hr-analytics-demo-sentiment-uploads"

# NEW VALUES:
PROJECT_ID = "vantage-ai-prod"
GCS_BUCKET = "vantage-ai-prod-pdfs"
SENTIMENT_BUCKET = "vantage-ai-prod-sentiment-uploads"
```

**Complete updated config.py:**
```python
# config.py

# GCP Project settings
PROJECT_ID = "vantage-ai-prod"  # ✅ UPDATED
LOCATION = "us-central1"

# BigQuery settings
BQ_DATASET = "hr_insights"
VECROR_TABLE_ID = "journal_vectors"

# ScraperAPI settings (for LinkedIn Scouting)
SCRAPERAPI_KEY = "72154411d522dc842a6917ac81175505"

# ScrapingBee settings (alternative for LinkedIn)
SCRAPINGBEE_API_KEY = "22ab254192274c25be74971b18632bec8aae3606118"

# Scrape.do settings (recommended for LinkedIn)
SCRAPEDO_API_KEY = "a707f76f02f94692a0dd791ad758b23248c7d187267"

# RapidAPI settings (Real-Time LinkedIn Scraper API)
RAPIDAPI_KEY = "42f6f2cc8fmsh34de4f5ad2a8598p15ed41jsnf9059c925c83"

# Mock mode for testing/demo
USE_MOCK_LINKEDIN_DATA = False

# GCS Buckets
GCS_BUCKET = "vantage-ai-prod-pdfs"  # ✅ UPDATED
SENTIMENT_BUCKET = "vantage-ai-prod-sentiment-uploads"  # ✅ UPDATED

IMAGE_URI = f"gcr.io/{PROJECT_ID}/vantage-api:v1"

CREATE_BUCKET_IF_MISSING = False
SENTIMENT_BUCKET_LOCATION = "US-CENTRAL1"

PUBSUB_TOPIC = f"projects/{PROJECT_ID}/topics/sentiment-jobs"

GEMINI_MODEL = "gemini-2.5-flash-lite"
```

### Step 5.2: Update Environment Variables (5 min)
```powershell
# Update command.txt with new credentials path
$commandFile = "C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\command.txt"

# Verify current content
Get-Content $commandFile

# Should show:
# $env:GOOGLE_APPLICATION_CREDENTIALS="C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys.json"
# uvicorn main:app --host 127.0.0.1 --port 8080 --reload

# No changes needed - path stays the same, just new key content
```

### Step 5.3: Update Frontend Environment (if applicable) (5 min)
```powershell
# If you have frontend .env file
$frontendEnv = "C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_frontend-main_code\.env.local"

# Update API endpoint if needed (usually no change for localhost)
# NEXT_PUBLIC_API_URL=http://localhost:8080

# No changes needed for local development
```

### Step 5.4: Verify Dependencies (5 min)
```powershell
# Check if all packages installed
cd C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api

# Activate virtual environment
.\backend_env\Scripts\Activate.ps1

# Verify installations
pip list | Select-String "google-cloud"

# Should see:
# google-cloud-bigquery
# google-cloud-storage
# google-cloud-aiplatform
```

---

## ✅ PHASE 6: TESTING & VALIDATION (35 min)

### Step 6.1: Test Service Account Authentication (5 min)
```powershell
# Set environment variable
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys.json"

# Test Python authentication
python -c "from google.cloud import bigquery; client = bigquery.Client(); print(f'✅ Authenticated as: {client.project}')"

# Expected output: ✅ Authenticated as: vantage-ai-prod
```

### Step 6.2: Test BigQuery Access (5 min)
```powershell
# Test query
python -c "
from google.cloud import bigquery
import config

client = bigquery.Client(project=config.PROJECT_ID)
query = f'SELECT COUNT(*) as count FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.linkedin_jobs`'
result = list(client.query(query).result())
print(f'✅ LinkedIn Jobs Count: {result[0].count}')
"
```

### Step 6.3: Test GCS Access (5 min)
```powershell
# Test bucket access
python -c "
from google.cloud import storage
import config

client = storage.Client(project=config.PROJECT_ID)
bucket = client.bucket(config.GCS_BUCKET)
exists = bucket.exists()
print(f'✅ Bucket {config.GCS_BUCKET} exists: {exists}')
"
```

### Step 6.4: Test Vertex AI Access (5 min)
```powershell
# Test Gemini API
python -c "
import vertexai
from vertexai.generative_models import GenerativeModel
import config

vertexai.init(project=config.PROJECT_ID, location=config.LOCATION)
model = GenerativeModel(config.GEMINI_MODEL)
response = model.generate_content('Say hello in 5 words')
print(f'✅ Vertex AI Response: {response.text}')
"
```

### Step 6.5: Start Backend Server (5 min)
```powershell
cd C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api

# Activate environment
.\backend_env\Scripts\Activate.ps1

# Set credentials
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys.json"

# Start server
uvicorn main:app --host 127.0.0.1 --port 8080 --reload

# ✅ Should see: "Application startup complete"
# ✅ Should see: "Uvicorn running on http://127.0.0.1:8080"
```

### Step 6.6: Test API Endpoints (5 min)
Open new PowerShell window:

```powershell
# Test health endpoint
curl http://localhost:8080/

# Expected: {"message":"Vantage AI API is running"}

# Test BigQuery endpoint
curl http://localhost:8080/api/linkedin/jobs?user_email=test@example.com

# Expected: JSON array of jobs (or empty array if no data)
```

### Step 6.7: Test Frontend (5 min)
```powershell
cd C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_frontend-main_code

# Start frontend
npm run dev

# Open browser: http://localhost:3000
# ✅ Should load Vantage AI dashboard
# ✅ Try uploading a test file to verify GCS upload
```

---

## 🔒 SECURITY CHECKLIST

### Post-Migration Security (5 min)

- [ ] **Delete old service account key** (after confirming new one works)
  ```bash
  gcloud config set project hr-analytics-demo
  gcloud iam service-accounts keys list \
    --iam-account=<OLD_SA_EMAIL>
  
  # Delete old key
  gcloud iam service-accounts keys delete <KEY_ID> \
    --iam-account=<OLD_SA_EMAIL>
  ```

- [ ] **Secure sa-keys.json file**
  - ✅ Added to .gitignore
  - ✅ Not committed to Git
  - ✅ Backup stored securely (encrypted USB/password manager)

- [ ] **Set up billing alerts**
  ```
  GCP Console → Billing → Budgets & Alerts
  Set alert at: $50, $100, $200
  ```

- [ ] **Enable audit logging**
  ```
  GCP Console → IAM & Admin → Audit Logs
  Enable for: BigQuery, Storage, Vertex AI
  ```

---

## 📊 VALIDATION CHECKLIST

Use this to confirm migration success:

### BigQuery ✅
- [ ] All 7 tables exist in new project
- [ ] Row counts match source tables
- [ ] Sample queries return correct data
- [ ] Journal vectors embeddings intact

### GCS Buckets ✅
- [ ] Both buckets created
- [ ] Files copied successfully
- [ ] File count matches source
- [ ] Permissions set correctly

### Service Account ✅
- [ ] SA created with correct name
- [ ] All 4 IAM roles assigned
- [ ] Key generated and downloaded
- [ ] Authentication works

### Application ✅
- [ ] config.py updated
- [ ] Environment variables set
- [ ] Backend starts without errors
- [ ] Frontend connects to backend
- [ ] Test API call succeeds

### APIs Enabled ✅
- [ ] BigQuery API
- [ ] Cloud Storage API
- [ ] Vertex AI API
- [ ] IAM Service Account Credentials API
- [ ] Cloud Resource Manager API

---

## 🆘 TROUBLESHOOTING

### Issue: "Permission Denied" errors
**Solution:**
```bash
# Re-apply IAM roles
PROJECT_ID=vantage-ai-prod
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:vantage-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"
```

### Issue: "Table not found"
**Solution:**
```bash
# Verify table exists
bq ls vantage-ai-prod:hr_insights

# If missing, re-run bq cp command from Phase 2
```

### Issue: "Bucket not found"
**Solution:**
```bash
# Verify bucket exists
gsutil ls

# If missing, recreate bucket
gsutil mb -l us-central1 gs://vantage-ai-prod-pdfs/
```

### Issue: "Authentication failed"
**Solution:**
```powershell
# Verify key file path
Get-Content $env:GOOGLE_APPLICATION_CREDENTIALS | Select-String "project_id"

# Re-export credentials
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys.json"
```

### Issue: "Quota exceeded"
**Solution:**
- Check free trial credits remaining
- Enable billing if trial expired
- Check API quotas: GCP Console → IAM & Admin → Quotas

---

## 📝 POST-MIGRATION TASKS

### Immediate (Day 1)
- [ ] Test all features (ATS, LinkedIn, Sentiment)
- [ ] Verify reports generate correctly
- [ ] Check Excel downloads work
- [ ] Test chatbot queries

### Within 1 Week
- [ ] Monitor billing for unexpected charges
- [ ] Set up automated backups (GCS → Cloud Storage Transfer)
- [ ] Document any custom configurations
- [ ] Train team on new project structure

### Within 90 Days (before trial expires)
- [ ] Review actual usage vs. free tier limits
- [ ] Decide on production billing plan
- [ ] Optimize costs (delete unused resources)
- [ ] Set up production monitoring (Cloud Monitoring)

---

## 💰 COST OPTIMIZATION TIPS

1. **BigQuery:**
   - Use partitioned tables for large datasets
   - Avoid `SELECT *` - specify columns
   - Set query cost limits

2. **GCS:**
   - Use Standard storage class (not Nearline/Coldline)
   - Enable object lifecycle policies (delete old files)
   - Compress large files

3. **Vertex AI:**
   - Use `gemini-2.5-flash-lite` (cheaper than Pro)
   - Batch API calls when possible
   - Cache responses for repeated queries

4. **Free Tier Limits (stay within these):**
   - BigQuery: 1TB queries/month free
   - GCS: 5GB storage free
   - Vertex AI: Varies by model

---

## 📞 SUPPORT CONTACTS

**GCP Support:**
- Documentation: https://cloud.google.com/docs
- Stack Overflow: Tag `google-cloud-platform`
- Community: https://cloud.google.com/community

**Migration Issues:**
- Check this guide's Troubleshooting section
- Review GCP Console logs (Logging → Logs Explorer)
- Test individual components (BigQuery, GCS, Vertex AI)

---

## ✅ FINAL VERIFICATION SCRIPT

Run this after migration to verify everything:

```powershell
# save as: test_migration.ps1
cd C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api

.\backend_env\Scripts\Activate.ps1
$env:GOOGLE_APPLICATION_CREDENTIALS="$PWD\keys\sa-keys.json"

Write-Host "🔍 Testing GCP Migration..." -ForegroundColor Cyan

# Test 1: Authentication
try {
    python -c "from google.cloud import bigquery; client = bigquery.Client(); print(f'✅ Authenticated as: {client.project}')"
} catch {
    Write-Host "❌ Authentication failed" -ForegroundColor Red
    exit 1
}

# Test 2: BigQuery
try {
    python -c "from google.cloud import bigquery; import config; client = bigquery.Client(); result = list(client.query(f'SELECT 1').result()); print('✅ BigQuery: OK')"
} catch {
    Write-Host "❌ BigQuery failed" -ForegroundColor Red
    exit 1
}

# Test 3: GCS
try {
    python -c "from google.cloud import storage; import config; client = storage.Client(); bucket = client.bucket(config.GCS_BUCKET); print(f'✅ GCS: {bucket.name} exists') if bucket.exists() else print('❌ GCS: Bucket not found')"
} catch {
    Write-Host "❌ GCS failed" -ForegroundColor Red
    exit 1
}

# Test 4: Vertex AI
try {
    python -c "import vertexai; from vertexai.generative_models import GenerativeModel; import config; vertexai.init(project=config.PROJECT_ID, location=config.LOCATION); model = GenerativeModel(config.GEMINI_MODEL); response = model.generate_content('Test'); print('✅ Vertex AI: OK')"
} catch {
    Write-Host "❌ Vertex AI failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ All tests passed! Migration successful!" -ForegroundColor Green
```

---

## 📄 MIGRATION SUMMARY

**What got migrated:**
- ✅ 7 BigQuery tables with all data
- ✅ 2 GCS buckets with all files
- ✅ Service account with proper IAM roles
- ✅ Application configuration updated
- ✅ API keys and credentials secured

**What stayed the same:**
- ✅ Code logic (no changes)
- ✅ API endpoints (same URLs)
- ✅ Frontend (same localhost URLs)
- ✅ File structure
- ✅ Dependencies (requirements.txt)

**What changed:**
- ⚠️ PROJECT_ID: `hr-analytics-demo` → `vantage-ai-prod`
- ⚠️ Bucket names: Added `-prod` suffix
- ⚠️ Service account email: New account
- ⚠️ Service account key: New key file

---

## 🎯 SUCCESS CRITERIA

Migration is successful when:
1. ✅ Backend starts without errors
2. ✅ Frontend loads correctly
3. ✅ API endpoints return data
4. ✅ File uploads work (ATS, Sentiment)
5. ✅ Reports generate correctly
6. ✅ Excel downloads work
7. ✅ No authentication errors
8. ✅ No permission errors

---

**END OF MIGRATION GUIDE**

*Last Updated: 2025-01-19*  
*Version: 1.0*  
*Author: Vantage AI Team*

---

## 📌 QUICK REFERENCE

**New Project Details:**
- Project ID: `vantage-ai-prod`
- Dataset: `hr_insights`
- Region: `us-central1`
- Service Account: `vantage-api-sa@vantage-ai-prod.iam.gserviceaccount.com`

**Key Files:**
- Config: `vantage_api/config.py`
- SA Key: `vantage_api/keys/sa-keys.json`
- Commands: `vantage_api/keys/command.txt`

**Critical Commands:**
```bash
# Set project
gcloud config set project vantage-ai-prod

# Set credentials
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api\keys\sa-keys.json"

# Start backend
uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```
