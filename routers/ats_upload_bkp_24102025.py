# routers/ats_upload.py
"""
ATS Checker Router - Unified Pattern
Endpoints follow the standard agent pattern:
  POST   /agents/ats/submit
  GET    /agents/ats/status/{job_id}
  GET    /agents/ats/results/{job_id}
  GET    /agents/ats/jobs
"""

import uuid
import json
from datetime import datetime
from typing import List, Optional
from io import BytesIO

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import bigquery
import config

# Import ATS processing (will run in background/async in production)
from worker.ats_processing import batch_analyze_candidates

router = APIRouter()

# BigQuery client
_bq = bigquery.Client(project=config.PROJECT_ID)

# Table references
DATASET_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}"
ATS_JOBS_TABLE = f"{DATASET_ID}.ats_jobs"
ATS_RESULTS_TABLE = f"{DATASET_ID}.ats_results"


# ==============================================================================
# ENDPOINT 1: Submit ATS Analysis Job
# ==============================================================================

@router.post("/submit")
async def submit_ats_job(
    jd_file: UploadFile = File(..., description="Job Description (PDF/DOCX/TXT)"),
    cv_files: List[UploadFile] = File(..., description="Candidate CVs (PDF/DOCX)"),
    position_title: str = Form(..., description="Position title"),
    organization: str = Form(default="", description="Organization name"),
    user_email: str = Form(default="guest@example.com", description="User email"),
    detect_ai: bool = Form(default=True, description="Enable AI detection"),
    save_to_bigquery: bool = Form(default=True, description="Save results to BigQuery")
):
    """
    Submit a new ATS analysis job
    
    **Request:**
    - jd_file: Job description file
    - cv_files: Multiple CV files (up to 20)
    - position_title: Job title
    - organization: Company name
    - user_email: User email
    - detect_ai: Enable AI-generated content detection
    - save_to_bigquery: Save results to database
    
    **Response:**
    ```json
    {
        "job_id": "abc-123-def",
        "status": "PROCESSING",
        "message": "Analysis started",
        "total_candidates": 5,
        "check_status_at": "/agents/ats/status/abc-123-def",
        "estimated_time_minutes": 3
    }
    ```
    """
    
    try:
        # Validation
        if not cv_files or len(cv_files) == 0:
            raise HTTPException(status_code=400, detail="At least one CV file is required")
        
        if len(cv_files) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 CV files allowed")
        
        # Validate file types
        allowed_extensions = ('.pdf', '.docx', '.doc', '.txt')
        if not jd_file.filename.lower().endswith(allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"JD file must be {', '.join(allowed_extensions)}"
            )
        
        for cv in cv_files:
            if not cv.filename.lower().endswith(allowed_extensions):
                raise HTTPException(
                    status_code=400,
                    detail=f"All CV files must be {', '.join(allowed_extensions)}"
                )
        
        # Count candidates
        total_candidates = len(cv_files)
        
        print(f"\n{'='*80}")
        print(f"📊 NEW ATS JOB SUBMITTED")
        print(f"   Position: {position_title}")
        print(f"   Organization: {organization}")
        print(f"   User: {user_email}")
        print(f"   Candidates: {total_candidates}")
        print(f"   Save to BQ: {save_to_bigquery}")
        print(f"{'='*80}\n")
        
        # Read JD file
        jd_bytes = await jd_file.read()
        jd_text = get_text_from_file(BytesIO(jd_bytes), jd_file.filename)
        
        # Read CV files
        cv_files_data = []
        for cv in cv_files:
            cv_bytes = await cv.read()
            cv_files_data.append((cv_bytes, cv.filename))
        
        # Run analysis (synchronous for now - would be async/queue in production)
        # ✅ FIX: Use the job_id returned by batch_analyze_candidates, don't generate our own!
        job_id, results = batch_analyze_candidates(
            cv_files_data=cv_files_data,
            jd_text=jd_text,
            position_title=position_title,
            organization=organization,
            user_email=user_email,
            detect_ai=detect_ai,
            save_to_bigquery=save_to_bigquery,
            verbose=True
        )
        
        print(f"✅ Analysis completed! Job ID: {job_id}")
        
        # Initialize variables
        report_url = None
        gcs_path = None
        
        # Generate Excel report and upload to GCS
        excel_filename = f"ATS_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Generate Excel in memory first
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as tmp_file:
            excel_path = tmp_file.name
        
        try:
            from worker.ats_processing import export_analysis_to_excel
            from google.cloud import storage
            
            jd_requirements = results[0].get('_jd_requirements', {}) if results else {}
            position_title_from_results = results[0].get('_position_title', position_title) if results else position_title
            
            # Generate Excel file
            export_analysis_to_excel(
                results=results,
                output_file=excel_path,
                jd_requirements=jd_requirements,
                position_title=position_title_from_results
            )
            
            print(f"✅ Excel report generated: {excel_path}")
            
            # Upload to GCS
            storage_client = storage.Client(project=config.PROJECT_ID)
            bucket_name = config.GCS_BUCKET
            
            # Create folder structure: ats-reports/{user_email}/{job_id}/
            blob_path = f"ats-reports/{user_email.replace('@', '_at_').replace('.', '_')}/{job_id}/{excel_filename}"
            
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            # Upload file
            blob.upload_from_filename(excel_path)
            
            # Generate signed URL (valid for 7 days)
            from datetime import timedelta
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=7),
                method="GET"
            )
            
            print(f"✅ Excel uploaded to GCS: gs://{bucket_name}/{blob_path}")
            print(f"✅ Signed URL generated (valid 7 days)")
            
            report_url = signed_url
            gcs_path = f"gs://{bucket_name}/{blob_path}"
            
            # Clean up temp file
            import os
            os.unlink(excel_path)
            
            # Update BigQuery with report URL
            if save_to_bigquery:
                try:
                    from google.cloud import bigquery
                    bq_client = bigquery.Client(project=config.PROJECT_ID)
                    
                    update_query = f"""
                    UPDATE `{config.PROJECT_ID}.{config.BQ_DATASET}.ats_jobs`
                    SET report_url = @report_url,
                        updated_at = CURRENT_TIMESTAMP()
                    WHERE job_id = @job_id
                    """
                    
                    job_config = bigquery.QueryJobConfig(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("report_url", "STRING", gcs_path),
                            bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
                        ]
                    )
                    
                    bq_client.query(update_query, job_config=job_config).result()
                    print(f"✅ Updated BigQuery with report URL")
                except Exception as bq_error:
                    print(f"⚠️ Failed to update BigQuery with report URL: {bq_error}")
            
        except Exception as e:
            print(f"⚠️ Failed to generate/upload Excel: {e}")
            import traceback
            traceback.print_exc()
            report_url = None
            gcs_path = None
        
        # Estimate time (rough: 20-40 seconds per candidate)
        estimated_minutes = max(1, (total_candidates * 30) // 60)
        
        return {
            "job_id": job_id,  # ✅ Now uses the CORRECT job_id from processing
            "status": "COMPLETED",  # Since we run synchronously
            "message": "Analysis completed successfully",
            "total_candidates": total_candidates,
            "analyzed_candidates": len(results),
            "report_url": report_url,  # ✅ GCS signed URL (valid 7 days)
            "gcs_path": gcs_path,  # ✅ GCS path for reference
            "check_status_at": f"/agents/ats/status/{job_id}",
            "get_results_at": f"/agents/ats/results/{job_id}",
            "estimated_time_minutes": estimated_minutes,
            "report_expires_in": "7 days" if report_url else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in submit_ats_job: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")


# ==============================================================================
# ENDPOINT 2: Get Job Status
# ==============================================================================

@router.get("/status/{job_id}")
async def get_ats_job_status(job_id: str):
    """
    Get the status of an ATS analysis job
    
    **Response:**
    ```json
    {
        "job_id": "abc-123-def",
        "status": "COMPLETED",
        "created_at": "2025-10-23T10:30:00",
        "updated_at": "2025-10-23T10:35:00",
        "completed_at": "2025-10-23T10:35:00",
        "total_candidates_analyzed": 5,
        "position_title": "Data Scientist - B2",
        "error_message": null
    }
    ```
    
    **Status values:**
    - RUNNING: Analysis in progress
    - COMPLETED: Analysis finished successfully
    - FAILED: Analysis failed (check error_message)
    """
    
    try:
        # Query ats_jobs table for latest status
        query = f"""
        SELECT 
            job_id,
            position_title,
            organization,
            user_email,
            total_candidates_analyzed,
            status,
            created_at,
            updated_at,
            completed_at,
            error_message,
            report_url
        FROM `{ATS_JOBS_TABLE}`
        WHERE job_id = @job_id
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
            ]
        )
        
        results = list(_bq.query(query, job_config=job_config).result())
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        row = results[0]
        
        return {
            "job_id": row.job_id,
            "status": row.status,
            "position_title": row.position_title,
            "organization": row.organization,
            "user_email": row.user_email,
            "total_candidates_analyzed": row.total_candidates_analyzed,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "error_message": row.error_message,
            "report_url": row.report_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_ats_job_status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


# ==============================================================================
# ENDPOINT 3: Get Job Results
# ==============================================================================

@router.get("/results/{job_id}")
async def get_ats_job_results(job_id: str):
    """
    Get the detailed results of a completed ATS analysis
    
    **Response:**
    ```json
    {
        "job_id": "abc-123-def",
        "position_title": "Data Scientist - B2",
        "summary": {
            "total_analyzed": 5,
            "avg_score": 55.1,
            "max_score": 66.1,
            "min_score": 49.4,
            "top_candidates_count": 0,
            "ai_detected_count": 2
        },
        "score_distribution": [66.1, 55.5, 52.9, 50.6, 49.4],
        "skills_coverage": ["python", "sql", "machine learning", ...],
        "missing_skills": ["kubernetes", "docker", ...],
        "report_url": "https://storage.googleapis.com/.../report.xlsx"
    }
    ```
    """
    
    try:
        # First check if job is completed
        status_query = f"""
        SELECT status, completed_at, report_url
        FROM `{ATS_JOBS_TABLE}`
        WHERE job_id = @job_id
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
            ]
        )
        
        status_results = list(_bq.query(status_query, job_config=job_config).result())
        
        if not status_results:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        status_row = status_results[0]
        
        if status_row.status != "COMPLETED":
            return {
                "job_id": job_id,
                "status": status_row.status,
                "message": f"Job is {status_row.status}. Results not yet available."
            }
        
        # Get detailed results from ats_results table
        results_query = f"""
        SELECT 
            result_id,
            job_id,
            resume_pool_size,
            top_n_selected,
            avg_score,
            max_score,
            min_score,
            score_distribution,
            skills_coverage,
            missing_skills,
            meta,
            created_at
        FROM `{ATS_RESULTS_TABLE}`
        WHERE job_id = @job_id
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        results_data = list(_bq.query(results_query, job_config=job_config).result())
        
        if not results_data:
            # Job completed but no aggregated results (shouldn't happen, but handle gracefully)
            return {
                "job_id": job_id,
                "status": "COMPLETED",
                "message": "Analysis completed but no detailed results available",
                "report_url": status_row.report_url
            }
        
        result = results_data[0]
        meta = json.loads(result.meta) if result.meta else {}
        
        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "result_id": result.result_id,
            "position_title": meta.get("position_title", ""),
            "summary": {
                "total_analyzed": result.resume_pool_size,
                "avg_score": round(result.avg_score, 1),
                "max_score": round(result.max_score, 1),
                "min_score": round(result.min_score, 1),
                "top_candidates_count": result.top_n_selected,
                "high_match_count": meta.get("high_match_count", 0),
                "medium_match_count": meta.get("medium_match_count", 0),
                "low_match_count": meta.get("low_match_count", 0),
                "ai_detected_count": meta.get("ai_detected_count", 0),
                "avg_skills_match": round(meta.get("avg_skills_match", 0), 1),
                "avg_experience": round(meta.get("avg_experience", 0), 1)
            },
            "score_distribution": result.score_distribution,
            "skills_coverage": result.skills_coverage[:20],  # Top 20
            "missing_skills": result.missing_skills[:20],  # Top 20
            "report_url": status_row.report_url,
            "created_at": result.created_at.isoformat() if result.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_ats_job_results: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


# ==============================================================================
# ENDPOINT 4: List User's Jobs
# ==============================================================================

@router.get("/jobs")
async def list_ats_jobs(
    user_email: Optional[str] = None,
    organization: Optional[str] = None,
    limit: int = 10
):
    """
    List ATS analysis jobs for a user or organization
    
    **Query Parameters:**
    - user_email: Filter by user email
    - organization: Filter by organization
    - limit: Maximum number of jobs to return (default: 10)
    
    **Response:**
    ```json
    {
        "jobs": [
            {
                "job_id": "abc-123",
                "position_title": "Data Scientist",
                "status": "COMPLETED",
                "created_at": "2025-10-23T10:30:00",
                "total_candidates": 5
            },
            ...
        ],
        "total": 2
    }
    ```
    """
    
    try:
        # Build query with optional filters
        where_clauses = []
        query_params = []
        
        if user_email:
            where_clauses.append("user_email = @user_email")
            query_params.append(bigquery.ScalarQueryParameter("user_email", "STRING", user_email))
        
        if organization:
            where_clauses.append("organization = @organization")
            query_params.append(bigquery.ScalarQueryParameter("organization", "STRING", organization))
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = f"""
        SELECT 
            job_id,
            position_title,
            organization,
            user_email,
            total_candidates_analyzed,
            status,
            created_at,
            completed_at
        FROM `{ATS_JOBS_TABLE}`
        {where_sql}
        ORDER BY created_at DESC
        LIMIT @limit
        """
        
        query_params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        results = list(_bq.query(query, job_config=job_config).result())
        
        jobs = []
        for row in results:
            jobs.append({
                "job_id": row.job_id,
                "position_title": row.position_title,
                "organization": row.organization,
                "user_email": row.user_email,
                "total_candidates_analyzed": row.total_candidates_analyzed,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None
            })
        
        return {
            "jobs": jobs,
            "total": len(jobs),
            "filters": {
                "user_email": user_email,
                "organization": organization,
                "limit": limit
            }
        }
        
    except Exception as e:
        print(f"❌ Error in list_ats_jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


# ==============================================================================
# Helper: Import file_utils function
# ==============================================================================

def get_text_from_file(file_io, filename):
    """Extract text from file - wrapper for file_utils"""
    from utils.file_utils import get_text_from_file as extract_text
    from pathlib import Path
    return extract_text(file_io, Path(filename).suffix)