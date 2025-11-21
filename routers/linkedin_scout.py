"""
LinkedIn Scout Router
Handles LinkedIn profile scraping, analysis, and candidate matching
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from google.cloud import bigquery, storage
from datetime import datetime
import uuid
import json
import traceback
from typing import List, Dict, Any, Optional
import io
from io import BytesIO

# Local imports
import config
from schemas.linkedin_models import (
    LinkedInScoutRequest,
    LinkedInScoutResponse,
    LinkedInJobResponse,
    LinkedInJobSummary,
    LinkedInCandidateResult,
    LinkedInAnalysis
)
# LinkedIn scraping clients - imported dynamically based on config
# from utils.rapidapi_linkedin_client import scrape_linkedin_profiles, search_linkedin_candidates
# from utils.scrapedo_linkedin_client import scrape_linkedin_profiles, search_linkedin_candidates
# from utils.scrapingbee_linkedin_client import scrape_linkedin_profiles, search_linkedin_candidates
# from utils.scraperapi_linkedin_client import scrape_linkedin_profiles, search_linkedin_candidates
from utils.vertex_ai_utils import analyze_linkedin_candidate, generate_linkedin_summary_report

router = APIRouter()

# BigQuery and Storage clients - lazy initialization
_bq_client = None
_storage_client = None

def get_bq_client():
    """Get or initialize BigQuery client"""
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=config.PROJECT_ID)
    return _bq_client

def get_storage_client():
    """Get or initialize Storage client"""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=config.PROJECT_ID)
    return _storage_client

# Table references
DATASET_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}"
LINKEDIN_JOBS_TABLE = f"{DATASET_ID}.linkedin_jobs"
LINKEDIN_RESULTS_TABLE = f"{DATASET_ID}.linkedin_results"


@router.post("/scout", response_model=LinkedInScoutResponse)
async def start_linkedin_scout(
    jd_file: Optional[UploadFile] = File(None, description="Job Description file (PDF/DOCX/TXT)"),
    job_description: Optional[str] = Form(None, description="Job Description text (if not uploading file)"),
    location: str = Form(..., description="Location to search for candidates"),
    min_experience: int = Form(default=0, description="Minimum years of experience"),
    max_experience: int = Form(default=20, description="Maximum years of experience"),
    num_candidates: int = Form(default=10, description="Number of candidates to find"),
    open_to_work_only: bool = Form(default=False, description="Filter for open to work candidates only"),
    user_email: str = Form(default="guest@example.com", description="User email"),
    organization_id: str = Form(default="default_org", description="Organization ID")
):
    """
    Start a LinkedIn scouting job
    
    **Required:** Either jd_file OR job_description must be provided
    **Required:** location
    
    Scrapes LinkedIn profiles, analyzes them against the JD, and stores results
    """
    try:
        # Validate input: must have either file or text
        if not jd_file and not job_description:
            raise HTTPException(
                status_code=400,
                detail="Either jd_file or job_description text must be provided"
            )
        
        # Extract text from file if provided
        jd_text = ""
        jd_filename = "job_description.txt"
        
        if jd_file:
            # Validate file type
            allowed_extensions = ('.pdf', '.docx', '.doc', '.txt')
            if not jd_file.filename.lower().endswith(allowed_extensions):
                raise HTTPException(
                    status_code=400,
                    detail=f"JD file must be {', '.join(allowed_extensions)}"
                )
            
            # Read and extract text from file
            jd_bytes = await jd_file.read()
            jd_text = get_text_from_file(BytesIO(jd_bytes), jd_file.filename)
            jd_filename = jd_file.filename
            print(f"📄 Extracted text from file: {jd_filename} ({len(jd_text)} chars)")
        else:
            # Use provided text
            jd_text = job_description
            print(f"📝 Using provided job description text ({len(jd_text)} chars)")
        
        if not jd_text or len(jd_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Job description is too short. Provide at least 50 characters."
            )
        
        # Generate job ID
        job_id = f"linkedin_scout_{uuid.uuid4().hex[:12]}"
        created_at = datetime.utcnow().isoformat()
        
        print(f"🚀 Starting LinkedIn Scout job: {job_id}")
        print(f"   Location: {location}")
        print(f"   Candidates requested: {num_candidates}")
        print(f"   Experience range: {min_experience}-{max_experience} years")
        print(f"   Open to work only: {open_to_work_only}")
        
        # Insert job record into BigQuery
        bq_client = get_bq_client()
        job_row = {
            "job_id": job_id,
            "jd_filename": jd_filename,
            "job_description": jd_text,
            "location": location,
            "min_experience": min_experience,
            "max_experience": max_experience,
            "num_candidates": num_candidates,
            "open_to_work_only": open_to_work_only,
            "user_email": user_email,
            "organization_id": organization_id,
            "status": "processing",
            "created_at": created_at,
            "updated_at": created_at,
            "completed_at": None,
            "total_found": 0,
            "total_analyzed": 0
        }
        
        errors = bq_client.insert_rows_json(LINKEDIN_JOBS_TABLE, [job_row])
        if errors:
            print(f"❌ BigQuery insert error: {errors}")
            raise HTTPException(status_code=500, detail=f"Failed to create job record: {errors}")
        
        print(f"✅ Job record created in BigQuery")
        
        # Start processing asynchronously (in background)
        # For now, we'll do it synchronously for simplicity
        # In production, use background tasks or Pub/Sub
        
        results = await process_linkedin_scout_job(
            job_id=job_id,
            job_description=jd_text,
            location=location,
            min_experience=min_experience,
            max_experience=max_experience,
            num_candidates=num_candidates,
            open_to_work_only=open_to_work_only,
            user_email=user_email
        )
        
        return LinkedInScoutResponse(
            job_id=job_id,
            message="LinkedIn scouting completed successfully",
            status="completed"
        )
        
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"❌ Error in start_linkedin_scout: {e}\n{tb_str}")
        raise HTTPException(status_code=500, detail=f"Failed to start LinkedIn scout: {str(e)}")


async def process_linkedin_scout_job(
    job_id: str,
    job_description: str,
    location: str,
    min_experience: int,
    max_experience: int,
    num_candidates: int,
    open_to_work_only: bool,
    user_email: str
) -> List[Dict[str, Any]]:
    """
    Process LinkedIn scouting: search candidates, scrape profiles, analyze, store results
    """
    try:
        print(f"\n📋 Processing job {job_id}")
        
        # Step 1: Search LinkedIn for candidates
        print(f"🔍 Step 1: Searching LinkedIn for candidates in {location}...")
        
        # Extract job title from job description using simple keyword matching
        job_title_keyword = "Software Engineer"  # Default fallback
        
        try:
            jd_lower = job_description.lower()
            
            # Check for specific roles (use simple, short keywords)
            if "data engineer" in jd_lower:
                job_title_keyword = "Data Engineer"
            elif "data scientist" in jd_lower or "data science" in jd_lower:
                job_title_keyword = "Data Scientist"
            elif "software engineer" in jd_lower or "software developer" in jd_lower:
                job_title_keyword = "Software Engineer"
            elif "backend" in jd_lower and "engineer" in jd_lower:
                job_title_keyword = "Backend Engineer"
            elif "frontend" in jd_lower and "engineer" in jd_lower:
                job_title_keyword = "Frontend Engineer"
            elif "full stack" in jd_lower or "fullstack" in jd_lower:
                job_title_keyword = "Full Stack Developer"
            elif "devops" in jd_lower:
                job_title_keyword = "DevOps Engineer"
            elif "machine learning" in jd_lower or "ml engineer" in jd_lower:
                job_title_keyword = "Machine Learning Engineer"
            elif "analyst" in jd_lower:
                job_title_keyword = "Data Analyst"
            elif "product manager" in jd_lower:
                job_title_keyword = "Product Manager"
                
        except Exception as e:
            print(f"   ⚠️  Error extracting job title: {e}, using default")
        
        print(f"   🔍 Using search keywords: {job_title_keyword}")
        
        # HYBRID APPROACH: Use HTML scrapers for search, RapidAPI for profile enrichment
        linkedin_urls = []
        search_provider_used = "simple_scraper"
        
        # Use simple scraper only - no paid APIs
        print("   🔍 Using simple scraper with known public profiles")
        
        # Step 1b: Use simple scraper to fetch profiles
        print(f"🕷️ Step 1b: Using simple LinkedIn scraper...")
        
        from utils.simple_linkedin_scraper import scrape_linkedin_candidates
        
        scraped_profiles = scrape_linkedin_candidates(
            job_description=job_description,
            location=location,
            target_count=num_candidates  # Max 5 profiles
        )
        
        if scraped_profiles:
            print(f"✅ Successfully scraped {len(scraped_profiles)} profiles")
        else:
            print(f"⚠️  No profiles found. Try different keywords or location.")
        
        # Step 2: Analyze each profile
        print(f"🧠 Step 2: Analyzing profiles against JD...")
        analyzed_results = []
        
        for idx, profile in enumerate(scraped_profiles, 1):
            print(f"   Analyzing {idx}/{len(scraped_profiles)}: {profile.get('name', 'Unknown')}")
            
            try:
                # Analyze with Gemini
                analysis = analyze_linkedin_candidate(profile, job_description)
                
                candidate_result = {
                    "result_id": f"result_{uuid.uuid4().hex[:12]}",
                    "job_id": job_id,
                    "rank": idx,
                    "linkedin_profile_id": None,  # Extract from URL if possible
                    "linkedin_profile_url": profile.get('url', ''),  # Simple scraper uses 'url' not 'profile_url'
                    "full_name": profile.get('name', 'Unknown'),
                    "headline": profile.get('headline', ''),
                    "current_title": profile.get('experience', [{}])[0].get('title') if profile.get('experience') else None,
                    "current_company": profile.get('experience', [{}])[0].get('company') if profile.get('experience') else None,
                    "current_tenure_years": None,  # Calculate from experience
                    "location": profile.get('location', ''),
                    "total_experience_years": None,  # Calculate from experience
                    "num_positions": len(profile.get('experience', [])),
                    "skills": profile.get('skills', []),
                    "open_to_work": None,  # Extract from profile if available
                    "match_score": analysis.get('match_score', 0),
                    "skills_score": analysis.get('skills_score', 0),
                    "experience_score": analysis.get('experience_score', 0),
                    "education_score": analysis.get('education_score', 0),
                    "key_strengths": analysis.get('key_strengths', ''),
                    "gaps": analysis.get('gaps', ''),
                    "recommendation": analysis.get('recommendation', 'N/A'),
                    "match_reasoning": analysis.get('match_reasoning', ''),
                    "job_hopping_risk": analysis.get('job_hopping_risk'),
                    "job_hopping_detail": analysis.get('job_hopping_detail'),
                    "summary_text": None,  # Can add individual summary if needed
                    "created_at": datetime.utcnow().isoformat(),
                    "raw_profile_json": json.dumps(profile)
                }
                
                analyzed_results.append(candidate_result)
                
            except Exception as e:
                print(f"   ❌ Error analyzing {profile.get('name', 'Unknown')}: {e}")
                # Create error result
                error_result = {
                    "result_id": f"result_{uuid.uuid4().hex[:12]}",
                    "job_id": job_id,
                    "rank": idx,
                    "linkedin_profile_id": None,
                    "linkedin_profile_url": profile.get('url', ''),  # Simple scraper uses 'url' not 'profile_url'
                    "full_name": profile.get('name', 'Unknown'),
                    "headline": profile.get('headline', ''),
                    "current_title": None,
                    "current_company": None,
                    "current_tenure_years": None,
                    "location": profile.get('location', ''),
                    "total_experience_years": None,
                    "num_positions": len(profile.get('experience', [])),
                    "skills": profile.get('skills', []),
                    "open_to_work": None,
                    "match_score": 0,
                    "skills_score": 0,
                    "experience_score": 0,
                    "education_score": 0,
                    "key_strengths": "",
                    "gaps": "Analysis failed",
                    "recommendation": "Error",
                    "match_reasoning": f"Error: {str(e)}",
                    "job_hopping_risk": None,
                    "job_hopping_detail": None,
                    "summary_text": None,
                    "created_at": datetime.utcnow().isoformat(),
                    "raw_profile_json": json.dumps(profile)
                }
                analyzed_results.append(error_result)
        
        print(f"✅ Analysis complete: {len(analyzed_results)} results")
        
        # Step 3: Store results in BigQuery (only if we have results)
        if not analyzed_results or len(analyzed_results) == 0:
            print("   No candidates found to save")
            print("✅ Job completed - no candidates found")
            
            # Insert completed status row (avoid UPDATE on streaming buffer)
            try:
                bq_client = get_bq_client()
                completed_at = datetime.utcnow().isoformat()
                
                # Get original job data
                query = f"""
                SELECT * FROM `{LINKEDIN_JOBS_TABLE}`
                WHERE job_id = '{job_id}'
                LIMIT 1
                """
                query_job = bq_client.query(query)
                results = list(query_job.result())
                
                if results:
                    original_job = dict(results[0])
                    
                    # Insert new row with completed status
                    completed_job_row = {
                        "job_id": job_id,
                        "jd_filename": original_job.get('jd_filename'),
                        "job_description": original_job.get('job_description'),
                        "location": original_job.get('location'),
                        "min_experience": original_job.get('min_experience'),
                        "max_experience": original_job.get('max_experience'),
                        "num_candidates": original_job.get('num_candidates'),
                        "open_to_work_only": original_job.get('open_to_work_only'),
                        "user_email": original_job.get('user_email'),
                        "organization_id": original_job.get('organization_id'),
                        "status": "completed",
                        "created_at": original_job.get('created_at').isoformat() if hasattr(original_job.get('created_at'), 'isoformat') else original_job.get('created_at'),
                        "updated_at": completed_at,
                        "completed_at": completed_at,
                        "total_found": 0,
                        "total_analyzed": 0,
                        "summary_text": "No candidates found matching the search criteria. LinkedIn may be blocking automated searches. Try using direct profile URLs instead."
                    }
                    
                    errors = bq_client.insert_rows_json(LINKEDIN_JOBS_TABLE, [completed_job_row])
                    if errors:
                        print(f"   ⚠️ BigQuery insert error: {errors}")
                    else:
                        print("   ✅ Completed status row inserted in BigQuery")
            except Exception as insert_error:
                print(f"   ⚠️  Could not insert completed status: {insert_error}")
            return
        
        if analyzed_results:
            print(f"💾 Step 3: Storing results in BigQuery...")
            bq_client = get_bq_client()
            errors = bq_client.insert_rows_json(LINKEDIN_RESULTS_TABLE, analyzed_results)
            if errors:
                print(f"❌ BigQuery insert errors: {errors}")
            else:
                print(f"✅ Stored {len(analyzed_results)} results in BigQuery")
        else:
            print(f"⚠️  Step 3: No results to store in BigQuery")
        
        # Step 4: Generate summary report
        print(f"📄 Step 4: Generating summary report...")
        
        if analyzed_results:
            candidates_for_report = []
            for result in analyzed_results:
                candidates_for_report.append({
                    "full_name": result["full_name"],
                    "headline": result["headline"],
                    "match_score": result["match_score"],
                    "skills_score": result["skills_score"],
                    "experience_score": result["experience_score"],
                    "education_score": result["education_score"],
                    "key_strengths": result["key_strengths"],
                    "gaps": result["gaps"],
                    "recommendation": result["recommendation"],
                    "match_reasoning": result["match_reasoning"],
                    "job_hopping_risk": result.get("job_hopping_risk"),
                    "job_hopping_detail": result.get("job_hopping_detail")
                })
            
            # Extract job title from JD or use location as fallback
            job_title = f"Position in {location}"  # Placeholder - can extract from JD with Gemini
            report_markdown = generate_linkedin_summary_report(
                job_title=job_title,
                job_description=job_description,
                candidates_analysis=candidates_for_report
            )
        else:
            # Generate a "no results" report
            job_title = f"Position in {location}"
            report_markdown = f"""# LinkedIn Talent Scout Report
## Position: {job_title}

### Search Criteria
- **Location**: {location}
- **Experience Range**: {min_experience or 0}-{max_experience or 'Any'} years
- **Candidates Requested**: {num_candidates}
- **Open to Work Only**: {'Yes' if open_to_work_only else 'No'}

### Results
No candidates found matching the search criteria.

**Suggestions**:
- Try a broader location (e.g., "Remote" instead of specific city)
- Adjust experience range
- Use different job title keywords
- Remove the "Open to Work" filter if enabled
"""
            print(f"⚠️  No candidates found - generated empty report")
        
        # Step 4.5: Generate Excel report and upload to GCS
        print(f"📊 Step 4.5: Generating Excel report...")
        excel_url = None
        try:
            import tempfile
            from worker.linkedin_processing import export_linkedin_analysis_to_excel
            
            if analyzed_results:
                # Generate Excel in memory
                excel_filename = f"LinkedIn_Scout_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as tmp_file:
                    excel_path = tmp_file.name
                
                # Generate Excel file
                export_linkedin_analysis_to_excel(
                    results=analyzed_results,
                    output_file=excel_path,
                    job_title=job_title,
                    location=location,
                    job_description=job_description
                )
                
                print(f"   ✅ Excel report generated: {excel_path}")
                
                # Upload to GCS
                storage_client = get_storage_client()
                bucket_name = config.GCS_BUCKET
                
                # Create folder structure: linkedin-reports/{user_email}/{job_id}/
                blob_path = f"linkedin-reports/{user_email.replace('@', '_at_').replace('.', '_')}/{job_id}/{excel_filename}"
                
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                
                # Set content type for Excel
                blob.content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                
                # Upload file
                blob.upload_from_filename(
                    excel_path,
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                # Generate signed URL (valid for 7 days) with download disposition
                from datetime import timedelta
                excel_url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(days=7),
                    method="GET",
                    response_disposition=f'attachment; filename="{excel_filename}"'
                )
                
                print(f"   ✅ Excel uploaded to GCS: gs://{bucket_name}/{blob_path}")
                print(f"   ✅ Signed URL generated (valid 7 days)")
                
                # Clean up temp file
                import os
                try:
                    os.unlink(excel_path)
                except:
                    pass
                
                # Append Excel link to the markdown report
                excel_section = f"""

---

## 📊 DETAILED EXCEL REPORT

For a comprehensive breakdown of all candidates with detailed analysis, please download the full Excel report:

**📥 [Download Full Excel Report]({excel_url})**

**The Excel report includes:**
- ✅ Executive Summary Dashboard
- ✅ Detailed Candidate Rankings  
- ✅ Complete Skills Analysis
- ✅ Job Hopping Risk Assessment
- ✅ Experience & Education Details
- ✅ Hiring Recommendations

*Note: The download link is valid for 7 days. Please save the report locally for future reference.*

---
"""
                # Append Excel link to report_markdown for journal storage
                report_markdown += excel_section
                print(f"   ✅ Excel link appended to summary")
            else:
                print(f"   ⓘ  No results to export to Excel")
                
        except Exception as e:
            print(f"   ⚠️ Failed to generate/upload Excel: {e}")
            import traceback
            traceback.print_exc()
            excel_url = None
        
        # Step 5: Store summary in journal_vectors with embeddings (includes Excel link in markdown)
        print(f"🧠 Step 6: Storing insights in journal_vectors...")
        await store_linkedin_insights_in_journal(
            job_id=job_id,
            job_title=job_title,
            location=location,
            min_experience=min_experience,
            max_experience=max_experience,
            num_candidates=num_candidates,
            open_to_work_only=open_to_work_only,
            report_markdown=report_markdown,
            analyzed_results=analyzed_results,
            user_email=user_email
        )
        print(f"✅ Insights stored in journal_vectors")
        
        # Step 7: Insert completed job status (avoid UPDATE on streaming buffer)
        print(f"🔄 Step 7: Inserting completed job status...")
        completed_at = datetime.utcnow().isoformat()
        
        # Get original job data
        query = f"""
        SELECT * FROM `{LINKEDIN_JOBS_TABLE}`
        WHERE job_id = '{job_id}'
        LIMIT 1
        """
        query_job = bq_client.query(query)
        results = list(query_job.result())
        
        if results:
            original_job = dict(results[0])
            
            # Insert new row with completed status (Excel URL stored in report_url)
            completed_job_row = {
                "job_id": job_id,
                "jd_filename": original_job.get('jd_filename'),
                "job_description": original_job.get('job_description'),
                "location": original_job.get('location'),
                "min_experience": original_job.get('min_experience'),
                "max_experience": original_job.get('max_experience'),
                "num_candidates": original_job.get('num_candidates'),
                "open_to_work_only": original_job.get('open_to_work_only'),
                "user_email": original_job.get('user_email'),
                "organization_id": original_job.get('organization_id'),
                "status": "completed",
                "created_at": original_job.get('created_at').isoformat() if hasattr(original_job.get('created_at'), 'isoformat') else original_job.get('created_at'),
                "updated_at": completed_at,
                "completed_at": completed_at,
                "total_found": len(scraped_profiles),
                "total_analyzed": len(analyzed_results),
                "report_url": excel_url,  # ✅ Excel download URL (no separate excel_url column exists)
                "summary_text": report_markdown  # ✅ Full summary with Excel link
            }
            
            errors = bq_client.insert_rows_json(LINKEDIN_JOBS_TABLE, [completed_job_row])
            if errors:
                print(f"⚠️ BigQuery insert error for completed status: {errors}")
            else:
                print(f"✅ Job status row inserted with 'completed' status")
        else:
            print(f"⚠️ Original job record not found for job_id: {job_id}")
        
        return analyzed_results
        
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"❌ Error processing LinkedIn scout job: {e}\n{tb_str}")
        
        # Insert failed job status row (avoid UPDATE on streaming buffer)
        try:
            bq_client = get_bq_client()
            failed_at = datetime.utcnow().isoformat()
            
            # Get original job data
            query = f"""
            SELECT * FROM `{LINKEDIN_JOBS_TABLE}`
            WHERE job_id = '{job_id}'
            LIMIT 1
            """
            query_job = bq_client.query(query)
            results = list(query_job.result())
            
            if results:
                original_job = dict(results[0])
                
                # Insert new row with failed status
                failed_job_row = {
                    "job_id": job_id,
                    "jd_filename": original_job.get('jd_filename'),
                    "job_description": original_job.get('job_description'),
                    "location": original_job.get('location'),
                    "min_experience": original_job.get('min_experience'),
                    "max_experience": original_job.get('max_experience'),
                    "num_candidates": original_job.get('num_candidates'),
                    "open_to_work_only": original_job.get('open_to_work_only'),
                    "user_email": original_job.get('user_email'),
                    "organization_id": original_job.get('organization_id'),
                    "status": "failed",
                    "created_at": original_job.get('created_at').isoformat() if hasattr(original_job.get('created_at'), 'isoformat') else original_job.get('created_at'),
                    "updated_at": failed_at,
                    "completed_at": failed_at,
                    "total_found": 0,
                    "total_analyzed": 0,
                    "summary_text": f"Job failed: {str(e)}"
                }
                
                errors = bq_client.insert_rows_json(LINKEDIN_JOBS_TABLE, [failed_job_row])
                if errors:
                    print(f"⚠️ BigQuery insert error for failed status: {errors}")
                else:
                    print(f"✅ Job status row inserted with 'failed' status")
        except Exception as insert_error:
            print(f"⚠️ Could not insert failed status: {insert_error}")
        
        raise


async def store_linkedin_insights_in_journal(
    job_id: str,
    job_title: str,
    location: str,
    min_experience: int,
    max_experience: int,
    num_candidates: int,
    open_to_work_only: bool,
    report_markdown: str,
    analyzed_results: List[Dict[str, Any]],
    user_email: str
) -> None:
    """
    Store LinkedIn scouting insights in journal_vectors table with embeddings
    This makes the insights searchable via the chatbot, including filter context
    """
    try:
        from utils.vertex_ai_utils import embedding_model
        
        # Calculate statistics
        total_candidates = len(analyzed_results)
        avg_score = sum(r['match_score'] for r in analyzed_results) / total_candidates if total_candidates > 0 else 0
        highly_recommended = len([r for r in analyzed_results if r['recommendation'] == 'Highly Recommended'])
        recommended = len([r for r in analyzed_results if r['recommendation'] == 'Recommended'])
        
        # Build experience range description
        exp_range = ""
        if min_experience is not None and max_experience is not None:
            exp_range = f" with {min_experience}-{max_experience} years experience"
        elif min_experience is not None:
            exp_range = f" with {min_experience}+ years experience"
        elif max_experience is not None:
            exp_range = f" with up to {max_experience} years experience"
        
        # Create a concise summary for embedding including filter context
        embedding_text = f"""LinkedIn Talent Scout Analysis for {job_title} in {location}

Search Criteria:
- Location: {location}
- Candidates requested: {num_candidates}
- Experience range: {exp_range if exp_range else 'Not specified'}
- Open to work only: {'Yes' if open_to_work_only else 'No'}

Results:
Analyzed {total_candidates} LinkedIn candidates with average match score of {avg_score:.1f}%.
{highly_recommended} highly recommended candidates and {recommended} recommended candidates found.

Top Candidates:
"""
        # Add top 5 candidates
        sorted_results = sorted(analyzed_results, key=lambda x: x['match_score'], reverse=True)
        for idx, result in enumerate(sorted_results[:5], 1):
            embedding_text += f"\n{idx}. {result['full_name']} ({result['headline']}) - {result['match_score']:.0f}% match"
            strengths = result['key_strengths'][:200] if result['key_strengths'] else "N/A"
            embedding_text += f"\n   Strengths: {strengths}"
        
        embedding_text += f"\n\nJob Title: {job_title}\nLocation: {location}\nTotal Analyzed: {total_candidates}"
        
        # Generate embedding
        print(f"   📢 Generating embedding vector for LinkedIn insights...")
        try:
            embeddings = embedding_model.get_embeddings([embedding_text])
            embedding_vector = embeddings[0].values if embeddings else []
            print(f"   ✅ Generated embedding vector (dim: {len(embedding_vector)})")
        except Exception as e:
            print(f"   ⚠️ Embedding generation failed: {e}, using empty vector")
            embedding_vector = []
        
        # Prepare journal_vectors record
        now = datetime.utcnow()
        journal_row = {
            "id": f"{job_id}_summary",
            "pdf_name": f"linkedin_scout_{job_id}",
            "title": f"LinkedIn Talent Scout: {job_title}",
            "embedding": embedding_vector,
            "summary": report_markdown,  # Full markdown report
            "source_type": "linkedin_scout",
            "created_at": now,  # Use datetime object, not ISO string
            "record_date": now.date().isoformat(),
            "file_hash": job_id,
            "organization_id": "default_org",
            "user_email": user_email
        }
        
        # Insert into journal_vectors
        bq_client = get_bq_client()
        journal_table = f"{config.PROJECT_ID}.{config.BQ_DATASET}.journal_vectors"
        errors = bq_client.insert_rows_json(journal_table, [journal_row])
        
        if errors:
            print(f"   ⚠️ Failed to insert into journal_vectors: {errors}")
        else:
            print(f"   ✅ LinkedIn insights stored in journal_vectors (searchable via chatbot)")
            
    except Exception as e:
        print(f"⚠️ Error storing LinkedIn insights in journal_vectors: {e}")
        # Don't fail the whole job if journal storage fails
        traceback.print_exc()


async def upload_report_to_gcs(job_id: str, report_content: str) -> str:
    """
    Upload report to Google Cloud Storage as HTML
    
    Returns: Public URL of the uploaded report
    """
    try:
        storage_client = get_storage_client()
        bucket = storage_client.bucket(config.GCS_BUCKET)
        
        # Convert Markdown to HTML with styling
        html_content = markdown_to_html(report_content)
        
        # Create blob path (HTML instead of MD)
        blob_path = f"linkedin-reports/{job_id}.html"
        blob = bucket.blob(blob_path)
        
        # Upload as HTML
        blob.upload_from_string(html_content, content_type='text/html; charset=utf-8')
        
        # Generate signed URL (valid for 7 days)
        url = blob.generate_signed_url(
            version="v4",
            expiration=604800,  # 7 days in seconds
            method="GET"
        )
        
        return url
        
    except Exception as e:
        print(f"❌ Error uploading report to GCS: {e}")
        return f"Error uploading report: {str(e)}"


def markdown_to_html(markdown_text: str) -> str:
    """
    Convert Markdown to styled HTML
    """
    try:
        import markdown
        # Convert markdown to HTML
        html_body = markdown.markdown(markdown_text, extensions=['extra', 'nl2br'])
    except ImportError:
        # Fallback if markdown library not available
        import re
        html_body = markdown_text
        # Headers
        html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_body, flags=re.MULTILINE)
        # Bold
        html_body = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html_body)
        # Lists
        html_body = re.sub(r'^- (.+)$', r'<li>\1</li>', html_body, flags=re.MULTILINE)
        # Line breaks
        html_body = html_body.replace('\n\n', '<br><br>\n')
    
    # Wrap in HTML template with styling
    styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkedIn Talent Scout Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f5;
            color: #333;
        }}
        h1 {{
            color: #0077b5;
            border-bottom: 3px solid #0077b5;
            padding-bottom: 10px;
            margin-bottom: 30px;
            font-size: 2.5em;
        }}
        h2 {{
            color: #0077b5;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-left: 4px solid #0077b5;
            padding-left: 15px;
        }}
        h3 {{
            color: #2c5282;
            margin-top: 25px;
            margin-bottom: 15px;
            font-size: 1.4em;
        }}
        strong {{
            color: #0077b5;
            font-weight: 600;
        }}
        ul {{
            background: white;
            padding: 20px 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 15px 0;
        }}
        li {{
            margin: 10px 0;
            line-height: 1.8;
        }}
        .content {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        @media print {{
            body {{ background: white; }}
            .content {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="content">
        {html_body}
    </div>
    <div class="footer">
        <p>Generated by VANTAGE AI - LinkedIn Talent Scout</p>
        <p>Report Date: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}</p>
    </div>
</body>
</html>"""
    
    return styled_html


@router.get("/jobs/{job_id}", response_model=LinkedInJobResponse)
async def get_linkedin_job(job_id: str):
    """
    Get LinkedIn scouting job details and results
    """
    try:
        bq_client = get_bq_client()
        
        # Get job details (fetch latest status by ordering by updated_at DESC)
        job_query = f"""
        SELECT * FROM `{LINKEDIN_JOBS_TABLE}`
        WHERE job_id = '{job_id}'
        ORDER BY updated_at DESC
        LIMIT 1
        """
        
        job_rows = list(bq_client.query(job_query).result())
        if not job_rows:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job_data = dict(job_rows[0])
        
        # Get results
        results_query = f"""
        SELECT * FROM `{LINKEDIN_RESULTS_TABLE}`
        WHERE job_id = '{job_id}'
        ORDER BY match_score DESC
        """
        
        results_rows = list(bq_client.query(results_query).result())
        
        # Build response
        results = []
        for row in results_rows:
            row_dict = dict(row)
            result = LinkedInCandidateResult(
                result_id=row_dict['result_id'],
                job_id=row_dict['job_id'],
                rank=row_dict.get('rank'),
                linkedin_profile_id=row_dict.get('linkedin_profile_id'),
                linkedin_profile_url=row_dict['linkedin_profile_url'],
                full_name=row_dict['full_name'],
                headline=row_dict['headline'],
                current_title=row_dict.get('current_title'),
                current_company=row_dict.get('current_company'),
                current_tenure_years=row_dict.get('current_tenure_years'),
                location=row_dict.get('location'),
                total_experience_years=row_dict.get('total_experience_years'),
                num_positions=row_dict.get('num_positions'),
                skills=row_dict.get('skills', []),
                open_to_work=row_dict.get('open_to_work'),
                match_score=float(row_dict['match_score']),
                skills_score=float(row_dict['skills_score']),
                experience_score=float(row_dict['experience_score']),
                education_score=float(row_dict['education_score']),
                key_strengths=row_dict['key_strengths'],
                gaps=row_dict['gaps'],
                recommendation=row_dict['recommendation'],
                match_reasoning=row_dict['match_reasoning'],
                job_hopping_risk=row_dict.get('job_hopping_risk'),
                job_hopping_detail=row_dict.get('job_hopping_detail'),
                summary_text=row_dict.get('summary_text'),
                created_at=row_dict['created_at'].isoformat() if hasattr(row_dict['created_at'], 'isoformat') else str(row_dict['created_at']),
                raw_profile_json=row_dict.get('raw_profile_json')
            )
            results.append(result)
        
        # Convert datetime objects to ISO format strings if needed
        def to_iso_string(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value
            # Handle datetime objects
            return value.isoformat() if hasattr(value, 'isoformat') else str(value)
        
        return LinkedInJobResponse(
            job_id=job_data['job_id'],
            jd_filename=job_data.get('jd_filename'),
            job_description=job_data['job_description'],
            location=job_data['location'],
            min_experience=job_data.get('min_experience'),
            max_experience=job_data.get('max_experience'),
            num_candidates=job_data['num_candidates'],
            open_to_work_only=job_data['open_to_work_only'],
            user_email=job_data['user_email'],
            organization_id=job_data['organization_id'],
            status=job_data['status'],
            created_at=to_iso_string(job_data['created_at']),
            updated_at=to_iso_string(job_data.get('updated_at')),
            completed_at=to_iso_string(job_data.get('completed_at')),
            summary_text=job_data.get('summary_text'),
            report_url=job_data.get('report_url'),  # Excel URL stored here
            total_found=job_data.get('total_found'),
            total_analyzed=job_data.get('total_analyzed'),
            error_message=job_data.get('error_message'),
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"❌ Error getting LinkedIn job: {e}\n{tb_str}")
        raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")


@router.get("/download/{job_id}")
async def download_linkedin_report(job_id: str, format: str = "excel"):
    """
    Download the LinkedIn scouting report
    
    Args:
        job_id: Job identifier
        format: Output format - 'excel' (default), 'html', or 'json'
    """
    try:
        # Default to Excel, redirect to Excel endpoint
        if format.lower() in ["excel", "xlsx", "xls"]:
            return await download_linkedin_report_excel(job_id)
        elif format.lower() == "html":
            bq_client = get_bq_client()
            
            # Get report URL
            query = f"""
            SELECT report_url FROM `{LINKEDIN_JOBS_TABLE}`
            WHERE job_id = '{job_id}'
            ORDER BY updated_at DESC
            LIMIT 1
            """
            
            rows = list(bq_client.query(query).result())
            if not rows:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            
            report_url = rows[0]['report_url']
            
            if not report_url or 'Error' in report_url:
                raise HTTPException(status_code=404, detail="Report not available")
            
            # Return redirect to signed URL
            return {"download_url": report_url}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use 'excel', 'html', or 'json'")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error downloading report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download report: {str(e)}")


@router.get("/download/{job_id}/excel")
async def download_linkedin_report_excel(job_id: str):
    """
    Download LinkedIn scouting results as Excel file
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter
        
        bq_client = get_bq_client()
        
        # Get job details
        job_query = f"""
        SELECT * FROM `{LINKEDIN_JOBS_TABLE}`
        WHERE job_id = '{job_id}'
        ORDER BY updated_at DESC
        LIMIT 1
        """
        job_rows = list(bq_client.query(job_query).result())
        if not job_rows:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job_data = dict(job_rows[0])
        
        # Get results
        results_query = f"""
        SELECT * FROM `{LINKEDIN_RESULTS_TABLE}`
        WHERE job_id = '{job_id}'
        ORDER BY match_score DESC
        """
        results_rows = list(bq_client.query(results_query).result())
        
        if not results_rows:
            raise HTTPException(status_code=404, detail=f"No results found for job {job_id}")
        
        # Create Excel workbook
        wb = openpyxl.Workbook()
        
        # Summary Sheet
        ws_summary = wb.active
        ws_summary.title = "Summary"
        
        # Header styling
        header_fill = PatternFill(start_color="0077B5", end_color="0077B5", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=12)
        
        # Add title
        ws_summary['A1'] = 'LinkedIn Talent Scout Report'
        ws_summary['A1'].font = Font(size=16, bold=True, color="0077B5")
        ws_summary.merge_cells('A1:D1')
        
        # Job details
        ws_summary['A3'] = 'Job ID:'
        ws_summary['B3'] = job_id
        ws_summary['A4'] = 'Position:'
        ws_summary['B4'] = job_data.get('location', 'N/A')
        ws_summary['A5'] = 'Total Candidates:'
        ws_summary['B5'] = len(results_rows)
        ws_summary['A6'] = 'Average Match Score:'
        avg_score = sum(float(dict(row)['match_score']) for row in results_rows) / len(results_rows)
        ws_summary['B6'] = f"{avg_score:.1f}/100"
        ws_summary['A7'] = 'Date Generated:'
        ws_summary['B7'] = datetime.utcnow().strftime('%B %d, %Y')
        
        # Style job details
        for row in range(3, 8):
            ws_summary[f'A{row}'].font = Font(bold=True)
        
        # Candidates Sheet
        ws_candidates = wb.create_sheet("Candidates")
        
        # Headers
        headers = [
            'Rank', 'Name', 'Headline', 'Current Title', 'Current Company',
            'Location', 'Match Score', 'Skills Score', 'Experience Score',
            'Education Score', 'Recommendation', 'LinkedIn URL'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws_candidates.cell(row=1, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Add data
        for row_idx, result_row in enumerate(results_rows, 2):
            result = dict(result_row)
            ws_candidates.cell(row=row_idx, column=1).value = row_idx - 1
            ws_candidates.cell(row=row_idx, column=2).value = result.get('full_name', '')
            ws_candidates.cell(row=row_idx, column=3).value = result.get('headline', '')
            ws_candidates.cell(row=row_idx, column=4).value = result.get('current_title', '')
            ws_candidates.cell(row=row_idx, column=5).value = result.get('current_company', '')
            ws_candidates.cell(row=row_idx, column=6).value = result.get('location', '')
            
            # Scores with conditional formatting
            match_score = float(result.get('match_score', 0))
            ws_candidates.cell(row=row_idx, column=7).value = match_score
            ws_candidates.cell(row=row_idx, column=8).value = float(result.get('skills_score', 0))
            ws_candidates.cell(row=row_idx, column=9).value = float(result.get('experience_score', 0))
            ws_candidates.cell(row=row_idx, column=10).value = float(result.get('education_score', 0))
            
            # Color code match score
            score_cell = ws_candidates.cell(row=row_idx, column=7)
            if match_score >= 80:
                score_cell.fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
            elif match_score >= 60:
                score_cell.fill = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
            else:
                score_cell.fill = PatternFill(start_color="FFB6C1", end_color="FFB6C1", fill_type="solid")
            
            ws_candidates.cell(row=row_idx, column=11).value = result.get('recommendation', '')
            ws_candidates.cell(row=row_idx, column=12).value = result.get('linkedin_profile_url', '')
            
            # Add hyperlink
            if result.get('linkedin_profile_url'):
                ws_candidates.cell(row=row_idx, column=12).hyperlink = result.get('linkedin_profile_url')
                ws_candidates.cell(row=row_idx, column=12).font = Font(color="0077B5", underline="single")
        
        # Auto-adjust column widths
        for col in range(1, len(headers) + 1):
            max_length = 0
            column_letter = get_column_letter(col)
            for row in ws_candidates[column_letter]:
                try:
                    if len(str(row.value)) > max_length:
                        max_length = len(str(row.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws_candidates.column_dimensions[column_letter].width = adjusted_width
        
        # Detailed Analysis Sheet
        ws_details = wb.create_sheet("Detailed Analysis")
        ws_details['A1'] = 'Candidate Details'
        ws_details['A1'].font = Font(size=14, bold=True, color="0077B5")
        
        detail_row = 3
        for result_row in results_rows:
            result = dict(result_row)
            
            # Candidate name header
            ws_details[f'A{detail_row}'] = result.get('full_name', '')
            ws_details[f'A{detail_row}'].font = Font(size=12, bold=True)
            ws_details.merge_cells(f'A{detail_row}:D{detail_row}')
            detail_row += 1
            
            # Key strengths
            ws_details[f'A{detail_row}'] = 'Key Strengths:'
            ws_details[f'A{detail_row}'].font = Font(bold=True)
            ws_details[f'B{detail_row}'] = result.get('key_strengths', '')
            detail_row += 1
            
            # Gaps
            ws_details[f'A{detail_row}'] = 'Gaps:'
            ws_details[f'A{detail_row}'].font = Font(bold=True)
            ws_details[f'B{detail_row}'] = result.get('gaps', '')
            detail_row += 1
            
            # Skills
            ws_details[f'A{detail_row}'] = 'Skills:'
            ws_details[f'A{detail_row}'].font = Font(bold=True)
            skills = result.get('skills', [])
            if isinstance(skills, list):
                ws_details[f'B{detail_row}'] = ', '.join(skills)
            else:
                ws_details[f'B{detail_row}'] = str(skills)
            detail_row += 1
            
            # Overall reasoning
            ws_details[f'A{detail_row}'] = 'Analysis:'
            ws_details[f'A{detail_row}'].font = Font(bold=True)
            ws_details[f'B{detail_row}'] = result.get('overall_reasoning', '')
            detail_row += 2
        
        # Adjust column widths for details sheet
        ws_details.column_dimensions['A'].width = 20
        ws_details.column_dimensions['B'].width = 80
        
        # Save to BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        # Return as downloadable file
        filename = f"linkedin_scout_{job_id}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"❌ Error generating Excel report: {e}\n{tb_str}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Excel report: {str(e)}")


@router.get("/jobs", response_model=List[LinkedInJobSummary])
async def list_linkedin_jobs(user_email: str = "guest@vantage.ai", limit: int = 50):
    """
    List LinkedIn scouting jobs for a user
    """
    try:
        bq_client = get_bq_client()
        
        query = f"""
        SELECT 
            job_id,
            job_title,
            status,
            total_candidates,
            candidates_analyzed,
            created_at,
            user_email
        FROM `{LINKEDIN_JOBS_TABLE}`
        WHERE user_email = '{user_email}'
        ORDER BY created_at DESC
        LIMIT {limit}
        """
        
        rows = list(bq_client.query(query).result())
        
        jobs = [LinkedInJobSummary(**dict(row)) for row in rows]
        
        return jobs
        
    except Exception as e:
        print(f"❌ Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


# ==============================================================================
# Helper: Extract text from uploaded files
# ==============================================================================

def get_text_from_file(file_io, filename):
    """Extract text from file - wrapper for file_utils"""
    from utils.file_utils import get_text_from_file as extract_text
    from pathlib import Path
    return extract_text(file_io, Path(filename).suffix)
