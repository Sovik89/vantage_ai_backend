# End-to-End Test Plan
## Final Validation Before Shutting Down hr-analytics-demo

**Test Date:** November 21, 2025 (Morning)  
**Project:** vantage-ai-prod  
**Objective:** Verify all functionality works before decommissioning hr-analytics-demo  
**Duration:** ~30-45 minutes  

---

## Pre-Test Checklist

### Environment Setup
```powershell
# 1. Navigate to project directory
cd C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\vantage_ai_backend-main_code\vantage_api

# 2. Activate virtual environment
.\backend_env\Scripts\Activate.ps1

# 3. Verify service account
gcloud auth activate-service-account --key-file=keys/sa-keys.json
gcloud config set project vantage-ai-prod

# 4. Verify environment variables
$env:GOOGLE_APPLICATION_CREDENTIALS = "keys/sa-keys.json"
$env:GCP_PROJECT_ID = "vantage-ai-prod"
```

---

## TEST SUITE 1: Core Infrastructure (10 min)

### Test 1.1: BigQuery Connection
```powershell
Write-Host "`n=== TEST 1.1: BigQuery Connection ===" -ForegroundColor Cyan

# Verify all tables exist
bq ls vantage-ai-prod:hr_insights

# Expected: 8 tables listed
# ✅ PASS if all 8 tables shown
# ❌ FAIL if missing tables
```

**Pass Criteria:** 8 tables visible (ats_jobs, ats_results, journal_vectors, linkedin_jobs, linkedin_results, sentiment_jobs, sentiment_results, sessions)

### Test 1.2: GCS Bucket Access
```powershell
Write-Host "`n=== TEST 1.2: GCS Bucket Access ===" -ForegroundColor Cyan

# List all buckets
gsutil ls

# Verify each bucket
gsutil ls gs://vantage-ai-prod-pdfs/ | Select-Object -First 5
gsutil ls gs://vantage-ai-prod-journals/
```

**Pass Criteria:** All 4 buckets accessible, files visible in pdfs and journals buckets

### Test 1.3: Vertex AI Connection
```powershell
Write-Host "`n=== TEST 1.3: Vertex AI Connection ===" -ForegroundColor Cyan

python -c "import vertexai; from vertexai.generative_models import GenerativeModel; vertexai.init(project='vantage-ai-prod', location='us-central1'); model = GenerativeModel('gemini-2.5-flash-lite'); print('✅ Vertex AI Connected')"
```

**Pass Criteria:** No errors, "✅ Vertex AI Connected" displayed

---

## TEST SUITE 2: API Endpoints (15 min)

### Test 2.1: Start API Server
```powershell
Write-Host "`n=== TEST 2.1: Start API Server ===" -ForegroundColor Cyan

# Start the FastAPI server
uvicorn main:app --reload --port 8000
```

**Pass Criteria:** Server starts without errors on http://localhost:8000

### Test 2.2: Health Check Endpoint
```powershell
# In a new terminal
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "project": "vantage-ai-prod"
}
```

### Test 2.3: List Sessions
```powershell
curl http://localhost:8000/sessions/list?user_email=guest@vantage.ai
```

**Pass Criteria:** Returns list of sessions from BigQuery

### Test 2.4: List Jobs (LinkedIn)
```powershell
curl http://localhost:8000/linkedin/jobs/list?user_email=guest@vantage.ai
```

**Pass Criteria:** Returns LinkedIn jobs from BigQuery

### Test 2.5: List Jobs (ATS)
```powershell
curl http://localhost:8000/ats/jobs/list?user_email=guest@vantage.ai
```

**Pass Criteria:** Returns ATS jobs from BigQuery

### Test 2.6: List Jobs (Sentiment)
```powershell
curl http://localhost:8000/sentiment/jobs/list?user_email=guest@vantage.ai
```

**Pass Criteria:** Returns sentiment jobs from BigQuery

---

## TEST SUITE 3: Data Operations (10 min)

### Test 3.1: Query BigQuery Data
```powershell
Write-Host "`n=== TEST 3.1: Query BigQuery Data ===" -ForegroundColor Cyan

python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys/sa-keys.json'
from google.cloud import bigquery

client = bigquery.Client(project='vantage-ai-prod')

# Test query
query = '''
SELECT job_id, user_email, status, created_at 
FROM \`vantage-ai-prod.hr_insights.linkedin_jobs\` 
ORDER BY created_at DESC 
LIMIT 5
'''

results = client.query(query).result()
print('Recent LinkedIn Jobs:')
for row in results:
    print(f'  {row.job_id} | {row.status} | {row.user_email}')
print('✅ Query successful')
"
```

**Pass Criteria:** Returns 5 most recent jobs

### Test 3.2: Write to BigQuery
```powershell
Write-Host "`n=== TEST 3.2: Write to BigQuery ===" -ForegroundColor Cyan

python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys/sa-keys.json'
from google.cloud import bigquery
from datetime import datetime
import uuid

client = bigquery.Client(project='vantage-ai-prod')

# Insert test session
test_data = [{
    'session_id': f'test_{uuid.uuid4().hex[:8]}',
    'user_email': 'test@migration.test',
    'created_at': datetime.utcnow().isoformat(),
    'status': 'active'
}]

table_id = 'vantage-ai-prod.hr_insights.sessions'
errors = client.insert_rows_json(table_id, test_data)

if not errors:
    print('✅ Write successful')
else:
    print(f'❌ Errors: {errors}')
"
```

**Pass Criteria:** Test record inserted successfully

### Test 3.3: Read from GCS
```powershell
Write-Host "`n=== TEST 3.3: Read from GCS ===" -ForegroundColor Cyan

python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys/sa-keys.json'
from google.cloud import storage

client = storage.Client(project='vantage-ai-prod')
bucket = client.bucket('vantage-ai-prod-pdfs')

# List first 5 files
blobs = list(bucket.list_blobs(max_results=5))
print('Files in bucket:')
for blob in blobs:
    print(f'  {blob.name}')
print('✅ Read successful')
"
```

**Pass Criteria:** Lists files from bucket

### Test 3.4: Write to GCS
```powershell
Write-Host "`n=== TEST 3.4: Write to GCS ===" -ForegroundColor Cyan

python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys/sa-keys.json'
from google.cloud import storage
from datetime import datetime

client = storage.Client(project='vantage-ai-prod')
bucket = client.bucket('vantage-ai-prod-pdfs')

# Upload test file
test_content = f'Test file created at {datetime.utcnow()}'
blob = bucket.blob('test/migration_test.txt')
blob.upload_from_string(test_content)
print('✅ Upload successful')

# Read back
content = blob.download_as_text()
print(f'Content: {content}')

# Cleanup
blob.delete()
print('✅ Cleanup successful')
"
```

**Pass Criteria:** File uploaded, read, and deleted successfully

---

## TEST SUITE 4: AI/ML Features (10 min)

### Test 4.1: Gemini Text Generation
```powershell
Write-Host "`n=== TEST 4.1: Gemini Text Generation ===" -ForegroundColor Cyan

python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys/sa-keys.json'
import vertexai
from vertexai.generative_models import GenerativeModel

vertexai.init(project='vantage-ai-prod', location='us-central1')
model = GenerativeModel('gemini-2.5-flash-lite')

prompt = '''
Analyze this candidate profile:
Name: John Doe
Title: Senior Data Engineer
Experience: 5 years
Skills: Python, SQL, BigQuery, Airflow

Rate this candidate for a Data Engineer role (1-10) and explain in 2 sentences.
'''

response = model.generate_content(prompt)
print('Response:')
print(response.text)
print('✅ Generation successful')
"
```

**Pass Criteria:** Generates coherent analysis with rating

### Test 4.2: Generate Embeddings
```powershell
Write-Host "`n=== TEST 4.2: Generate Embeddings ===" -ForegroundColor Cyan

python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys/sa-keys.json'
import vertexai
from vertexai.language_models import TextEmbeddingModel

vertexai.init(project='vantage-ai-prod', location='us-central1')
model = TextEmbeddingModel.from_pretrained('text-embedding-004')

texts = [
    'Senior Data Engineer with Python expertise',
    'Junior Frontend Developer with React skills',
    'DevOps Engineer specialized in Kubernetes'
]

embeddings = model.get_embeddings(texts)
print(f'Generated {len(embeddings)} embeddings')
print(f'Dimensions: {len(embeddings[0].values)}')
print('✅ Embeddings successful')
"
```

**Pass Criteria:** Generates 768-dimensional vectors for all texts

### Test 4.3: Resume Analysis (Full Workflow)
```powershell
Write-Host "`n=== TEST 4.3: Resume Analysis Workflow ===" -ForegroundColor Cyan

# This would test the full ATS upload flow
# If you have a test endpoint:
curl -X POST http://localhost:8000/ats/upload \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "test@migration.test",
    "job_description": "Senior Data Engineer with 5+ years Python experience"
  }'
```

**Pass Criteria:** Returns job_id and status

---

## TEST SUITE 5: Integration Tests (5 min)

### Test 5.1: End-to-End LinkedIn Scout Flow
```powershell
Write-Host "`n=== TEST 5.1: LinkedIn Scout Flow ===" -ForegroundColor Cyan

# Step 1: Create job
$response = curl -X POST http://localhost:8000/linkedin/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "test@migration.test",
    "job_title": "Data Engineer",
    "location": "San Francisco",
    "num_profiles": 5
  }'

# Step 2: Check job status
# Extract job_id from response
curl http://localhost:8000/linkedin/jobs/{job_id}/status

# Step 3: Verify job in BigQuery
bq query --use_legacy_sql=false \
"SELECT job_id, status FROM \`vantage-ai-prod.hr_insights.linkedin_jobs\` WHERE user_email='test@migration.test' ORDER BY created_at DESC LIMIT 1"
```

**Pass Criteria:** Job created, status retrieved, visible in BigQuery

### Test 5.2: Journal Vector Search
```powershell
Write-Host "`n=== TEST 5.2: Journal Vector Search ===" -ForegroundColor Cyan

python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys/sa-keys.json'
from google.cloud import bigquery

client = bigquery.Client(project='vantage-ai-prod')

# Query journal vectors
query = '''
SELECT vector_id, text_chunk, chunk_index
FROM \`vantage-ai-prod.hr_insights.journal_vectors\`
LIMIT 3
'''

results = client.query(query).result()
print('Journal Vectors:')
for row in results:
    print(f'  ID: {row.vector_id} | Chunk: {row.chunk_index}')
print('✅ Vector retrieval successful')
"
```

**Pass Criteria:** Returns journal vector records

---

## TEST SUITE 6: Performance & Reliability (5 min)

### Test 6.1: Response Time
```powershell
Write-Host "`n=== TEST 6.1: Response Time ===" -ForegroundColor Cyan

Measure-Command {
    curl http://localhost:8000/sessions/list?user_email=guest@vantage.ai
}
```

**Pass Criteria:** Response time < 2 seconds

### Test 6.2: Concurrent Requests
```powershell
Write-Host "`n=== TEST 6.2: Concurrent Requests ===" -ForegroundColor Cyan

# Run 5 concurrent requests
1..5 | ForEach-Object -Parallel {
    curl http://localhost:8000/health
} -ThrottleLimit 5
```

**Pass Criteria:** All requests succeed

### Test 6.3: Error Handling
```powershell
Write-Host "`n=== TEST 6.3: Error Handling ===" -ForegroundColor Cyan

# Test invalid request
curl http://localhost:8000/sessions/list
# Should return proper error (missing user_email)
```

**Pass Criteria:** Returns appropriate error message

---

## Post-Test Validation

### Data Comparison (Optional but Recommended)
```powershell
Write-Host "`n=== Data Comparison: Old vs New ===" -ForegroundColor Yellow

# Compare row counts
Write-Host "OLD PROJECT (hr-analytics-demo):" -ForegroundColor Red
gcloud config set project hr-analytics-demo
bq query --use_legacy_sql=false "SELECT COUNT(*) as count FROM \`hr-analytics-demo.hr_insights.linkedin_jobs\`"

Write-Host "`nNEW PROJECT (vantage-ai-prod):" -ForegroundColor Green
gcloud config set project vantage-ai-prod
bq query --use_legacy_sql=false "SELECT COUNT(*) as count FROM \`vantage-ai-prod.hr_insights.linkedin_jobs\`"
```

---

## Test Results Checklist

### Infrastructure Tests
- [ ] 1.1 BigQuery Connection
- [ ] 1.2 GCS Bucket Access
- [ ] 1.3 Vertex AI Connection

### API Tests
- [ ] 2.1 API Server Start
- [ ] 2.2 Health Check
- [ ] 2.3 List Sessions
- [ ] 2.4 List LinkedIn Jobs
- [ ] 2.5 List ATS Jobs
- [ ] 2.6 List Sentiment Jobs

### Data Operations
- [ ] 3.1 Query BigQuery
- [ ] 3.2 Write to BigQuery
- [ ] 3.3 Read from GCS
- [ ] 3.4 Write to GCS

### AI/ML Features
- [ ] 4.1 Gemini Generation
- [ ] 4.2 Embeddings
- [ ] 4.3 Resume Analysis

### Integration Tests
- [ ] 5.1 LinkedIn Scout Flow
- [ ] 5.2 Journal Vector Search

### Performance Tests
- [ ] 6.1 Response Time
- [ ] 6.2 Concurrent Requests
- [ ] 6.3 Error Handling

---

## Decision Matrix

### IF ALL TESTS PASS ✅
**Action:** Proceed with decommissioning hr-analytics-demo
1. Archive old project data
2. Remove old service accounts
3. Update all documentation
4. Notify team of successful migration

### IF ANY CRITICAL TEST FAILS ❌
**Action:** DO NOT shut down old project
1. Document failing test
2. Compare with old project behavior
3. Fix issue in new project
4. Re-run full test suite
5. Only proceed when all tests pass

### Critical Tests (Must Pass)
- ✅ BigQuery Connection
- ✅ GCS Bucket Access
- ✅ Vertex AI Connection
- ✅ API Health Check
- ✅ Data Query/Write Operations

### Non-Critical Tests (Nice to Have)
- Performance benchmarks
- Advanced error handling
- Specific workflow tests

---

## Cleanup After Testing

```powershell
# Remove test data
python -c "
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'keys/sa-keys.json'
from google.cloud import bigquery

client = bigquery.Client(project='vantage-ai-prod')
query = '''
DELETE FROM \`vantage-ai-prod.hr_insights.sessions\`
WHERE user_email = 'test@migration.test'
'''
client.query(query).result()
print('✅ Test data cleaned up')
"
```

---

## Emergency Rollback Plan

### IF Migration Needs to be Rolled Back:
1. **Immediate:** Switch back to old project
   ```powershell
   gcloud config set project hr-analytics-demo
   # Update config.py to use old values
   ```

2. **Short-term:** Keep both projects running
   - Use old project for production
   - Fix issues in new project
   - Re-test when ready

3. **Data Sync:** If new data was created
   ```powershell
   # Export new data from vantage-ai-prod
   # Import to hr-analytics-demo
   # Run validation queries
   ```

---

## Success Criteria Summary

**PASS Requirements:**
- ✅ All 6 critical tests pass
- ✅ API responds to all endpoints
- ✅ Data reads/writes work
- ✅ AI features functional
- ✅ No data loss detected
- ✅ Response times acceptable

**GO/NO-GO Decision:**
- **GO:** All critical tests pass → Proceed with shutdown
- **NO-GO:** Any critical test fails → Keep old project running

---

## Contact for Issues

**If issues found during testing:**
- Document exact error message
- Note which test failed
- Check service account permissions
- Verify config.py settings
- Review COMPLETE_MIGRATION_DOCUMENTATION.md

---

**Test Date:** Tomorrow Morning (November 21, 2025)  
**Estimated Duration:** 30-45 minutes  
**Next Step:** Decommission hr-analytics-demo (if all tests pass)

**Good luck with the testing! 🚀**
