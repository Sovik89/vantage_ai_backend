# utils/bigquery_ats_utils.py
"""
BigQuery utilities for ATS Checker
FINAL VERSION with EMBEDDINGS - Matches ACTUAL table schemas in hr_insights dataset
"""

import config
from google.cloud import bigquery
from datetime import datetime
from google.api_core import exceptions as google_exceptions
import json
import hashlib
import vertexai
from vertexai.language_models import TextEmbeddingModel

# --- BigQuery Client Initialization ---
client = bigquery.Client(project=config.PROJECT_ID)

# --- Initialize Vertex AI for embeddings ---
vertexai.init(project=config.PROJECT_ID, location=config.LOCATION)
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

# --- Table Definitions ---
DATASET_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}"
ATS_JOBS_TABLE = f"{DATASET_ID}.ats_jobs"
ATS_RESULTS_TABLE = f"{DATASET_ID}.ats_results"
ATS_CANDIDATES_TABLE = f"{DATASET_ID}.ats_candidates"
JOURNAL_VECTORS_TABLE = f"{DATASET_ID}.journal_vectors"


# ====================================================================================
# EMBEDDING GENERATION
# ====================================================================================

def generate_embedding(text: str, max_length: int = 5000) -> list:
    """
    Generate embedding vector for text using Vertex AI
    
    Args:
        text: Text to embed
        max_length: Maximum text length (text-embedding-004 supports up to 20k chars)
    
    Returns:
        List of floats (768 dimensions for text-embedding-004)
    """
    try:
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        # Generate embedding
        embeddings = embedding_model.get_embeddings([text])
        embedding_vector = embeddings[0].values
        
        print(f"   ✅ Generated embedding: {len(embedding_vector)} dimensions")
        return embedding_vector
        
    except Exception as e:
        print(f"   ⚠️ Error generating embedding: {e}")
        return []  # Return empty list on error


# ====================================================================================
# ATS JOBS - Job tracking
# ====================================================================================

def insert_ats_job(job_id: str, position_title: str, organization: str, 
                   user_email: str, total_candidates: int):
    """
    Insert new ATS job record with status='RUNNING' and all data upfront
    This avoids the UPDATE streaming buffer issue
    
    Args:
        job_id: Unique job ID
        position_title: Job title
        organization: Organization name
        user_email: User email
        total_candidates: Total number of candidates to analyze
    """
    row = {
        "job_id": job_id,
        "position_title": position_title,
        "organization": organization,
        "user_email": user_email,
        "total_candidates_analyzed": total_candidates,  # Set upfront
        "status": "RUNNING",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "record_date": datetime.utcnow().date().isoformat(),
        "record_date_str": datetime.utcnow().strftime("%Y-%m-%d"),
        "meta": json.dumps({}),
    }
    
    try:
        errors = client.insert_rows_json(ATS_JOBS_TABLE, [row])
        if errors:
            print(f"   ❌ Error inserting job: {errors}")
            return False
        else:
            print(f"   ✅ Job created with status: RUNNING")
            return True
    except Exception as e:
        print(f"   ❌ Exception inserting job: {e}")
        return False


def finalize_ats_job(job_id: str, position_title: str, organization: str, 
                     user_email: str, total_candidates: int, status: str = "COMPLETED",
                     report_url: str = None, error_message: str = None):
    """
    Insert final job record with status='COMPLETED' or 'FAILED'
    Uses a new row with same job_id to avoid UPDATE streaming buffer issue
    
    Args:
        job_id: Job ID
        position_title: Job title
        organization: Organization name
        user_email: User email
        total_candidates: Total number of candidates analyzed
        status: 'COMPLETED' or 'FAILED'
        report_url: URL to the Excel report
        error_message: Error message if failed
    """
    now = datetime.utcnow()
    row = {
        "job_id": job_id,
        "position_title": position_title,
        "organization": organization,
        "user_email": user_email,
        "total_candidates_analyzed": total_candidates,
        "status": status,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "completed_at": now.isoformat() if status == "COMPLETED" else None,
        "record_date": now.date().isoformat(),
        "record_date_str": now.strftime("%Y-%m-%d"),
        "report_url": report_url,
        "error_message": error_message,
        "meta": json.dumps({"final_status": True}),
    }
    
    try:
        errors = client.insert_rows_json(ATS_JOBS_TABLE, [row])
        if errors:
            print(f"   ❌ Error finalizing job: {errors}")
            return False
        else:
            print(f"   ✅ Job finalized with status: {status}")
            return True
    except Exception as e:
        print(f"   ❌ Exception finalizing job: {e}")
        return False


# ====================================================================================
# ATS RESULTS - Aggregated analysis results
# ====================================================================================

def insert_aggregated_ats_results(job_id: str, results: list, position_title: str=None, organization: str=None, user_email: str=None, summary: str = None):
    """
    Insert aggregated results WITH individual candidate details for querying
    
    Args:
        job_id: Job ID
        results: List of individual analysis results
        summary: Full analysis summary text (300-400 words) with Excel link
    """
    
    if not results:
        return False
    
    # Calculate aggregated statistics
    total = len(results)
    avg_score = sum(r['overall_match_percentage'] for r in results) / total
    max_score = max(r['overall_match_percentage'] for r in results)
    min_score = min(r['overall_match_percentage'] for r in results)
    
    # Score distribution (all scores)
    score_distribution = [r['overall_match_percentage'] for r in results]
    
    # Skills coverage (all matched skills, deduplicated)
    all_matched_skills = set()
    all_missing_skills = set()
    for r in results:
        all_matched_skills.update(r.get('matched_skills', []))
        all_missing_skills.update(r.get('missing_skills', []))
    
    skills_coverage = list(all_matched_skills)[:50]  # Limit to 50
    missing_skills = list(all_missing_skills)[:50]  # Limit to 50
    
    # Count top candidates (>=70%)
    top_n_selected = len([r for r in results if r['overall_match_percentage'] >= 70])
    
    # ✅ NEW: Store individual candidate details (like sentiment does)
    candidate_details = []
    for idx, r in enumerate(results, 1):
        detail = {
            'rank': idx,
            'candidate_name': r.get('candidate_name', 'Unknown'),
            'overall_score': r.get('overall_match_percentage', 0),
            'skills_match_score': r['component_scores'].get('skills_match', 0),
            'experience_match_score': r['component_scores'].get('experience_match', 0),
            'technical_depth_score': r['component_scores'].get('technical_depth', 0),
            'domain_match_score': r['component_scores'].get('domain_match', 0),
            'total_experience_years': r.get('total_experience_years', 0),
            'current_company': r.get('current_company', ''),
            'current_role': r.get('current_role', ''),
            'matched_skills': r.get('matched_skills', [])[:20],  # Limit to 20
            'missing_skills': r.get('missing_skills', [])[:20],  # Limit to 20
            'match_reason': r.get('match_reason', ''),
            'ai_probability': r.get('ai_generated_flags', {}).get('ai_probability', 0) if r.get('ai_generated_flags') else 0,
            'ai_warning_level': r.get('ai_generated_flags', {}).get('warning_level', 'low') if r.get('ai_generated_flags') else 'low'
        }
        candidate_details.append(detail)
    
    # Create result row
    now = datetime.utcnow()
    result_id = str(hashlib.md5(f"{job_id}_{now.isoformat()}".encode()).hexdigest()[:16])
    row = {
        "result_id": result_id,
        "ingestion_id": job_id,  # Use job_id as ingestion_id
        "job_id": job_id,
        "created_at": now.isoformat(),
        "record_date": now.date().isoformat(),
        "record_date_str": now.strftime("%Y-%m-%d"),
        "processed_by": "ats_processing_module",
        "organization_id": organization,
        "user_email": user_email,
        "resume_pool_size": total,
        "top_n_selected": top_n_selected,
        "avg_score": avg_score,
        "max_score": max_score,
        "min_score": min_score,
        "summary_text": summary,
        "score_distribution": score_distribution,
        "skills_coverage": skills_coverage,
        "missing_skills": missing_skills,
        "details": candidate_details,  # ✅ NEW: Individual candidate details
        "meta": json.dumps({
            "position_title": position_title,
            "high_match_count": len([r for r in results if r['overall_match_percentage'] >= 70]),
            "medium_match_count": len([r for r in results if 50 <= r['overall_match_percentage'] < 70]),
            "low_match_count": len([r for r in results if r['overall_match_percentage'] < 50]),
            "ai_detected_count": len([r for r in results if r.get('ai_generated_flags', {}).get('is_likely_ai_generated', False)]),
            "avg_skills_match": sum(r.get('skills_match_percentage', 0) for r in results) / total,
            "avg_experience": sum(r.get('total_experience_years', 0) for r in results) / total,
        }),
    }
    try:
        errors = client.insert_rows_json(ATS_RESULTS_TABLE, [row])
        if errors:
            print(f"   ❌ Error inserting results: {errors}")
            return False
        else:
            print(f"   ✅ Aggregated results saved")
            return True
    except Exception as e:
        print(f"   ❌ Exception inserting results: {e}")
        import traceback
        traceback.print_exc()
        return False

def insert_ats_results(job_id: str, results: list, position_title: str, 
                       organization: str, user_email: str):
    """
    Insert aggregated ATS results matching actual table schema
    
    Schema fields:
    - result_id, ingestion_id, job_id, created_at, record_date, record_date_str
    - processed_by, organization_id, user_email
    - resume_pool_size, top_n_selected
    - avg_score, max_score, min_score
    - score_distribution (REPEATED FLOAT)
    - skills_coverage (REPEATED STRING)
    - missing_skills (REPEATED STRING)
    - meta (STRING)
    
    Args:
        job_id: Job ID
        results: List of individual candidate results
        position_title: Job title
        organization: Organization name
        user_email: User email
    """
    
    if not results:
        print("   ⚠️ No results to save")
        return False
    
    # Calculate aggregated statistics
    total = len(results)
    avg_score = sum(r['overall_match_percentage'] for r in results) / total
    max_score = max(r['overall_match_percentage'] for r in results)
    min_score = min(r['overall_match_percentage'] for r in results)
    
    # Score distribution (all scores)
    score_distribution = [r['overall_match_percentage'] for r in results]
    
    # Skills coverage (all matched skills, deduplicated)
    all_matched_skills = set()
    all_missing_skills = set()
    for r in results:
        all_matched_skills.update(r.get('matched_skills', []))
        all_missing_skills.update(r.get('missing_skills', []))
    
    skills_coverage = list(all_matched_skills)[:50]  # Limit to 50
    missing_skills = list(all_missing_skills)[:50]  # Limit to 50
    
    # Count top candidates (>=70%)
    top_n_selected = len([r for r in results if r['overall_match_percentage'] >= 70])
    
    # Create result row
    now = datetime.utcnow()
    result_id = str(hashlib.md5(f"{job_id}_{now.isoformat()}".encode()).hexdigest()[:16])
    
    row = {
        "result_id": result_id,
        "ingestion_id": job_id,  # Use job_id as ingestion_id
        "job_id": job_id,
        "created_at": now.isoformat(),
        "record_date": now.date().isoformat(),
        "record_date_str": now.strftime("%Y-%m-%d"),
        "processed_by": "ats_processing_module",
        "organization_id": organization,
        "user_email": user_email,
        "resume_pool_size": total,
        "top_n_selected": top_n_selected,
        "avg_score": avg_score,
        "max_score": max_score,
        "min_score": min_score,
        "score_distribution": score_distribution,
        "skills_coverage": skills_coverage,
        "missing_skills": missing_skills,
        "meta": json.dumps({
            "position_title": position_title,
            "high_match_count": len([r for r in results if r['overall_match_percentage'] >= 70]),
            "medium_match_count": len([r for r in results if 50 <= r['overall_match_percentage'] < 70]),
            "low_match_count": len([r for r in results if r['overall_match_percentage'] < 50]),
            "ai_detected_count": len([r for r in results if r.get('ai_generated_flags', {}).get('is_likely_ai_generated', False)]),
            "avg_skills_match": sum(r.get('skills_match_percentage', 0) for r in results) / total,
            "avg_experience": sum(r.get('total_experience_years', 0) for r in results) / total,
        }),
    }
    
    try:
        errors = client.insert_rows_json(ATS_RESULTS_TABLE, [row])
        if errors:
            print(f"   ❌ Error inserting results: {errors}")
            return False
        else:
            print(f"   ✅ Aggregated results saved")
            return True
    except Exception as e:
        print(f"   ❌ Exception inserting results: {e}")
        import traceback
        traceback.print_exc()
        return False


# ====================================================================================
# JOURNAL VECTORS - Analysis summary/insights WITH EMBEDDINGS
# ====================================================================================

def insert_analysis_summary_to_journal(job_id: str, summary_text: str, 
                                      position_title: str, organization: str, 
                                      user_email: str):
    """
    Insert analysis summary to journal_vectors with EMBEDDINGS for future insights
    
    ACTUAL Schema fields (from your tables.json):
    - pdf_name, title, embedding (REPEATED FLOAT), summary, source_type
    - created_at, file_hash, organization_id, user_email
    
    Args:
        job_id: Job ID
        summary_text: The analysis summary text (from Excel Summary sheet)
        position_title: Job title
        organization: Organization name
        user_email: User email
    """
    
    now = datetime.utcnow()
    
    # Wrap the summary with metadata
    full_summary = f"""ATS Analysis Summary - {position_title}
Job ID: {job_id}
Organization: {organization}
Analysis Date: {now.strftime("%Y-%m-%d %H:%M:%S")}

{summary_text}
"""
    
    # ✅ GENERATE EMBEDDING for the summary
    print("   🔮 Generating embedding for analysis summary...")
    embedding_vector = generate_embedding(full_summary)
    
    # Create row matching ACTUAL schema with EMBEDDINGS
    row = {
        "pdf_name": f"ATS_Analysis_{job_id[:8]}",  # Short identifier
        "title": f"ATS Analysis: {position_title}",
        "embedding": embedding_vector,  # ✅ NOW WITH EMBEDDINGS!
        "summary": full_summary,
        "source_type": "ats_analysis",
        "created_at": now.isoformat(),
        "file_hash": hashlib.md5(full_summary.encode()).hexdigest(),
        "organization_id": organization,
        "user_email": user_email,
    }
    
    try:
        errors = client.insert_rows_json(JOURNAL_VECTORS_TABLE, [row])
        if errors:
            print(f"   ❌ Error inserting journal entry: {errors}")
            return False
        else:
            print(f"   ✅ Analysis summary saved to journal with embeddings")
            return True
    except Exception as e:
        print(f"   ❌ Exception inserting journal: {e}")
        import traceback
        traceback.print_exc()
        return False


# ====================================================================================
# SEMANTIC SEARCH - Find similar analysis summaries
# ====================================================================================

def search_similar_analyses(query_text: str, limit: int = 5, min_similarity: float = 0.7):
    """
    Search for similar ATS analyses using vector similarity
    
    Args:
        query_text: Search query (e.g., "Data Scientist with Python skills")
        limit: Number of results to return
        min_similarity: Minimum cosine similarity (0-1)
    
    Returns:
        List of similar analyses with scores
    """
    
    try:
        # Generate embedding for query
        print(f"🔍 Searching for: '{query_text}'")
        query_embedding = generate_embedding(query_text)
        
        if not query_embedding:
            print("   ❌ Failed to generate query embedding")
            return []
        
        # Use BigQuery vector search
        query = f"""
        SELECT 
            pdf_name,
            title,
            summary,
            source_type,
            organization_id,
            created_at,
            ML.DISTANCE(embedding, {query_embedding}, 'COSINE') AS distance,
            (1 - ML.DISTANCE(embedding, {query_embedding}, 'COSINE')) AS similarity
        FROM `{JOURNAL_VECTORS_TABLE}`
        WHERE source_type = 'ats_analysis'
        AND ARRAY_LENGTH(embedding) > 0
        ORDER BY similarity DESC
        LIMIT {limit}
        """
        
        results = client.query(query).result()
        
        similar_analyses = []
        for row in results:
            if row.similarity >= min_similarity:
                similar_analyses.append({
                    "title": row.title,
                    "summary": row.summary[:500] + "..." if len(row.summary) > 500 else row.summary,
                    "organization": row.organization_id,
                    "created_at": row.created_at,
                    "similarity": round(row.similarity, 3)
                })
        
        print(f"   ✅ Found {len(similar_analyses)} similar analyses")
        return similar_analyses
        
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return []


# ====================================================================================
# ATS CANDIDATES - Phase 2 (Candidate tracking across jobs)
# ====================================================================================

def upsert_candidate(email: str, candidate_data: dict, analysis_result: dict):
    """
    Insert or update candidate in ats_candidates table
    PHASE 2 function - for candidate tracking across multiple jobs
    
    Args:
        email: Candidate email (unique identifier)
        candidate_data: Dict with candidate info (name, phone, company, etc.)
        analysis_result: Dict with analysis results
    """
    
    if not email or not candidate_data:
        return False
    
    try:
        # Generate candidate_id from email
        candidate_id = hashlib.md5(email.lower().encode()).hexdigest()[:16]
        
        # Check if candidate exists
        query = f"""
        SELECT * FROM `{ATS_CANDIDATES_TABLE}`
        WHERE candidate_id = @candidate_id
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("candidate_id", "STRING", candidate_id)
            ]
        )
        
        results = list(client.query(query, job_config=job_config).result())
        existing = dict(results[0]) if results else None
        
        now = datetime.utcnow().isoformat()
        
        if existing:
            # Update existing candidate - use MERGE to avoid streaming buffer issue
            times_analyzed = existing.get("times_analyzed", 0) + 1
            current_match = analysis_result.get("overall_match_percentage", 0)
            avg_match = ((existing.get("average_match_score", 0) * existing.get("times_analyzed", 0)) + current_match) / times_analyzed
            best_match = max(existing.get("best_match_score", 0), current_match)
            
            ai_detection_count = existing.get("ai_detection_count", 0)
            if analysis_result.get("ai_generated_flags", {}).get("is_likely_ai_generated"):
                ai_detection_count += 1
            
            current_ai_prob = analysis_result.get("ai_generated_flags", {}).get("ai_generated_probability", 0)
            avg_ai_prob = ((existing.get("avg_ai_probability", 0) * existing.get("times_analyzed", 0)) + current_ai_prob) / times_analyzed
            
            # Insert new row (append mode)
            row = {
                "candidate_id": candidate_id,
                "candidate_name": candidate_data.get("name"),
                "email": email,
                "phone": candidate_data.get("phone"),
                "current_company": candidate_data.get("current_company"),
                "total_experience_years": float(candidate_data.get("total_experience", 0)),
                "skills": candidate_data.get("skills", [])[:50],  # Limit
                "certifications": candidate_data.get("certifications", [])[:20],  # Limit
                "education_json": json.dumps(candidate_data.get("education", [])),
                "times_analyzed": times_analyzed,
                "average_match_score": float(avg_match),
                "best_match_score": float(best_match),
                "best_match_position": analysis_result.get("job_id", ""),
                "ai_detection_count": ai_detection_count,
                "avg_ai_probability": float(avg_ai_prob),
                "first_analyzed": existing.get("first_analyzed"),
                "last_analyzed": now,
                "created_at": existing.get("created_at"),
                "updated_at": now,
                "cv_structured_json": json.dumps(candidate_data),
                "meta": json.dumps({"last_update": "ats_analysis"}),
            }
            
            errors = client.insert_rows_json(ATS_CANDIDATES_TABLE, [row])
            if errors:
                print(f"   ❌ Error updating candidate: {errors}")
                return False
            else:
                print(f"   ✅ Updated candidate: {candidate_data.get('name')}")
                return True
            
        else:
            # Insert new candidate
            row = {
                "candidate_id": candidate_id,
                "candidate_name": candidate_data.get("name"),
                "email": email,
                "phone": candidate_data.get("phone"),
                "current_company": candidate_data.get("current_company"),
                "total_experience_years": float(candidate_data.get("total_experience", 0)),
                "skills": candidate_data.get("skills", [])[:50],  # Limit
                "certifications": candidate_data.get("certifications", [])[:20],  # Limit
                "education_json": json.dumps(candidate_data.get("education", [])),
                "times_analyzed": 1,
                "average_match_score": float(analysis_result.get("overall_match_percentage", 0)),
                "best_match_score": float(analysis_result.get("overall_match_percentage", 0)),
                "best_match_position": analysis_result.get("job_id", ""),
                "ai_detection_count": 1 if analysis_result.get("ai_generated_flags", {}).get("is_likely_ai_generated") else 0,
                "avg_ai_probability": float(analysis_result.get("ai_generated_flags", {}).get("ai_generated_probability", 0)),
                "first_analyzed": now,
                "last_analyzed": now,
                "created_at": now,
                "updated_at": now,
                "cv_structured_json": json.dumps(candidate_data),
                "meta": json.dumps({}),
            }
            
            errors = client.insert_rows_json(ATS_CANDIDATES_TABLE, [row])
            if errors:
                print(f"   ❌ Error inserting candidate: {errors}")
                return False
            else:
                print(f"   ✅ Inserted new candidate: {row['candidate_name']}")
                return True
                
    except Exception as e:
        print(f"   ❌ Exception in upsert_candidate: {e}")
        import traceback
        traceback.print_exc()
        return False


def append_excel_link_to_summary(job_id: str, excel_link_text: str):
    """
    Append Excel download link to existing summary in ats_results table
    
    Args:
        job_id: Job ID
        excel_link_text: Text to append with Excel link
    """
    try:
        # Fetch current summary
        query = f"""
        SELECT result_id, summary_text
        FROM `{ATS_RESULTS_TABLE}`
        WHERE job_id = @job_id
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("job_id", "STRING", job_id)]
        )
        
        results = list(client.query(query, job_config=job_config).result())
        
        if not results:
            print(f"   ⚠️ No results found for job_id {job_id}")
            return False
        
        result = results[0]
        current_summary = result.summary_text or ""
        result_id = result.result_id
        
        # Append Excel link to summary
        updated_summary = current_summary + excel_link_text
        
        # Update the row (BigQuery DML UPDATE)
        update_query = f"""
        UPDATE `{ATS_RESULTS_TABLE}`
        SET summary_text = @updated_summary
        WHERE result_id = @result_id
        """
        
        update_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("updated_summary", "STRING", updated_summary),
                bigquery.ScalarQueryParameter("result_id", "STRING", result_id)
            ]
        )
        
        client.query(update_query, job_config=update_config).result()
        print(f"   ✅ Summary updated with Excel link for result_id {result_id}")
        return True
        
    except Exception as e:
        print(f"   ❌ Exception appending Excel link: {e}")
        import traceback
        traceback.print_exc()
        return False


print("✅ BigQuery ATS Utils Loaded (WITH EMBEDDINGS - text-embedding-005)")