# scripts/local_full_run_debug.py
"""
Enhanced test script for sentiment processing WITH REAL BIGQUERY.
Processes existing Excel files from test_data folder.
"""

import os
import sys
import uuid
import traceback
from datetime import datetime
import glob

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

print(f"DEBUG: repo root on sys.path -> {REPO_ROOT}")

# Test data directory
TEST_DATA_DIR = os.path.join(REPO_ROOT, "test_data")
os.makedirs(TEST_DATA_DIR, exist_ok=True)

def list_available_files():
    """List all Excel files in test_data folder."""
    excel_files = glob.glob(os.path.join(TEST_DATA_DIR, "*.xlsx"))
    excel_files += glob.glob(os.path.join(TEST_DATA_DIR, "*.xls"))
    
    if not excel_files:
        print(f"⚠️  No Excel files found in {TEST_DATA_DIR}")
        return []
    
    print(f"\n📁 Found {len(excel_files)} Excel file(s) in test_data folder:")
    print("="*80)
    for idx, file in enumerate(excel_files, 1):
        filename = os.path.basename(file)
        size_kb = os.path.getsize(file) / 1024
        print(f"  {idx}. {filename} ({size_kb:.1f} KB)")
    print("="*80)
    
    return excel_files

def select_file_interactive():
    """Let user select which file to process."""
    files = list_available_files()
    
    if not files:
        print("\n❌ No files available. Please add Excel files to test_data folder.")
        return None
    
    if len(files) == 1:
        print(f"\n✅ Auto-selecting the only file: {os.path.basename(files[0])}")
        return files[0]
    
    print(f"\n📝 Select a file to process:")
    print(f"   Enter 1-{len(files)} to select a specific file")
    print(f"   Enter 'a' to process ALL files")
    print(f"   Enter 'q' to quit")
    
    choice = input("\nYour choice: ").strip().lower()
    
    if choice == 'q':
        print("👋 Exiting...")
        return None
    elif choice == 'a':
        return 'all'
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                return files[idx]
            else:
                print(f"❌ Invalid choice. Please enter 1-{len(files)}")
                return select_file_interactive()
        except ValueError:
            print(f"❌ Invalid input. Please enter a number, 'a', or 'q'")
            return select_file_interactive()

def run_single_file(file_path, use_new_processor=True):
    """
    Process a single Excel file with sentiment analysis.
    
    Args:
        file_path: Path to Excel file
        use_new_processor: If True, uses new candidate-aware sentiment_processing.py
    """
    
    filename = os.path.basename(file_path)
    
    print(f"\n{'='*80}")
    print(f"🔄 PROCESSING FILE: {filename}")
    print(f"{'='*80}\n")
    
    # Import the sentiment processing module
    print(f"DEBUG: importing worker.sentiment_processing...")
    try:
        if use_new_processor:
            from worker import sentiment_processing
            print("DEBUG: Using NEW candidate-aware sentiment_processing")
        else:
            from worker import sentiment_processing_old as sentiment_processing
            print("DEBUG: Using OLD sentiment_processing")
    except Exception as e:
        print(f"ERROR: failed to import sentiment processing module")
        traceback.print_exc()
        return False
    
    # Verify BigQuery client
    from google.cloud import bigquery
    import config
    
    try:
        real_bq_client = bigquery.Client(project=config.PROJECT_ID)
        print(f"✅ Real BigQuery client initialized: {real_bq_client.project}")
    except Exception as e:
        print(f"❌ Failed to initialize BigQuery client: {e}")
        traceback.print_exc()
        return False
    
    # Detect domain from filename
    filename_lower = filename.lower()
    if "exit" in filename_lower:
        domain = "exit_feedback"
    elif "onboarding" in filename_lower:
        domain = "onboarding_feedback"
    elif "training" in filename_lower:
        domain = "training_feedback"
    elif "appraisal" in filename_lower or "performance" in filename_lower:
        domain = "appraisal_feedback"
    elif "pulse" in filename_lower:
        domain = "pulse_feedback"
    else:
        domain = "general"
    
    print(f"🏷️  Detected domain: {domain}")
    
    # Read file
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        print(f"✅ Read {len(file_bytes)} bytes from file")
    except Exception as e:
        print(f"❌ Failed to read file: {e}")
        return False
    
    # Prepare payload
    job_id = str(uuid.uuid4())
    payload = {
        "job_id": job_id,
        "ingestion_id": str(uuid.uuid4()),
        "file_bytes": file_bytes.hex(),
        "filename": filename,
        "domain": domain,
        "user_email": "tester@example.com",
        "organization_id": "test_org_001",
        "include_full_text": False
    }
    
    print(f"\n{'='*80}")
    print(f"🚀 Starting sentiment processing WITH REAL BIGQUERY")
    print(f"{'='*80}")
    print(f"   Job ID: {job_id}")
    print(f"   File: {filename}")
    print(f"   Domain: {domain}")
    print(f"   Organization: test_org_001")
    print(f"{'='*80}\n")
    
    # Call process_job
    try:
        start_time = datetime.now()
        result_id, summary = sentiment_processing.process_job(payload, sync_mode=True)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"✅ PROCESSING COMPLETED")
        print(f"{'='*80}")
        print(f"   File: {filename}")
        print(f"   Duration: {duration:.2f} seconds")
        print(f"   Result ID: {result_id}")
        print(f"   Summary: {summary}")
        print(f"{'='*80}\n")
        
        # Verify data in BigQuery
        print(f"🔍 Verifying data in BigQuery...")
        verify_bq_data(job_id)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Processing failed with exception:")
        print(f"   {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

def verify_bq_data(job_id: str):
    """Query BigQuery to verify data was inserted."""
    import config
    from google.cloud import bigquery
    
    try:
        client = bigquery.Client(project=config.PROJECT_ID)
        
        # Check sentiment_jobs
        print(f"\n📊 Checking sentiment_jobs table...")
        query = f"""
        SELECT job_id, status, created_at, updated_at
        FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_jobs`
        WHERE job_id = @job_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
            ]
        )
        
        results = list(client.query(query, job_config=job_config).result())
        if results:
            for row in results:
                print(f"✅ Found job record:")
                print(f"   job_id: {row.job_id}")
                print(f"   status: {row.status}")
                print(f"   created_at: {row.created_at}")
        else:
            print(f"⚠️  No job record found for job_id: {job_id}")
        
        # Check sentiment_results
        print(f"\n📊 Checking sentiment_results table...")
        query = f"""
        SELECT result_id, unit_level, questionnaire_name, 
               total_texts, positive_count, neutral_count, negative_count,
               sentiment_index
        FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_results`
        WHERE job_id = @job_id
        ORDER BY unit_level DESC
        """
        
        results = list(client.query(query, job_config=job_config).result())
        if results:
            print(f"✅ Found {len(results)} result record(s):")
            for row in results:
                print(f"\n   result_id: {row.result_id}")
                print(f"   unit_level: {row.unit_level}")
                print(f"   questionnaire: {row.questionnaire_name}")
                print(f"   total_texts: {row.total_texts}")
                print(f"   positive/neutral/negative: {row.positive_count}/{row.neutral_count}/{row.negative_count}")
                print(f"   sentiment_index: {row.sentiment_index:.3f}")
        else:
            print(f"⚠️  No result records found for job_id: {job_id}")
        
        # Check journal_vectors
        print(f"\n📊 Checking journal_vectors table...")
        query = f"""
        SELECT COUNT(*) as count
        FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.journal_vectors`
        WHERE pdf_name LIKE '%sentiment_summary%'
        """
        
        results = list(client.query(query).result())
        count = results[0].count if results else 0
        print(f"✅ Total sentiment summaries in journal_vectors: {count}")
        
    except Exception as e:
        print(f"❌ BigQuery verification failed: {e}")
        traceback.print_exc()

def run():
    """Main runner - let user select files to process."""
    
    print("\n" + "="*80)
    print("🚀 SENTIMENT PROCESSING WITH REAL BIGQUERY")
    print("="*80)
    
    # Check environment first
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set!")
        print("   Set it with: $env:GOOGLE_APPLICATION_CREDENTIALS='path/to/key.json'")
        sys.exit(1)
    elif not os.path.exists(creds):
        print(f"❌ Credentials file not found: {creds}")
        sys.exit(1)
    else:
        print(f"✅ Using credentials: {creds}")
    
    # Select file(s) to process
    selected = select_file_interactive()
    
    if selected is None:
        return
    
    # Process file(s)
    if selected == 'all':
        files = list_available_files()
        print(f"\n🔄 Processing ALL {len(files)} files...\n")
        
        success_count = 0
        for idx, file in enumerate(files, 1):
            print(f"\n{'='*80}")
            print(f"📂 FILE {idx}/{len(files)}")
            print(f"{'='*80}")
            
            success = run_single_file(file, use_new_processor=True)
            if success:
                success_count += 1
            
            print(f"\n{'='*80}")
            print(f"✅ Completed {idx}/{len(files)} files | Success: {success_count}")
            print(f"{'='*80}\n")
        
        print(f"\n🎉 ALL FILES PROCESSED!")
        print(f"   Total: {len(files)}")
        print(f"   Success: {success_count}")
        print(f"   Failed: {len(files) - success_count}")
        
    else:
        # Process single file
        run_single_file(selected, use_new_processor=True)
    
    print("\n" + "="*80)
    print("✅ SCRIPT FINISHED")
    print("="*80 + "\n")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("📂 SENTIMENT PROCESSING TEST RUNNER")
    print("="*80)
    
    try:
        run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()