# BigQuery Migration for DIFFERENT Gmail Accounts
## Complete Step-by-Step Guide

**Scenario:** Source project (`hr-analytics-demo`) and target project (`vantage-ai-prod`) are owned by **different Gmail accounts**.

**Solution:** Export to local files → Upload to new project

**Total Time:** ~60 minutes (30 min export + 30 min import)

---

## 📦 PART 1: EXPORT FROM OLD PROJECT (30 min)

### Step 1: Login with OLD Gmail Account
```powershell
# Open PowerShell as Administrator
# Login with the OLD Gmail account that owns hr-analytics-demo
gcloud auth login

# When browser opens, select the OLD Gmail account
# Wait for "You are now logged in" message
```

### Step 2: Set Old Project and Verify Access
```powershell
# Set to old project
gcloud config set project hr-analytics-demo

# Verify you can see the tables
bq ls hr-analytics-demo:hr_insights

# You should see all 8 tables listed
```

### Step 3: Create Local Export Directory
```powershell
# Create directory for exports
mkdir C:\temp\bq_migration
cd C:\temp\bq_migration
```

### Step 4: Export All Tables to JSON Files
```powershell
# Table 1: linkedin_jobs
Write-Host "`n📤 Exporting 1/8: linkedin_jobs..." -ForegroundColor Cyan
bq extract --destination_format=NEWLINE_DELIMITED_JSON `
  hr-analytics-demo:hr_insights.linkedin_jobs `
  gs://hr-analytics-pdfs/bq_export/linkedin_jobs_*.json

gsutil -m cp gs://hr-analytics-pdfs/bq_export/linkedin_jobs_*.json .\
Remove-Item gs://hr-analytics-pdfs/bq_export/linkedin_jobs_*.json

# Table 2: linkedin_results
Write-Host "`n📤 Exporting 2/8: linkedin_results..." -ForegroundColor Cyan
bq extract --destination_format=NEWLINE_DELIMITED_JSON `
  hr-analytics-demo:hr_insights.linkedin_results `
  gs://hr-analytics-pdfs/bq_export/linkedin_results_*.json

gsutil -m cp gs://hr-analytics-pdfs/bq_export/linkedin_results_*.json .\
gsutil rm gs://hr-analytics-pdfs/bq_export/linkedin_results_*.json

# Table 3: ats_jobs
Write-Host "`n📤 Exporting 3/8: ats_jobs..." -ForegroundColor Cyan
bq extract --destination_format=NEWLINE_DELIMITED_JSON `
  hr-analytics-demo:hr_insights.ats_jobs `
  gs://hr-analytics-pdfs/bq_export/ats_jobs_*.json

gsutil -m cp gs://hr-analytics-pdfs/bq_export/ats_jobs_*.json .\
gsutil rm gs://hr-analytics-pdfs/bq_export/ats_jobs_*.json

# Table 4: ats_results
Write-Host "`n📤 Exporting 4/8: ats_results..." -ForegroundColor Cyan
bq extract --destination_format=NEWLINE_DELIMITED_JSON `
  hr-analytics-demo:hr_insights.ats_results `
  gs://hr-analytics-pdfs/bq_export/ats_results_*.json

gsutil -m cp gs://hr-analytics-pdfs/bq_export/ats_results_*.json .\
gsutil rm gs://hr-analytics-pdfs/bq_export/ats_results_*.json

# Table 5: sentiment_jobs
Write-Host "`n📤 Exporting 5/8: sentiment_jobs..." -ForegroundColor Cyan
bq extract --destination_format=NEWLINE_DELIMITED_JSON `
  hr-analytics-demo:hr_insights.sentiment_jobs `
  gs://hr-analytics-pdfs/bq_export/sentiment_jobs_*.json

gsutil -m cp gs://hr-analytics-pdfs/bq_export/sentiment_jobs_*.json .\
gsutil rm gs://hr-analytics-pdfs/bq_export/sentiment_jobs_*.json

# Table 6: sentiment_results
Write-Host "`n📤 Exporting 6/8: sentiment_results..." -ForegroundColor Cyan
bq extract --destination_format=NEWLINE_DELIMITED_JSON `
  hr-analytics-demo:hr_insights.sentiment_results `
  gs://hr-analytics-pdfs/bq_export/sentiment_results_*.json

gsutil -m cp gs://hr-analytics-pdfs/bq_export/sentiment_results_*.json .\
gsutil rm gs://hr-analytics-pdfs/bq_export/sentiment_results_*.json

# Table 7: journal_vectors
Write-Host "`n📤 Exporting 7/8: journal_vectors..." -ForegroundColor Cyan
bq extract --destination_format=NEWLINE_DELIMITED_JSON `
  hr-analytics-demo:hr_insights.journal_vectors `
  gs://hr-analytics-pdfs/bq_export/journal_vectors_*.json

gsutil -m cp gs://hr-analytics-pdfs/bq_export/journal_vectors_*.json .\
gsutil rm gs://hr-analytics-pdfs/bq_export/journal_vectors_*.json

# Table 8: sessions
Write-Host "`n📤 Exporting 8/8: sessions..." -ForegroundColor Cyan
bq extract --destination_format=NEWLINE_DELIMITED_JSON `
  hr-analytics-demo:hr_insights.sessions `
  gs://hr-analytics-pdfs/bq_export/sessions_*.json

gsutil -m cp gs://hr-analytics-pdfs/bq_export/sessions_*.json .\
gsutil rm gs://hr-analytics-pdfs/bq_export/sessions_*.json

Write-Host "`n✅ All tables exported to C:\temp\bq_migration\" -ForegroundColor Green
```

### Step 5: Verify Export Files
```powershell
# Check exported files
Get-ChildItem C:\temp\bq_migration\

# You should see JSON files for all 8 tables
# linkedin_jobs_*.json
# linkedin_results_*.json
# ats_jobs_*.json
# ats_results_*.json
# sentiment_jobs_*.json
# sentiment_results_*.json
# journal_vectors_*.json
# sessions_*.json
```

---

## 📥 PART 2: IMPORT TO NEW PROJECT (30 min)

### Step 6: Switch to NEW Gmail Account
```powershell
# IMPORTANT: Logout from old account and login with NEW account
gcloud auth revoke  # Logout from old account

# Login with NEW Gmail account
gcloud auth login
# When browser opens, select the NEW Gmail account that owns vantage-ai-prod
```

### Step 7: Set New Project
```powershell
# Set to new project
gcloud config set project vantage-ai-prod

# Verify access
gcloud projects describe vantage-ai-prod
```

### Step 8: Create Dataset (if not already created)
```powershell
# Create the hr_insights dataset
bq mk --dataset --location=us-central1 --description="HR Analytics Dataset" vantage-ai-prod:hr_insights

# Verify
bq ls vantage-ai-prod:hr_insights
```

### Step 8.5: Export Source Schemas (CRITICAL)
```powershell
# Make sure you're logged in as source account
gcloud config set account sovikde89@gmail.com
gcloud config set project hr-analytics-demo

# Navigate to export directory
cd C:\temp\bq_migration

# Export schemas for the 3 problematic tables
Write-Host "`n📋 Exporting schemas from source..." -ForegroundColor Cyan

bq show --schema --format=prettyjson hr-analytics-demo:hr_insights.ats_results > ats_results_schema.json
bq show --schema --format=prettyjson hr-analytics-demo:hr_insights.sentiment_jobs > sentiment_jobs_schema.json
bq show --schema --format=prettyjson hr-analytics-demo:hr_insights.sentiment_results > sentiment_results_schema.json

Write-Host "✅ Schemas exported" -ForegroundColor Green
```

### Step 9: Import All Tables from Local Files
```powershell
# Switch to destination account
gcloud config set account orvahrai@gmail.com
gcloud config set project vantage-ai-prod

# Navigate to export directory
cd C:\temp\bq_migration

# Delete and recreate the 3 problematic tables with correct schemas
Write-Host "`n🔧 Fixing schema mismatches..." -ForegroundColor Yellow

# Delete existing tables with wrong schemas
bq rm -f -t vantage-ai-prod:hr_insights.ats_results
bq rm -f -t vantage-ai-prod:hr_insights.sentiment_jobs
bq rm -f -t vantage-ai-prod:hr_insights.sentiment_results

# Create tables with correct schemas
bq mk --table vantage-ai-prod:hr_insights.ats_results ats_results_schema.json
bq mk --table vantage-ai-prod:hr_insights.sentiment_jobs sentiment_jobs_schema.json
bq mk --table vantage-ai-prod:hr_insights.sentiment_results sentiment_results_schema.json

Write-Host "✅ Tables recreated with correct schemas" -ForegroundColor Green

# Table 1: linkedin_jobs (already imported, skip)
Write-Host "`n✓ linkedin_jobs - Already imported" -ForegroundColor Gray

# Table 2: linkedin_results (already imported, skip)
Write-Host "✓ linkedin_results - Already imported" -ForegroundColor Gray

# Table 3: ats_jobs (already imported, skip)
Write-Host "✓ ats_jobs - Already imported" -ForegroundColor Gray

# Table 4: ats_results (reload with correct schema)
Write-Host "`n📥 Importing 4/8: ats_results..." -ForegroundColor Cyan
Get-ChildItem ats_results_*.json | ForEach-Object {
    bq load --source_format=NEWLINE_DELIMITED_JSON `
      --schema=ats_results_schema.json `
      vantage-ai-prod:hr_insights.ats_results `
      $_.Name
}

# Table 5: sentiment_jobs (reload with correct schema)
Write-Host "`n📥 Importing 5/8: sentiment_jobs..." -ForegroundColor Cyan
Get-ChildItem sentiment_jobs_*.json | ForEach-Object {
    bq load --source_format=NEWLINE_DELIMITED_JSON `
      --schema=sentiment_jobs_schema.json `
      vantage-ai-prod:hr_insights.sentiment_jobs `
      $_.Name
}

# Table 6: sentiment_results (reload with correct schema)
Write-Host "`n📥 Importing 6/8: sentiment_results..." -ForegroundColor Cyan
Get-ChildItem sentiment_results_*.json | ForEach-Object {
    bq load --source_format=NEWLINE_DELIMITED_JSON `
      --schema=sentiment_results_schema.json `
      vantage-ai-prod:hr_insights.sentiment_results `
      $_.Name
}

# Table 7: journal_vectors (already imported, skip)
Write-Host "`n✓ journal_vectors - Already imported" -ForegroundColor Gray

# Table 8: sessions (already imported, skip)
Write-Host "`n✓ sessions - Already imported" -ForegroundColor Gray

Write-Host "`n✅ All tables imported to vantage-ai-prod!" -ForegroundColor Green
```

### Step 10: Verify Import
```powershell
# List all tables in new project
bq ls vantage-ai-prod:hr_insights

# Check row counts
bq query --use_legacy_sql=false `
"SELECT 
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.linkedin_jobs\`) as linkedin_jobs,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.linkedin_results\`) as linkedin_results,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.ats_jobs\`) as ats_jobs,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.ats_results\`) as ats_results,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.sentiment_jobs\`) as sentiment_jobs,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.sentiment_results\`) as sentiment_results,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.journal_vectors\`) as journal_vectors,
  (SELECT COUNT(*) FROM \`vantage-ai-prod.hr_insights.sessions\`) as sessions"

# Test sample query
bq query --use_legacy_sql=false `
"SELECT * FROM \`vantage-ai-prod.hr_insights.linkedin_jobs\` LIMIT 5"
```

### Step 11: Cleanup (Optional)
```powershell
# After verifying import success, cleanup local files
# Remove-Item C:\temp\bq_migration\* -Recurse -Force

# Or keep them as backup for now
Write-Host "`n💡 Tip: Keep C:\temp\bq_migration\ as backup until fully verified" -ForegroundColor Yellow
```

---

## ✅ VERIFICATION CHECKLIST

- [ ] All 8 tables visible in `bq ls vantage-ai-prod:hr_insights`
- [ ] Row counts match between old and new project
- [ ] Sample queries return correct data
- [ ] No errors in import logs

---

## 🆘 TROUBLESHOOTING

### Issue: "Permission denied" during export
**Cause:** Not logged in with old Gmail account  
**Solution:** Run `gcloud auth login` and select OLD account

### Issue: "Dataset not found" during import
**Cause:** Dataset not created in new project  
**Solution:** Run `bq mk --dataset vantage-ai-prod:hr_insights`

### Issue: "Invalid schema" during import
**Cause:** `--autodetect` failed  
**Solution:** Export schema from old table and use it explicitly:
```powershell
# Get schema from old project
bq show --schema hr-analytics-demo:hr_insights.linkedin_jobs > schema.json

# Load with explicit schema
bq load --source_format=NEWLINE_DELIMITED_JSON `
  --schema=schema.json `
  vantage-ai-prod:hr_insights.linkedin_jobs `
  linkedin_jobs_*.json
```

### Issue: "Out of disk space"
**Cause:** Large tables don't fit in C:\temp  
**Solution:** Use external drive or cloud storage:
```powershell
# Export to external drive
mkdir D:\bq_migration
cd D:\bq_migration
# Then run export commands
```

---

## 💡 PRO TIPS

1. **Test with one table first:**
   ```powershell
   # Export just linkedin_jobs
   bq extract --destination_format=NEWLINE_DELIMITED_JSON `
     hr-analytics-demo:hr_insights.linkedin_jobs `
     gs://hr-analytics-pdfs/bq_export/test_*.json
   
   # Download and import
   gsutil -m cp gs://hr-analytics-pdfs/bq_export/test_*.json .\
   bq load --source_format=NEWLINE_DELIMITED_JSON --autodetect `
     vantage-ai-prod:hr_insights.linkedin_jobs `
     test_*.json
   ```

2. **Monitor progress:**
   ```powershell
   # Check BigQuery job status
   bq ls -j -a -n 10
   ```

3. **Parallel processing (faster):**
   - Export all 8 tables simultaneously in separate PowerShell windows
   - Import all 8 tables simultaneously in separate windows
   - Can reduce time from 60 min to 20 min

---

## 📊 EXPECTED FILE SIZES

Approximate sizes (adjust based on your data):
- `linkedin_jobs`: ~10 MB
- `linkedin_results`: ~50 MB
- `ats_jobs`: ~5 MB
- `ats_results`: ~20 MB
- `sentiment_jobs`: ~5 MB
- `sentiment_results`: ~15 MB
- `journal_vectors`: ~100 MB (contains embeddings)
- `sessions`: ~2 MB

**Total:** ~207 MB (ensure C:\temp has at least 500 MB free)

---

**Next Steps:** After successful migration, proceed to **Phase 3: GCS Bucket Migration** in the main guide.
