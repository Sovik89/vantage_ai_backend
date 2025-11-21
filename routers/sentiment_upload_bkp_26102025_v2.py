# routers/sentiment_upload.py
"""
Sentiment Analyzer Router - Unified Pattern with GCS Storage
Minimal changes - works with existing sentiment_processing.py AS-IS
"""

import uuid
import json
import traceback
import os
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from google.cloud import bigquery, storage
import config

# Import sentiment processing worker
try:
    from worker import sentiment_processing
except ImportError as e:
    print(f"❌ ERROR: Could not import sentiment_processing: {e}")
    raise

router = APIRouter()

# Initialize clients
_bq = bigquery.Client(project=config.PROJECT_ID)
_storage = storage.Client(project=config.PROJECT_ID)

# Table references
DATASET_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}"
SENTIMENT_JOBS_TABLE = f"{DATASET_ID}.sentiment_jobs"
SENTIMENT_RESULTS_TABLE = f"{DATASET_ID}.sentiment_results"

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class SubmitResponse(BaseModel):
    """Response from POST /agents/sentiment/submit"""
    job_id: str
    status: str
    message: str
    total_items: Optional[int] = None
    check_status_at: str
    estimated_time_minutes: int

class StatusResponse(BaseModel):
    """Response from GET /agents/sentiment/status/{job_id}"""
    job_id: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    report_url: Optional[str] = None

class ResultsSummary(BaseModel):
    """Summary statistics for sentiment results"""
    summary_text: Optional[str] = None  # From return value of process_job
    total_texts: int
    positive_count: int
    neutral_count: int
    negative_count: int
    sentiment_index: float
    average_confidence: float

class ResultsResponse(BaseModel):
    """Response from GET /agents/sentiment/results/{job_id}"""
    job_id: str
    summary: ResultsSummary
    sentiment_breakdown: Dict
    key_themes: Optional[List[str]] = None
    report_url: Optional[str] = None

class JobListItem(BaseModel):
    """Single job in list response"""
    job_id: str
    status: str
    created_at: str
    organization_id: str

class JobsResponse(BaseModel):
    """Response from GET /agents/sentiment/jobs"""
    total: int
    jobs: List[JobListItem]

# ============================================================================
# ENDPOINT 1: POST /agents/sentiment/submit
# ============================================================================

@router.post("/submit", response_model=SubmitResponse)
async def submit_sentiment_job(
    file: UploadFile = File(...),
    domain: str = Form("employee_feedback"),
    user_email: str = Form("guest@orvahr.ai"),
    organization_id: str = Form("guest_org"),
    include_full_text: bool = Form(False)
):
    """Submit employee feedback file for sentiment analysis"""
    
    print(f"\n{'='*80}")
    print(f"🎭 NEW SENTIMENT ANALYSIS JOB")
    print(f"{'='*80}")
    print(f"📁 File: {file.filename}")
    print(f"📊 Domain: {domain}")
    print(f"👤 User: {user_email}")
    
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(
                status_code=400,
                detail="Only Excel (.xlsx, .xls) and CSV files are supported"
            )
        
        # Read file content
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        
        if file_size_mb > 50:
            raise HTTPException(status_code=400, detail=f"File too large: {file_size_mb:.1f}MB")
        
        print(f"✅ File validated: {file.filename} ({file_size_mb:.2f}MB)")
        
        # Prepare payload
        payload = {
            "filename": file.filename,
            "file_bytes": content.hex(),
            "domain": domain,
            "user_email": user_email,
            "organization_id": organization_id,
            "include_full_text": include_full_text
        }
        
        print(f"🚀 Starting sentiment processing...")
        
        # Call processing - returns (result_id, summary_text)
        result_id, summary_text = sentiment_processing.process_job(payload, sync_mode=True)
        
        if not result_id or (summary_text and summary_text.startswith("error")):
            raise HTTPException(status_code=500, detail=f"Processing failed: {summary_text}")
        
        print(f"✅ Processing completed! Result ID: {result_id}")
        
        # Get job_id from BigQuery
        job_query = f"""
        SELECT job_id, total_texts
        FROM `{SENTIMENT_RESULTS_TABLE}`
        WHERE result_id = @result_id
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("result_id", "STRING", result_id)]
        )
        
        results = list(_bq.query(job_query, job_config=job_config).result())
        
        if not results:
            raise HTTPException(status_code=500, detail="Job not found after processing")
        
        job_id = results[0].job_id
        total_texts = results[0].total_texts
        
        print(f"✅ Job ID: {job_id}")
        
        # Upload Excel to GCS
        report_url = None
        try:
            from worker.sentiment_processing import LOCAL_REPORT_DIR
            local_excel_path = os.path.join(LOCAL_REPORT_DIR, f"sentiment-candidate-report-{job_id}.xlsx")
            
            if os.path.exists(local_excel_path):
                excel_filename = f"Sentiment_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                bucket_name = config.GCS_BUCKET
                blob_path = f"sentiment-reports/{user_email.replace('@', '_at_').replace('.', '_')}/{job_id}/{excel_filename}"
                
                bucket = _storage.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                blob.upload_from_filename(local_excel_path)
                
                # Generate signed URL (7 days)
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(days=7),
                    method="GET"
                )
                
                report_url = signed_url
                print(f"✅ Excel uploaded: gs://{bucket_name}/{blob_path}")
                
                # Update BigQuery with report_url
                update_sql = f"""
                UPDATE `{SENTIMENT_JOBS_TABLE}`
                SET report_url = @report_url,
                    status = 'COMPLETED',
                    updated_at = CURRENT_TIMESTAMP()
                WHERE job_id = @job_id
                """
                
                update_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("report_url", "STRING", signed_url),
                        bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
                    ]
                )
                
                _bq.query(update_sql, job_config=update_config).result()
                
        except Exception as e:
            print(f"⚠️ Excel upload failed: {e}")
            traceback.print_exc()
        
        return SubmitResponse(
            job_id=job_id,
            status="COMPLETED",
            message=f"Successfully analyzed sentiment for {file.filename}",
            total_items=total_texts,
            check_status_at=f"/agents/sentiment/status/{job_id}",
            estimated_time_minutes=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 2: GET /agents/sentiment/status/{job_id}
# ============================================================================

@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_sentiment_status(job_id: str):
    """Check status of a sentiment analysis job"""
    
    try:
        sql = f"""
        SELECT job_id, status, created_at, updated_at, report_url, error_message
        FROM `{SENTIMENT_JOBS_TABLE}`
        WHERE job_id = @job_id
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("job_id", "STRING", job_id)]
        )
        
        results = list(_bq.query(sql, job_config=job_config).result())
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = results[0]
        
        completed_at = None
        if job.status == "COMPLETED" and job.updated_at:
            completed_at = job.updated_at.isoformat()
        
        return StatusResponse(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at.isoformat() if job.created_at else None,
            updated_at=job.updated_at.isoformat() if job.updated_at else None,
            completed_at=completed_at,
            error_message=job.error_message,
            report_url=job.report_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 3: GET /agents/sentiment/results/{job_id}
# ============================================================================

@router.get("/results/{job_id}", response_model=ResultsResponse)
async def get_sentiment_results(job_id: str):
    """Get detailed sentiment analysis results"""
    
    try:
        # Check job status
        status_sql = f"""
        SELECT status, report_url
        FROM `{SENTIMENT_JOBS_TABLE}`
        WHERE job_id = @job_id
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("job_id", "STRING", job_id)]
        )
        
        status_results = list(_bq.query(status_sql, job_config=job_config).result())
        
        if not status_results:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        status_row = status_results[0]
        
        if status_row.status != "COMPLETED":
            return {
                "job_id": job_id,
                "status": status_row.status,
                "message": f"Job is {status_row.status}. Results not yet available."
            }
        
        # Get results - NOTE: summary_text might be NULL since it's not in overall_result dict
        # But we can use the one-liner that's already there
        results_sql = f"""
        SELECT 
            result_id,
            job_id,
            total_texts,
            positive_count,
            neutral_count,
            negative_count,
            sentiment_index,
            average_confidence,
            details
        FROM `{SENTIMENT_RESULTS_TABLE}`
        WHERE job_id = @job_id
        LIMIT 1
        """
        
        results = list(_bq.query(results_sql, job_config=job_config).result())
        
        if not results:
            return {
                "job_id": job_id,
                "status": "COMPLETED",
                "message": "Analysis completed but no detailed results available",
                "report_url": status_row.report_url
            }
        
        result = results[0]
        
        # Build summary_text from the data (since it's not stored in DB)
        high_risk_count = 0
        if result.details:
            # Count high-risk from details
            high_risk_count = len([d for d in result.details if d.get('label') == 'NEGATIVE'])
        
        summary_text = f"""Processed {result.total_texts} responses with overall sentiment index of {result.sentiment_index:.2f}.

DISTRIBUTION:
• Positive: {result.positive_count} ({result.positive_count/result.total_texts*100:.1f}%)
• Neutral: {result.neutral_count} ({result.neutral_count/result.total_texts*100:.1f}%)
• Negative: {result.negative_count} ({result.negative_count/result.total_texts*100:.1f}%)

{"⚠️ ATTENTION REQUIRED: Significant negative feedback identified." if result.negative_count > result.positive_count else "✅ POSITIVE OUTLOOK: Majority positive sentiment."}

Download the full Excel report for detailed candidate-level analysis and actionable insights."""
        
        summary = ResultsSummary(
            summary_text=summary_text,
            total_texts=result.total_texts,
            positive_count=result.positive_count,
            neutral_count=result.neutral_count,
            negative_count=result.negative_count,
            sentiment_index=result.sentiment_index,
            average_confidence=result.average_confidence
        )
        
        sentiment_breakdown = {
            "positive": {
                "count": result.positive_count,
                "percentage": round(result.positive_count / result.total_texts * 100, 1) if result.total_texts > 0 else 0
            },
            "neutral": {
                "count": result.neutral_count,
                "percentage": round(result.neutral_count / result.total_texts * 100, 1) if result.total_texts > 0 else 0
            },
            "negative": {
                "count": result.negative_count,
                "percentage": round(result.negative_count / result.total_texts * 100, 1) if result.total_texts > 0 else 0
            }
        }
        
        # Extract key themes from details
        key_themes = []
        if result.details:
            question_counts = {}
            for detail in result.details:
                if detail.get('question_text'):
                    q_text = detail['question_text']
                    question_counts[q_text] = question_counts.get(q_text, 0) + 1
            
            sorted_questions = sorted(question_counts.items(), key=lambda x: x[1], reverse=True)
            key_themes = [q[0] for q in sorted_questions[:3]]
        
        return ResultsResponse(
            job_id=job_id,
            summary=summary,
            sentiment_breakdown=sentiment_breakdown,
            key_themes=key_themes if key_themes else None,
            report_url=status_row.report_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 4: GET /agents/sentiment/jobs
# ============================================================================

@router.get("/jobs", response_model=JobsResponse)
async def list_sentiment_jobs(
    user_email: Optional[str] = None,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10
):
    """List sentiment analysis jobs"""
    
    try:
        where_clauses = []
        query_params = []
        
        if user_email:
            where_clauses.append("user_email = @user_email")
            query_params.append(bigquery.ScalarQueryParameter("user_email", "STRING", user_email))
        
        if organization_id:
            where_clauses.append("organization_id = @organization_id")
            query_params.append(bigquery.ScalarQueryParameter("organization_id", "STRING", organization_id))
        
        if status:
            where_clauses.append("status = @status")
            query_params.append(bigquery.ScalarQueryParameter("status", "STRING", status))
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        sql = f"""
        SELECT job_id, status, created_at, organization_id
        FROM `{SENTIMENT_JOBS_TABLE}`
        {where_sql}
        ORDER BY created_at DESC
        LIMIT @limit
        """
        
        query_params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        
        results = list(_bq.query(sql, job_config=job_config).result())
        
        jobs = [
            JobListItem(
                job_id=row.job_id,
                status=row.status,
                created_at=row.created_at.isoformat() if row.created_at else "",
                organization_id=row.organization_id
            )
            for row in results
        ]
        
        return JobsResponse(total=len(jobs), jobs=jobs)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))