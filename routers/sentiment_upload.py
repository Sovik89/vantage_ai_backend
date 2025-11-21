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
from schemas.sentiment_models import SentimentQueryRequest, SentimentQueryResponse
from utils import vertex_ai_utils


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
                
                # ✅ INSERT new row with COMPLETED status and GCS URL
                try:
                    completion_job_row = {
                        "job_id": job_id,
                        "ingestion_id": str(uuid.uuid4()),  # Same job, new record
                        "user_email": user_email,
                        "organization_id": organization_id,
                        "status": "COMPLETED",  # ✅ Mark as completed
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                        "record_date": datetime.now().date().isoformat(),
                        "record_date_str": datetime.now().strftime("%d-%m-%Y"),
                        "report_url": signed_url,  # ✅ GCS signed URL
                        "error_message": None,
                        "meta": json.dumps({
                            "filename": file.filename,
                            "domain": domain,
                            "gcs_path": blob_path,
                            "total_texts": total_texts
                        })
                    }
                    
                    print(f"📤 Inserting COMPLETED job row with report URL...")
                    errors = _bq.insert_rows_json(SENTIMENT_JOBS_TABLE, [completion_job_row])
                    
                    if errors:
                        print(f"⚠️ Error inserting COMPLETED row: {errors}")
                    else:
                        print(f"✅ COMPLETED job row inserted with GCS URL")
                        
                except Exception as e:
                    print(f"⚠️ Failed to insert COMPLETED job row: {e}")
                    traceback.print_exc()
                
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
        ORDER BY updated_at DESC
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
        ORDER BY updated_at DESC
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
    
# ============================================================================
# ENDPOINT 4: POST /agents/sentiment/query
# ============================================================================
    

@router.post("/query", response_model=SentimentQueryResponse)
async def query_sentiment_analysis(request: SentimentQueryRequest):
    """
    Query completed sentiment analysis using LLM with BigQuery context
    
    Example queries:
    - "What are the top 3 reasons employees are leaving?"
    - "Which candidates had the most negative feedback?"
    - "What themes appear most frequently in exit interviews?"
    """
    
    try:
        # 1. Validate job exists and is completed
        job_query = f"""
        SELECT status, created_at
        FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_jobs`
        WHERE job_id = @job_id
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("job_id", "STRING", request.job_id)
            ]
        )
        
        job_results = list(_bq.query(job_query, job_config=job_config).result())
        
        if not job_results:
            raise HTTPException(404, "Job not found")
        
        # holding it for just testing purpose

        if job_results[0].status != 'COMPLETED':
            raise HTTPException(400, "Job not completed yet. Please wait for processing to finish.")
        
        # 2. Fetch sentiment results
        results_query = f"""
        SELECT
            result_id,
            unit_level,
            questionnaire_name,
            total_texts,
            positive_count,
            neutral_count,
            negative_count,
            sentiment_index,
            average_confidence,
            summary_text,
            details
        FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_results`
        WHERE job_id = @job_id
        """
        
        results = list(_bq.query(results_query, job_config=job_config).result())
        
        if not results:
            raise HTTPException(404, "No results found for this job")
        
        # 3. Build context from results
        context = build_sentiment_context(results)
        
        # 4. Build prompt for Gemini
        prompt = f"""You are an expert HR analytics assistant analyzing employee sentiment data.

        Your role is to provide actionable, data-driven insights based on sentiment analysis results.

        SENTIMENT ANALYSIS DATA:
        {context}

        USER QUESTION:
        {request.query}
        
        AVOID: vague or generic answers. Focus on specifics from the data provided.

        INSTRUCTIONS:
        1. Answer the question directly using the data provided above
        2. Include specific numbers, percentages, and sentiment scores
        3. Cite examples from actual feedback when relevant
        4. Provide actionable recommendations when appropriate
        5. Format your response with clear structure (headers, bullet points)
        6. Be concise but thorough.
        7. If the data does not support a definitive answer, state that clearly.
        8. Do not make up data or statistics - rely only on the provided information.
        9. Only answer if related to analysis done by user on SENTIMENT ANALYSIS DATA above.
        10. Only consider data if the user says like last time, previously, earlier etc. DO NOT bring any other data. If not found gracefully say "NO DATA FOUND"
        11. User may ask for specific candidates or questions - only answer if that data is present in SENTIMENT ANALYSIS DATA. and User may ask specific dates - only answer if that data is present in SENTIMENT ANALYSIS DATA.
        ANSWER:"""
        
        # 5. Call Gemini
        # answer = vertex_ai_utils.generate_text_gemini(
        #     prompt=prompt,
        #     max_tokens=1000,
        #     temperature=0.3  # Lower temperature for more factual responses
        # )
        answer = vertex_ai_utils.generate_freeform(prompt)
        
        # 6. Extract supporting data
        supporting_data = extract_sentiment_supporting_data(results)
        
        # 7. Get relevant example sources
        sources = extract_relevant_sources(results, request.query)
        
        return SentimentQueryResponse(
            job_id=request.job_id,
            query=request.query,
            answer=answer,
            supporting_data=supporting_data,
            sources=sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error querying sentiment analysis: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to query sentiment analysis: {str(e)}")


def build_sentiment_context(results: List) -> str:
    """
    Build context from sentiment results for Claude to answer queries
    Includes overall stats and questionnaire-level insights
    
    ✅ FIXED: Zero-division protection
    ✅ FIXED: Dict access for details
    ✅ FIXED: Correct unit_level filtering ('doc' instead of 'overall')
    """
    
    # Get overall metrics from 'doc' level result
    overall_results = [r for r in results if r.unit_level == 'doc']
    
    if overall_results:
        doc_result = overall_results[0]
        total_texts = doc_result.total_texts or 0
        total_positive = doc_result.positive_count or 0
        total_neutral = doc_result.neutral_count or 0
        total_negative = doc_result.negative_count or 0
        overall_details = doc_result.details or []
    else:
        # Fallback: sum questionnaire-level results
        questionnaire_results = [r for r in results if r.unit_level == 'questionnaire']
        total_texts = sum(r.total_texts or 0 for r in questionnaire_results)
        total_positive = sum(r.positive_count or 0 for r in questionnaire_results)
        total_neutral = sum(r.neutral_count or 0 for r in questionnaire_results)
        total_negative = sum(r.negative_count or 0 for r in questionnaire_results)
        overall_details = []
        for r in questionnaire_results:
            if r.details:
                overall_details.extend(r.details)
    
    # Check for zero before division
    overall_sentiment_index = (total_positive - total_negative) / total_texts if total_texts > 0 else 0
    
    # Calculate percentages safely
    positive_pct = (total_positive / total_texts * 100) if total_texts > 0 else 0
    neutral_pct = (total_neutral / total_texts * 100) if total_texts > 0 else 0
    negative_pct = (total_negative / total_texts * 100) if total_texts > 0 else 0
    
    # Extract candidate info from details
    candidate_sentiments = {}
    for detail in overall_details:
        candidate_name = detail.get('candidate_name', 'Unknown')
        label = detail.get('label', 'neutral')
        
        if candidate_name not in candidate_sentiments:
            candidate_sentiments[candidate_name] = {'positive': 0, 'neutral': 0, 'negative': 0}
        
        candidate_sentiments[candidate_name][label] += 1
    
    # Calculate candidate-level sentiment indices
    candidate_summaries = []
    for name, counts in candidate_sentiments.items():
        total = sum(counts.values())
        if total > 0:
            sentiment_idx = (counts['positive'] - counts['negative']) / total
            candidate_summaries.append({
                'name': name,
                'sentiment_index': sentiment_idx,
                'positive': counts['positive'],
                'neutral': counts['neutral'],
                'negative': counts['negative']
            })
    
    candidate_summaries.sort(key=lambda x: x['sentiment_index'], reverse=True)
    
    context = f"""
    OVERALL SENTIMENT SUMMARY:
    - Total Texts Analyzed: {total_texts}
    - Total Candidates: {len(candidate_sentiments)}
    - Sentiment Index: {overall_sentiment_index:.3f} (range: -1 to +1)
    - Positive: {total_positive} ({positive_pct:.1f}%)
    - Neutral: {total_neutral} ({neutral_pct:.1f}%)
    - Negative: {total_negative} ({negative_pct:.1f}%)

    CANDIDATE-LEVEL INSIGHTS:
    """
    
    # Top 5 most positive candidates
    context += "\nTop 5 Most Positive Candidates:\n"
    for c in candidate_summaries[:5]:
        context += f"- {c['name']}: Sentiment {c['sentiment_index']:.2f} "
        context += f"({c['positive']}+ / {c['neutral']}= / {c['negative']}-)\n"
    
    # Top 5 most negative candidates
    context += "\nTop 5 Most Negative Candidates:\n"
    for c in candidate_summaries[-5:]:
        context += f"- {c['name']}: Sentiment {c['sentiment_index']:.2f} "
        context += f"({c['positive']}+ / {c['neutral']}= / {c['negative']}-)\n"
    
    # Questionnaire-level insights
    questionnaire_results = [r for r in results if r.unit_level == 'questionnaire']
    questionnaire_results.sort(key=lambda x: x.sentiment_index or 0)
    
    context += "\nQUESTIONNAIRE/SHEET-LEVEL INSIGHTS:\n"
    
    if len(questionnaire_results) > 0:
        context += "\nMost Negative Questionnaires:\n"
        for r in questionnaire_results[:3]:
            context += f"- {r.questionnaire_name}: Sentiment {r.sentiment_index:.2f} "
            context += f"({r.positive_count}+ / {r.negative_count}-)\n"
        
        context += "\nMost Positive Questionnaires:\n"
        for r in questionnaire_results[-3:]:
            context += f"- {r.questionnaire_name}: Sentiment {r.sentiment_index:.2f} "
            context += f"({r.positive_count}+ / {r.negative_count}-)\n"
    
    # Add sample feedback details
    context += "\nSAMPLE FEEDBACK EXAMPLES:\n"
    
    sample_count = 0
    for detail in overall_details[:10]:  # First 10 details
        text_snippet = detail.get('text_snippet', '')
        label = detail.get('label', 'unknown')
        confidence = detail.get('confidence', 0.0)
        candidate_name = detail.get('candidate_name', 'Unknown')
        question_text = detail.get('question_text', 'N/A')
        
        if text_snippet and sample_count < 5:
            context += f"\n- Candidate: {candidate_name}\n"
            context += f"  Question: {question_text[:100]}...\n" if len(question_text) > 100 else f"  Question: {question_text}\n"
            context += f"  Feedback: \"{text_snippet[:150]}...\"\n"
            context += f"  Sentiment: {label} (confidence: {confidence:.2f})\n"
            sample_count += 1
    
    return context


def extract_sentiment_supporting_data(results: List) -> Dict:
    """
    Extract key metrics as supporting data
    """
    
    overall = [r for r in results if r.unit_level == 'overall']
    
    if not overall:
        return {}
    
    o = overall[0]
    
    return {
        "total_analyzed": o.total_texts,
        "positive_count": o.positive_count,
        "neutral_count": o.neutral_count,
        "negative_count": o.negative_count,
        "sentiment_index": float(o.sentiment_index),
        "average_confidence": float(o.average_confidence) if o.average_confidence else None,
        "candidates_analyzed": len([r for r in results if r.unit_level == 'candidate']),
        "questions_analyzed": len([r for r in results if r.unit_level == 'question'])
    }


def extract_relevant_sources(results: List, query: str) -> List[Dict]:
    """
    Extract relevant feedback examples based on query
    
    This is a simple implementation - could be enhanced with embedding similarity
    """
    
    sources = []
    
    # Extract sample feedback from details
    for r in results:
        if r.details and len(r.details) > 0:
            for detail in r.details[:3]:  # Max 3 per result
                sources.append({
                    "candidate": r.questionnaire_name if r.unit_level == 'candidate' else None,
                    "question": detail.question_text if hasattr(detail, 'question_text') else None,
                    "feedback_snippet": detail.text_snippet[:200] if hasattr(detail, 'text_snippet') else None,
                    "sentiment": detail.label if hasattr(detail, 'label') else None,
                    "confidence": float(detail.confidence) if hasattr(detail, 'confidence') else None
                })
    
    # Return max 5 sources
    return sources[:5]