# routers/ats_upload.py
"""
ATS Checker Router - Unified Pattern
Endpoints follow the standard agent pattern:
  POST   /agents/ats/submit
  GET    /agents/ats/status/{job_id}
  GET    /agents/ats/results/{job_id}
  GET    /agents/ats/jobs
  GET    /agents/ats/query
"""

import uuid
import json
from datetime import datetime
from typing import List, Optional,Dict
from io import BytesIO
from collections import Counter
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import bigquery
import config
from schemas.ats_models import AtsQueryRequest, AtsQueryResponse
import utils.vertex_ai_utils as vertex_ai_utils

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
    job_description: UploadFile = File(..., description="Job Description (PDF/DOCX/TXT)"),
    resumes: List[UploadFile] = File(..., description="Candidate CVs (PDF/DOCX)"),
    position_title: str = Form(default="", description="Position title (auto-extracted if not provided)"),
    organization: str = Form(default="", description="Organization name"),
    user_email: str = Form(default="guest@example.com", description="User email"),
    detect_ai: bool = Form(default=True, description="Enable AI detection"),
    save_to_bigquery: bool = Form(default=True, description="Save results to BigQuery"),
    results_filter: str = Form(default="all", description="Results filter: 'all' or 'top'"),
    top_count: int = Form(default=5, description="Number of top candidates if filter is 'top'")
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
        if not resumes or len(resumes) == 0:
            raise HTTPException(status_code=400, detail="At least one CV file is required")
        
        if len(resumes) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 CV files allowed")
        
        # Validate file types
        allowed_extensions = ('.pdf', '.docx', '.doc', '.txt')
        if not job_description.filename.lower().endswith(allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"JD file must be {', '.join(allowed_extensions)}"
            )
        
        for cv in resumes:
            if not cv.filename.lower().endswith(allowed_extensions):
                raise HTTPException(
                    status_code=400,
                    detail=f"All CV files must be {', '.join(allowed_extensions)}"
                )
        
        # Count candidates
        total_candidates = len(resumes)
        
        # Read JD file first to extract position if needed
        jd_bytes = await job_description.read()
        jd_text = get_text_from_file(BytesIO(jd_bytes), job_description.filename)
        
        # Auto-extract position title if not provided
        if not position_title or position_title.strip() == "":
            print("⚠️ Position title not provided, extracting from JD...")
            try:
                from worker.ats_processing import extract_position_from_jd
                position_title = extract_position_from_jd(jd_text)
                print(f"✅ Extracted position: {position_title}")
            except Exception as e:
                print(f"⚠️ Could not extract position title: {e}")
                position_title = "Position Not Specified"
        
        print(f"\n{'='*80}")
        print(f"📊 NEW ATS JOB SUBMITTED")
        print(f"   Position: {position_title}")
        print(f"   Organization: {organization}")
        print(f"   User: {user_email}")
        print(f"   Candidates: {total_candidates}")
        print(f"   Save to BQ: {save_to_bigquery}")
        print(f"{'='*80}\n")
        
        # Read CV files
        cv_files_data = []
        for cv in resumes:
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
            
            # Upload to GCS using service account (for URL signing)
            from google.oauth2 import service_account
            from datetime import timedelta
            
            signing_credentials = service_account.Credentials.from_service_account_file(
                config.SA_KEY_PATH
            )
            
            storage_client = storage.Client(
                project=config.PROJECT_ID,
                credentials=signing_credentials
            )
            bucket_name = config.GCS_BUCKET
            
            # Create folder structure: ats-reports/{user_email}/{job_id}/
            blob_path = f"ats-reports/{user_email.replace('@', '_at_').replace('.', '_')}/{job_id}/{excel_filename}"
            
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            # Upload file
            blob.upload_from_filename(excel_path)
            
            # Generate signed URL (valid for 7 days)
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
            
        except Exception as e:
            print(f"⚠️ Failed to generate/upload Excel: {e}")
            import traceback
            traceback.print_exc()
            report_url = None
            gcs_path = None
        
        # ✅ GENERATE SUMMARY WITH EXCEL LINK (Don't query BigQuery - just use what we have!)
        summary = None
        try:
            from worker.ats_processing import generate_privacy_safe_summary
            
            jd_requirements = results[0].get('_jd_requirements', {}) if results else {}
            
            # Generate the summary directly
            summary = generate_privacy_safe_summary(results, jd_requirements, position_title)
            
            # Append Excel link to summary
            if report_url:
                summary += f"""

📊 DETAILED ANALYSIS REPORT:
For a comprehensive breakdown of all candidates including individual scores, skills matrices, AI detection details, and ranking comparisons, check out our detailed findings in the Excel report:

📥 Download Full Report: {report_url}

This Excel report includes:
• Executive Summary Dashboard
• Detailed Candidate Rankings
• Complete Skills Analysis Matrix
• AI Detection Results
• Experience & Technical Depth Comparisons
• Hiring Recommendations

Note: The download link is valid for 7 days. Please save the report locally for future reference.
"""
            print(f"✅ Summary generated with Excel link")
                
        except Exception as e:
            print(f"⚠️ Could not generate summary: {e}")
            import traceback
            traceback.print_exc()
            summary = f"Analysis completed. Check the Excel report for full details: {report_url if report_url else 'Report generation failed'}"
        
        # ✅ UPDATE: Finalize job with report_url (worker already marked it COMPLETED)
        # This adds a new row with the report_url included
        if report_url:
            try:
                from utils import bigquery_ats_utils as bq_ats
                bq_ats.finalize_ats_job(
                    job_id=job_id,
                    position_title=position_title,
                    organization=organization,
                    user_email=user_email,
                    total_candidates=len(results),
                    status="COMPLETED",
                    report_url=report_url
                )
                print(f"✅ Job finalized with report_url in ats_jobs table")
            except Exception as e:
                print(f"⚠️ Failed to update job with report_url: {e}")
        
        # Estimate time (rough: 20-40 seconds per candidate)
        estimated_minutes = max(1, (total_candidates * 30) // 60)
        
        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "message": "Analysis completed successfully",
            "total_candidates": total_candidates,
            "analyzed_candidates": len(results),
            "report_url": report_url,
            "gcs_path": gcs_path,
            "summary": summary,  # ✅ Full summary with Excel link
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
            summary_text,
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
        
        # ✅ Return clean summary WITHOUT the URL (frontend will render the link separately)
        summary_text = result.summary_text if hasattr(result, "summary_text") and result.summary_text else "Analysis completed."
        
        # Frontend displays summary in conversation and renders report_url as a separate link
        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "result_id": result.result_id,
            "position_title": meta.get("position_title", ""),
            "summary": summary_text,  # ✅ Clean summary text (no URL)
            "report_url": status_row.report_url,  # ✅ Frontend renders this as clickable link
            "stats": {
                # Optional: Basic stats if frontend wants to show them separately
                "total_analyzed": result.resume_pool_size,
                "avg_score": round(result.avg_score, 1),
                "max_score": round(result.max_score, 1),
                "min_score": round(result.min_score, 1),
                "top_candidates_count": result.top_n_selected,
                "ai_detected_count": meta.get("ai_detected_count", 0)
            },
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
# ENDPOINT 5: Query ATS Screening with LLM
# ==============================================================================  


@router.post("/query", response_model=AtsQueryResponse)
async def query_ats_screening(request: AtsQueryRequest):
    """
    Query completed ATS screening using LLM with job summary and results context
    
    **NEW:** Now includes job summary from ats_jobs table for better context!
    
    Example queries:
    - "What are the collective strengths of all candidates?"
    - "What are the main gaps in skills across all applicants?"
    - "How many candidates were flagged for AI-generated content?"
    - "What is the average skill match percentage?"
    - "When was this analysis completed?"
    - "What position was this analysis for?"
    
    **Date Filtering:**
    - If you have multiple analyses for the same position, use `analysis_date` parameter
    - Format: YYYY-MM-DD (e.g., "2025-10-27")
    """
    
    try:
        # ============================================================
        # STEP 1: Fetch Job Metadata from ats_jobs table
        # ============================================================
        
        job_query = f"""
        SELECT 
            job_id,
            position_title,
            organization,
            user_email,
            total_candidates_analyzed,
            status,
            created_at,
            completed_at,
            report_url
        FROM `{ATS_JOBS_TABLE}`
        WHERE job_id = @job_id
        ORDER BY created_at DESC
        LIMIT 2
        """
        print("The query is:",job_query)
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("job_id", "STRING", request.job_id)
            ]
        )
        
        job_results = list(_bq.query(job_query, job_config=job_config).result())
        
        if not job_results:
            raise HTTPException(404, f"Job ID '{request.job_id}' not found")
        
        job_row = job_results[0]
        
        # Validate job belongs to user
        if job_row.user_email != request.user_email:
            raise HTTPException(403, "You don't have access to this job")
        
        if job_row.status != "COMPLETED":
            raise HTTPException(
                400, 
                f"Job not completed yet. Current status: {job_row.status}. Please wait for analysis to finish."
            )
        
        # Extract job summary
        job_summary = {
            "job_id": job_row.job_id,
            "position_title": job_row.position_title,
            "organization": job_row.organization,
            "total_candidates_analyzed": job_row.total_candidates_analyzed,
            "status": job_row.status,
            "created_at": job_row.created_at.isoformat() if job_row.created_at else None,
            "completed_at": job_row.completed_at.isoformat() if job_row.completed_at else None,
            "report_url": job_row.report_url,
            "summary_text": job_row.summary if hasattr(job_row, 'summary') else None
        }
        
        print(f"✅ Job metadata fetched: {job_row.position_title} - {job_row.total_candidates_analyzed} candidates")
        
        # ============================================================
        # STEP 2: Fetch Candidate Results from ats_results table
        # ============================================================
        
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
            summary_text,
            details,
            meta,
            created_at
        FROM `{ATS_RESULTS_TABLE}`
        WHERE job_id = @job_id
        """

        # Add date filter if provided
        query_params = [bigquery.ScalarQueryParameter("job_id", "STRING", request.job_id)]

        if request.analysis_date:
            results_query += " AND DATE(created_at) = @analysis_date"
            query_params.append(
                bigquery.ScalarQueryParameter("analysis_date", "DATE", request.analysis_date)
            )

        results_query += " ORDER BY created_at DESC LIMIT 1"  # ✅ Get latest result

        results_config = bigquery.QueryJobConfig(query_parameters=query_params)
        results = list(_bq.query(results_query, job_config=results_config).result())

        # Since it's aggregated, we only have ONE result row
        if not results:
            raise HTTPException(404, f"No results found for job '{request.job_id}'")

        aggregated_result = results[0]  # Only one row
        
        if not results:
            if request.analysis_date:
                raise HTTPException(
                    404, 
                    f"No results found for job '{request.job_id}' on date {request.analysis_date}. "
                    f"Try without date filter or check available dates."
                )
            else:
                raise HTTPException(404, f"No results found for job '{request.job_id}'")
        
        print(f"✅ Found {len(results)} candidate results")
        
        # ============================================================
        # STEP 3: Build Enhanced Context (Job Summary + Results)
        # ============================================================
        
        context = build_enhanced_ats_context(
            job_summary=job_summary,
            results=results,
            analysis_date=request.analysis_date
        )
        
        # ============================================================
        # STEP 4: Build Prompt for Gemini
        # ============================================================
        
        prompt = f"""You are an expert technical recruiter analyzing ATS screening results.

Your role is to help make data-driven hiring decisions based on candidate screening data.

IMPORTANT CONTEXT:
- You have access to BOTH aggregated statistics AND individual candidate details
- Individual candidate names, scores, and backgrounds are provided in the context below
- You can answer questions about specific candidates by name
- The user has access to a detailed Excel report for additional information
- Answer questions about the job, timeline, aggregated metrics, and individual candidates

JOB & ANALYSIS CONTEXT:
{context}

USER QUESTION:
{request.query}

INSTRUCTIONS:
1. Use both job summary, aggregated metrics, AND individual candidate details to answer
2. If asked about specific candidates by name, provide detailed information from the candidate details section
3. If asked about the job/position/organization/timeline, use the job summary
4. If asked about overall trends/patterns, use the aggregated metrics
5. Give collective insights about the candidate pool as a whole when appropriate
6. Highlight overall strengths and common gaps across all candidates
7. Provide actionable recommendations for next steps in hiring
8. When discussing specific candidates, use their names and provide detailed scores
9. If asked about when the analysis was done, use the created_at/completed_at timestamps
10. If the data does not support a definitive answer, state that clearly
11. For questions requiring more detail than available, direct users to the Excel report

ANSWER:"""
        
        # ============================================================
        # STEP 5: Call Gemini
        # ============================================================
        
        answer = vertex_ai_utils.generate_freeform(prompt)
        
        # ============================================================
        # STEP 6: Extract Aggregated Supporting Data
        # ============================================================
        
        supporting_data = extract_aggregated_metrics(results)
        
        # ============================================================
        # STEP 7: Return Enhanced Response
        # ============================================================
        
        return AtsQueryResponse(
            job_id=request.job_id,
            query=request.query,
            answer=answer,
            job_summary=job_summary,  # ✅ NEW: Include job metadata
            supporting_data=supporting_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error querying ATS: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to query ATS screening: {str(e)}")


# ============================================================
# HELPER: Build Enhanced Context with Job Summary
# ============================================================

def build_enhanced_ats_context(
    job_summary: Dict,
    results: List,
    analysis_date: Optional[str] = None
) -> str:
    """
    Build context from AGGREGATED ATS results for AI query answering
    
    ✅ FIXED: Works with aggregated data (not individual candidates)
    ✅ FIXED: Fields are already parsed (not JSON strings)
    
    Args:
        job_summary: Job metadata dict
        results: List with ONE aggregated result row from ats_results table
        analysis_date: Optional date filter
    
    Returns:
        Formatted context string for AI
    """
    
    if not results or len(results) == 0:
        return "No ATS results available for this job."
    
    # Get the single aggregated result
    agg_result = results[0]
    
    # ✅ FIX: These fields are ALREADY parsed Python objects (list/dict), not JSON strings!
    # BigQuery automatically parses JSON columns
    score_dist = agg_result.score_distribution if agg_result.score_distribution else {}
    skills_coverage = agg_result.skills_coverage if agg_result.skills_coverage else []
    missing_skills = agg_result.missing_skills if agg_result.missing_skills else []
    meta = agg_result.meta if agg_result.meta else {}
    
    # Extract values with defaults
    resume_pool_size = agg_result.resume_pool_size or 0
    top_n_selected = agg_result.top_n_selected or 0
    avg_score = agg_result.avg_score or 0
    max_score = agg_result.max_score or 0
    min_score = agg_result.min_score or 0
    
    # ============================================================
    # BUILD CONTEXT STRING WITH JOB SUMMARY FIRST
    # ============================================================
    
    context = f"""
    JOB SUMMARY:
    Position: {job_summary['position_title']}
    Organization: {job_summary['organization']}
    Total Candidates Screened: {job_summary['total_candidates_analyzed']}
    Analysis Completed: {job_summary.get('completed_at', 'N/A')}
    """
    
    if analysis_date:
        context += f"\nAnalysis Date Filter: {analysis_date}"
    
    context += f"""
    
    SCREENING STATISTICS:
    - Total CVs Analyzed: {resume_pool_size}
    - Top Candidates Selected: {top_n_selected}
    - Average Score: {avg_score:.1f}/100
    - Highest Score: {max_score:.1f}/100
    - Lowest Score: {min_score:.1f}/100
    """
    
    # ============================================================
    # SCORE DISTRIBUTION
    # ============================================================
    
    context += "\n\nSCORE DISTRIBUTION:\n"
    
    if score_dist and isinstance(score_dist, dict):
        excellent = score_dist.get('excellent', 0)
        good = score_dist.get('good', 0)
        average = score_dist.get('average', 0)
        below_avg = score_dist.get('below_average', 0)
        
        if resume_pool_size > 0:
            context += f"- Excellent (80-100): {excellent} candidates ({excellent/resume_pool_size*100:.1f}%)\n"
            context += f"- Good (60-79): {good} candidates ({good/resume_pool_size*100:.1f}%)\n"
            context += f"- Average (40-59): {average} candidates ({average/resume_pool_size*100:.1f}%)\n"
            context += f"- Below Average (<40): {below_avg} candidates ({below_avg/resume_pool_size*100:.1f}%)\n"
        else:
            context += "- Score distribution data not available\n"
    else:
        context += "- Score distribution data not available\n"
    
    # ============================================================
    # SKILLS ANALYSIS
    # ============================================================
    
    context += "\n\nSKILLS ANALYSIS:\n"
    
    if skills_coverage and isinstance(skills_coverage, list):
        context += f"Top Skills Found Across Candidates: {', '.join(str(s) for s in skills_coverage[:15])}\n"
    else:
        context += "Skills coverage data not available\n"
    
    if missing_skills and isinstance(missing_skills, list):
        context += f"Commonly Missing Skills: {', '.join(str(s) for s in missing_skills[:10])}\n"
    else:
        context += "No significant skill gaps identified\n"
    
    # ============================================================
    # OVERALL SUMMARY
    # ============================================================
    
    if agg_result.summary_text:
        context += f"\n\nOVERALL SUMMARY:\n{agg_result.summary_text}\n"
    
    # ============================================================
    # CANDIDATE-LEVEL DETAILS (like sentiment's "doc mode")
    # ============================================================
    
    candidate_details = agg_result.details if hasattr(agg_result, 'details') and agg_result.details else []
    
    if candidate_details and len(candidate_details) > 0:
        context += f"\n\nINDIVIDUAL CANDIDATE DETAILS:\n"
        context += f"Total Candidates Analyzed: {len(candidate_details)}\n\n"
        
        # Show top 10 candidates with full details
        for detail in candidate_details[:10]:
            candidate_name = detail.get('candidate_name', 'Unknown')
            rank = detail.get('rank', 0)
            overall_score = detail.get('overall_score', 0)
            skills_match = detail.get('skills_match_score', 0)
            exp_match = detail.get('experience_match_score', 0)
            tech_depth = detail.get('technical_depth_score', 0)
            domain_match = detail.get('domain_match_score', 0)
            experience_years = detail.get('total_experience_years', 0)
            current_company = detail.get('current_company', 'N/A')
            current_role = detail.get('current_role', 'N/A')
            matched_skills = detail.get('matched_skills', [])
            missing_skills = detail.get('missing_skills', [])
            match_reason = detail.get('match_reason', '')
            ai_probability = detail.get('ai_probability', 0)
            ai_warning = detail.get('ai_warning_level', 'low')
            
            context += f"Rank #{rank}: {candidate_name}\n"
            context += f"  Overall Match Score: {overall_score:.1f}%\n"
            context += f"  Component Scores:\n"
            context += f"    - Skills Match: {skills_match:.1f}%\n"
            context += f"    - Experience Match: {exp_match:.1f}%\n"
            context += f"    - Technical Depth: {tech_depth:.1f}%\n"
            context += f"    - Domain Match: {domain_match:.1f}%\n"
            context += f"  Background:\n"
            context += f"    - Current Role: {current_role} at {current_company}\n"
            context += f"    - Total Experience: {experience_years} years\n"
            if matched_skills:
                context += f"  Matched Skills ({len(matched_skills)}): {', '.join(matched_skills[:10])}\n"
            if missing_skills:
                context += f"  Missing Skills ({len(missing_skills)}): {', '.join(missing_skills[:5])}\n"
            context += f"  Assessment: {match_reason}\n"
            if ai_probability > 50:
                context += f"  ⚠️ AI Detection: {ai_probability:.0f}% probability ({ai_warning} risk)\n"
            context += "\n"
    
    # ============================================================
    # ADDITIONAL METADATA
    # ============================================================
    
    if meta and isinstance(meta, dict):
        context += "\n\nADDITIONAL DETAILS:\n"
        if 'ai_detection_enabled' in meta:
            context += f"- AI Detection: {'Enabled' if meta['ai_detection_enabled'] else 'Disabled'}\n"
        if 'processing_time_seconds' in meta:
            context += f"- Processing Time: {meta['processing_time_seconds']} seconds\n"
        if 'jd_filename' in meta:
            context += f"- Job Description: {meta['jd_filename']}\n"
    
    context += """
    
    IMPORTANT NOTES:
    - Individual candidate names and details are provided above for specific questions
    - You can answer questions about specific candidates by name
    - Full detailed Excel report is also available for download
    - Scores are based on skills match, experience match, technical depth, and domain relevance
    - The analysis considers job requirements, candidate qualifications, and market standards
    """
    
    return context

# def extract_aggregated_metrics(results: List) -> dict:
#     """
#     Extract aggregated metrics from ATS results
#     NO individual candidate data - only summary statistics
    
#     Args:
#         results: List of BigQuery Row objects from ats_results table
    
#     Returns:
#         dict: Aggregated metrics including:
#             - total_candidates
#             - average_scores
#             - ai_detection stats
#             - recommendations distribution
#             - skills_analysis
#             - score_distribution
#     """
    
#     # Handle empty results
#     if not results or len(results) == 0:
#         return {
#             "total_candidates": 0,
#             "average_scores": {},
#             "ai_detection": {},
#             "recommendations": {},
#             "skills_analysis": {},
#             "score_distribution": {}
#         }
    
#     total_candidates = len(results)
    
#     # ============================================================
#     # 1. Calculate Average Scores
#     # ============================================================
    
#     avg_overall_score = sum(r.overall_score for r in results) / total_candidates if total_candidates > 0 else 0
#     avg_skills_match = sum(r.skills_match for r in results) / total_candidates if total_candidates > 0 else 0
#     avg_experience_match = sum(r.experience_match for r in results) / total_candidates if total_candidates > 0 else 0
#     avg_technical_depth = sum(r.technical_depth for r in results) / total_candidates if total_candidates > 0 else 0
    
#     # ============================================================
#     # 2. AI Detection Statistics
#     # ============================================================
    
#     ai_flagged_count = sum(1 for r in results if r.is_likely_ai_generated)
#     authentic_count = total_candidates - ai_flagged_count
    
#     # ============================================================
#     # 3. Recommendation Distribution
#     # ============================================================
    
#     strong_fit_count = sum(1 for r in results if r.recommendation == "STRONG_FIT")
#     good_fit_count = sum(1 for r in results if r.recommendation == "GOOD_FIT")
#     moderate_fit_count = sum(1 for r in results if r.recommendation == "MODERATE_FIT")
#     weak_fit_count = sum(1 for r in results if r.recommendation == "WEAK_FIT")
#     poor_fit_count = sum(1 for r in results if r.recommendation == "POOR_FIT")
    
#     # ============================================================
#     # 4. Skills Analysis - Aggregate All Skills
#     # ============================================================
    
#     all_matched_skills = []
#     all_missing_skills = []
    
#     for r in results:
#         # Matched skills
#         if hasattr(r, 'matched_skills') and r.matched_skills:
#             if isinstance(r.matched_skills, list):
#                 all_matched_skills.extend(r.matched_skills)
#             elif isinstance(r.matched_skills, str):
#                 # If stored as JSON string, parse it
#                 try:
#                     import json
#                     parsed = json.loads(r.matched_skills)
#                     if isinstance(parsed, list):
#                         all_matched_skills.extend(parsed)
#                 except:
#                     pass
        
#         # Missing skills
#         if hasattr(r, 'missing_skills') and r.missing_skills:
#             if isinstance(r.missing_skills, list):
#                 all_missing_skills.extend(r.missing_skills)
#             elif isinstance(r.missing_skills, str):
#                 try:
#                     import json
#                     parsed = json.loads(r.missing_skills)
#                     if isinstance(parsed, list):
#                         all_missing_skills.extend(parsed)
#                 except:
#                     pass
    
#     # Count skill frequencies
#     matched_skills_counter = Counter(all_matched_skills)
#     missing_skills_counter = Counter(all_missing_skills)
    
#     # Get top 10 skills with counts and percentages
#     top_matched_skills = [
#         {
#             "skill": skill, 
#             "count": count, 
#             "percentage": round(count / total_candidates * 100, 1)
#         } 
#         for skill, count in matched_skills_counter.most_common(10)
#     ]
    
#     top_missing_skills = [
#         {
#             "skill": skill, 
#             "count": count, 
#             "percentage": round(count / total_candidates * 100, 1)
#         } 
#         for skill, count in missing_skills_counter.most_common(10)
#     ]
    
#     # ============================================================
#     # 5. Score Distribution by Quartiles
#     # ============================================================
    
#     top_quartile = sum(1 for r in results if r.overall_score >= 75)
#     second_quartile = sum(1 for r in results if 50 <= r.overall_score < 75)
#     third_quartile = sum(1 for r in results if 25 <= r.overall_score < 50)
#     bottom_quartile = sum(1 for r in results if r.overall_score < 25)
    
#     # ============================================================
#     # 6. Build and Return Aggregated Metrics Dictionary
#     # ============================================================
    
#     return {
#         "total_candidates": total_candidates,
        
#         "average_scores": {
#             "overall": round(avg_overall_score, 1),
#             "skills_match": round(avg_skills_match, 1),
#             "experience_match": round(avg_experience_match, 1),
#             "technical_depth": round(avg_technical_depth, 1)
#         },
        
#         "ai_detection": {
#             "flagged_count": ai_flagged_count,
#             "flagged_percentage": round((ai_flagged_count / total_candidates * 100), 1) if total_candidates > 0 else 0,
#             "authentic_count": authentic_count,
#             "authentic_percentage": round((authentic_count / total_candidates * 100), 1) if total_candidates > 0 else 0
#         },
        
#         "recommendations": {
#             "strong_fit": strong_fit_count,
#             "good_fit": good_fit_count,
#             "moderate_fit": moderate_fit_count,
#             "weak_fit": weak_fit_count,
#             "poor_fit": poor_fit_count,
#             "strong_fit_percentage": round((strong_fit_count / total_candidates * 100), 1) if total_candidates > 0 else 0,
#             "good_fit_percentage": round((good_fit_count / total_candidates * 100), 1) if total_candidates > 0 else 0
#         },
        
#         "skills_analysis": {
#             "top_matched_skills": top_matched_skills,
#             "top_missing_skills": top_missing_skills,
#             "total_unique_matched_skills": len(matched_skills_counter),
#             "total_unique_missing_skills": len(missing_skills_counter)
#         },
        
#         "score_distribution": {
#             "top_quartile": top_quartile,
#             "second_quartile": second_quartile,
#             "third_quartile": third_quartile,
#             "bottom_quartile": bottom_quartile,
#             "top_quartile_percentage": round((top_quartile / total_candidates * 100), 1) if total_candidates > 0 else 0
#         }
#     }

def extract_aggregated_metrics(results: List) -> dict:
    """
    Extract aggregated metrics from ATS results
    
    ✅ FIXED: Works with aggregated data (not individual candidates)
    
    Args:
        results: List with ONE aggregated result row from ats_results table
    
    Returns:
        dict: Supporting data for query response
    """
    
    if not results or len(results) == 0:
        return {
            "total_candidates": 0,
            "average_score": 0,
            "score_distribution": {},
            "skills_found": [],
            "skills_missing": []
        }
    
    # Get the single aggregated result
    agg_result = results[0]
    
    # Fields are already parsed Python objects, not JSON strings
    score_dist = agg_result.score_distribution if agg_result.score_distribution else {}
    skills_coverage = agg_result.skills_coverage if agg_result.skills_coverage else []
    missing_skills = agg_result.missing_skills if agg_result.missing_skills else []
    
    # Extract values
    resume_pool_size = agg_result.resume_pool_size or 0
    top_n_selected = agg_result.top_n_selected or 0
    avg_score = agg_result.avg_score or 0
    max_score = agg_result.max_score or 0
    min_score = agg_result.min_score or 0
    
    return {
        "total_candidates": resume_pool_size,
        "top_candidates_selected": top_n_selected,
        "average_score": round(avg_score, 1),
        "highest_score": round(max_score, 1),
        "lowest_score": round(min_score, 1),
        "score_distribution": {
            "excellent_80_100": score_dist.get('excellent', 0) if isinstance(score_dist, dict) else 0,
            "good_60_79": score_dist.get('good', 0) if isinstance(score_dist, dict) else 0,
            "average_40_59": score_dist.get('average', 0) if isinstance(score_dist, dict) else 0,
            "below_average_0_39": score_dist.get('below_average', 0) if isinstance(score_dist, dict) else 0
        },
        "skills_found": skills_coverage[:10] if isinstance(skills_coverage, list) else [],
        "skills_missing": missing_skills[:10] if isinstance(missing_skills, list) else [],
        "summary": agg_result.summary_text if hasattr(agg_result, 'summary_text') else None
    }


# ==============================================================================
# Helper: Import file_utils function
# ==============================================================================

def get_text_from_file(file_io, filename):
    """Extract text from file - wrapper for file_utils"""
    from utils.file_utils import get_text_from_file as extract_text
    from pathlib import Path
    return extract_text(file_io, Path(filename).suffix)