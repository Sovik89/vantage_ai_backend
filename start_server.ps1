# Startup script for Vantage API with proper GCP credentials
# Sets environment variables and starts FastAPI server

Write-Host "🚀 Starting Vantage.AI Backend Server..." -ForegroundColor Green
Write-Host ""

# Set Google Cloud credentials (REQUIRED for BigQuery, GCS access)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\DataEngineering\1GenAI_demo_for_PA_in_GCP\hr_analytics_demo\keys\sa-keys.json"
Write-Host "✅ Google Cloud credentials set" -ForegroundColor Green
Write-Host "   Path: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Gray

# Verify credentials file exists
if (Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS) {
    Write-Host "✅ Service account key file found" -ForegroundColor Green
} else {
    Write-Host "❌ ERROR: Service account key file not found!" -ForegroundColor Red
    Write-Host "   Expected: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Yellow
    exit 1
}

# Check mock mode status
Write-Host ""
Write-Host "📋 Configuration Check:" -ForegroundColor Cyan
python -c "import config; print(f'   🧪 Mock LinkedIn Data: {\"ENABLED\" if config.USE_MOCK_LINKEDIN_DATA else \"DISABLED\"}')"
Write-Host "   ✅ Lazy model loading: Models initialize on first use (after auth)" -ForegroundColor Green

Write-Host ""
Write-Host "🌐 Starting server on http://localhost:8080" -ForegroundColor Cyan
Write-Host "📚 API Docs: http://localhost:8080/docs" -ForegroundColor Cyan
Write-Host "🧪 Mock Mode: No LinkedIn scraping costs!" -ForegroundColor Yellow
Write-Host ""

# Start uvicorn server
uvicorn main:app --reload --port 8080 --host 0.0.0.0
