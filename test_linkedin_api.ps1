# Test LinkedIn Scout endpoint with mock data
# Make sure server is running first: .\start_server.ps1

Write-Host "🧪 Testing LinkedIn Scout API with Mock Data" -ForegroundColor Green
Write-Host "=" * 60

# Check if server is running
Write-Host "`n1️⃣ Checking server health..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get
    Write-Host "   ✅ Server is running" -ForegroundColor Green
    Write-Host "   Project: $($health.project_id)" -ForegroundColor Gray
    Write-Host "   Dataset: $($health.dataset)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Server is not running!" -ForegroundColor Red
    Write-Host "   Start server with: .\start_server.ps1" -ForegroundColor Yellow
    exit 1
}

# Test LinkedIn Scout endpoint
Write-Host "`n2️⃣ Testing LinkedIn Scout endpoint..." -ForegroundColor Cyan

$body = @{
    job_description = "We are looking for a Senior Data Scientist with 5+ years of experience in machine learning, Python, and cloud technologies. Must have strong statistics background and experience with TensorFlow/PyTorch."
    location = "San Francisco, CA"
    min_experience = 3
    max_experience = 10
    num_candidates = 5
    open_to_work_only = $false
    user_email = "test@fiinch.ai"
    organization_id = "demo_org"
} | ConvertTo-Json

Write-Host "`n📤 Sending request..." -ForegroundColor Gray
Write-Host "   Location: San Francisco, CA" -ForegroundColor Gray
Write-Host "   Candidates: 5" -ForegroundColor Gray
Write-Host "   Experience: 3-10 years" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/agents/linkedin/scout" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body
    
    Write-Host "`n✅ Request successful!" -ForegroundColor Green
    Write-Host "   Job ID: $($response.job_id)" -ForegroundColor Cyan
    Write-Host "   Status: $($response.status)" -ForegroundColor Cyan
    Write-Host "   Message: $($response.message)" -ForegroundColor Gray
    
    # Save job ID for further testing
    $jobId = $response.job_id
    
    # Test get job details
    Write-Host "`n3️⃣ Testing get job details..." -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    
    $jobDetails = Invoke-RestMethod -Uri "http://localhost:8080/agents/linkedin/jobs/$jobId" -Method Get
    Write-Host "   ✅ Job details retrieved" -ForegroundColor Green
    Write-Host "   Total found: $($jobDetails.total_found)" -ForegroundColor Gray
    Write-Host "   Total analyzed: $($jobDetails.total_analyzed)" -ForegroundColor Gray
    Write-Host "   Status: $($jobDetails.status)" -ForegroundColor Gray
    
    Write-Host "`n" + "=" * 60
    Write-Host "✅ ALL TESTS PASSED - Mock LinkedIn is working!" -ForegroundColor Green
    Write-Host "=" * 60
    
} catch {
    Write-Host "`n❌ Request failed!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    
    if ($_.ErrorDetails.Message) {
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Host "   Details: $($errorDetails.detail)" -ForegroundColor Yellow
    }
}

Write-Host "`n💡 View all endpoints: http://localhost:8080/docs`n" -ForegroundColor Cyan
