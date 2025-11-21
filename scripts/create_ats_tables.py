# scripts/create_ats_tables.py
"""
Create ATS BigQuery Tables
Run this once to set up the database schema
"""

import os
import sys

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from google.cloud import bigquery
import config

def create_ats_tables():
    """
    Create ATS tables in BigQuery
    """
    
    client = bigquery.Client(project=config.PROJECT_ID)
    dataset_id = f"{config.PROJECT_ID}.{config.BQ_DATASET}"
    
    print("\n" + "="*80)
    print("🔧 CREATING ATS BIGQUERY TABLES")
    print("="*80 + "\n")
    
    print(f"Project: {config.PROJECT_ID}")
    print(f"Dataset: {config.BQ_DATASET}")
    print(f"Location: {config.LOCATION}\n")
    
    # Ensure dataset exists
    try:
        client.get_dataset(dataset_id)
        print(f"✅ Dataset '{config.BQ_DATASET}' exists\n")
    except Exception:
        print(f"⚠️  Dataset '{config.BQ_DATASET}' not found. Creating...")
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = config.LOCATION
        client.create_dataset(dataset, timeout=30)
        print(f"✅ Created dataset '{config.BQ_DATASET}'\n")
    
    # Table 1: ats_jobs
    print("📋 Creating table: ats_jobs")
    print("-" * 80)
    
    ats_jobs_schema = [
        bigquery.SchemaField("job_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("position_title", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("organization", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("user_email", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("total_candidates_analyzed", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("completed_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("record_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("record_date_str", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("report_url", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("error_message", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("meta", "STRING", mode="NULLABLE"),
    ]
    
    table_id = f"{dataset_id}.ats_jobs"
    
    try:
        client.get_table(table_id)
        print(f"✅ Table 'ats_jobs' already exists\n")
    except Exception:
        table = bigquery.Table(table_id, schema=ats_jobs_schema)
        table.description = "ATS job metadata - tracks analysis jobs (NO candidate PII)"
        client.create_table(table)
        print(f"✅ Created table 'ats_jobs'")
        print(f"   - Fields: {len(ats_jobs_schema)}")
        print(f"   - Description: Job metadata only\n")
    
    # Table 2: ats_results
    print("📊 Creating table: ats_results")
    print("-" * 80)
    
    ats_results_schema = [
        bigquery.SchemaField("result_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("job_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("record_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("record_date_str", "STRING", mode="NULLABLE"),
        
        # Aggregated Statistics
        bigquery.SchemaField("total_candidates", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("avg_match_percentage", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("median_match_percentage", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("max_match_percentage", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("min_match_percentage", "FLOAT", mode="NULLABLE"),
        
        # Match Distribution
        bigquery.SchemaField("high_match_count", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("medium_match_count", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("low_match_count", "INTEGER", mode="NULLABLE"),
        
        # Skills Analysis (Aggregated)
        bigquery.SchemaField("avg_skills_match", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("most_common_missing_skills", "STRING", mode="REPEATED"),
        bigquery.SchemaField("most_common_found_skills", "STRING", mode="REPEATED"),
        
        # Experience Analysis
        bigquery.SchemaField("avg_experience_match", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("avg_candidate_experience_years", "FLOAT", mode="NULLABLE"),
        
        # AI Detection Summary
        bigquery.SchemaField("ai_generated_detected_count", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("avg_ai_probability", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("high_ai_risk_count", "INTEGER", mode="NULLABLE"),
        
        # Technical & Domain
        bigquery.SchemaField("avg_technical_depth", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("avg_domain_relevance", "FLOAT", mode="NULLABLE"),
        
        # Bias Detection
        bigquery.SchemaField("total_bias_flags", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("bias_types_detected", "STRING", mode="REPEATED"),
        
        # Key Insights
        bigquery.SchemaField("common_strengths", "STRING", mode="REPEATED"),
        bigquery.SchemaField("common_gaps", "STRING", mode="REPEATED"),
        bigquery.SchemaField("key_recommendations", "STRING", mode="REPEATED"),
        
        # Summary
        bigquery.SchemaField("analysis_summary", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("meta", "STRING", mode="NULLABLE"),
    ]
    
    table_id = f"{dataset_id}.ats_results"
    
    try:
        client.get_table(table_id)
        print(f"✅ Table 'ats_results' already exists\n")
    except Exception:
        table = bigquery.Table(table_id, schema=ats_results_schema)
        table.description = "ATS aggregated results - NO PII, only statistics and patterns"
        client.create_table(table)
        print(f"✅ Created table 'ats_results'")
        print(f"   - Fields: {len(ats_results_schema)}")
        print(f"   - Description: Aggregated analytics only\n")
    
    # Check journal_vectors table
    print("📚 Checking shared table: journal_vectors")
    print("-" * 80)
    
    journal_table_id = f"{dataset_id}.journal_vectors"
    
    try:
        table = client.get_table(journal_table_id)
        print(f"✅ Table 'journal_vectors' exists")
        print(f"   - Will be used for ATS learning insights")
        print(f"   - Current rows: {table.num_rows:,}\n")
    except Exception:
        print(f"⚠️  Table 'journal_vectors' not found")
        print(f"   - Should be created by sentiment analysis setup")
        print(f"   - ATS learning insights will be stored here\n")
    
    # Summary
    print("="*80)
    print("✅ ATS TABLES SETUP COMPLETE")
    print("="*80)
    print("\n📋 Summary:")
    print(f"   ✅ ats_jobs - Job metadata")
    print(f"   ✅ ats_results - Aggregated analytics (NO PII)")
    print(f"   ✅ journal_vectors - Learning insights (shared)")
    print("\n🔒 Privacy Compliance:")
    print(f"   ✅ NO candidate names stored")
    print(f"   ✅ NO candidate emails stored")
    print(f"   ✅ NO candidate phone numbers stored")
    print(f"   ✅ Only aggregated statistics retained")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 ATS BIGQUERY SETUP")
    print("="*80 + "\n")
    
    # Check credentials
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set!")
        print("   Set it with: $env:GOOGLE_APPLICATION_CREDENTIALS='path/to/key.json'")
        sys.exit(1)
    elif not os.path.exists(creds):
        print(f"❌ Credentials file not found: {creds}")
        sys.exit(1)
    else:
        print(f"✅ Using credentials: {creds}\n")
    
    try:
        create_ats_tables()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)