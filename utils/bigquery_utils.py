import config
from google.cloud import bigquery
from datetime import datetime

# --- BigQuery Client Initialization ---
client = bigquery.Client(project=config.PROJECT_ID)

# --- Table Definitions ---
SUMMARIES_TABLE_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}.journal_summaries"
VECTORS_TABLE_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}.journal_vectors"
SESSIONS_TABLE_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}.sessions"
DATASET_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}"



# --- Hash-based Deduplication ---
def check_hash_exists(file_hash: str) -> bool:
    """
    Checks if a file with the given SHA256 hash already exists in the database.
    This is the primary method for content-based deduplication.
    """
    query = f"""
        SELECT EXISTS (
            SELECT 1
            FROM `{VECTORS_TABLE_ID}`
            WHERE file_hash = @hash
            LIMIT 1
        )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("hash", "STRING", file_hash)
        ]
    )
    try:
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()
        # The result of an EXISTS query is a single row with a single boolean value.
        return next(results)[0]
    except Exception as e:
        print(f"❌ Error checking hash existence: {e}")
        # Fail safe: assume it doesn't exist to allow processing, but log the error.
        return False


# --- Data Insertion for Summaries Table ---
def insert_summary(record: dict):
    """
    Insert a structured record, including the file_hash, into the summaries table.
    """
    # Ensure all required fields are present, especially the new file_hash
    if 'file_hash' not in record:
        print("❌ Error: file_hash is missing from the record for insert_summary.")
        return
    
    errors = client.insert_rows_json(SUMMARIES_TABLE_ID, [record])
    if errors:
        print(f"❌ Error inserting summary rows: {errors}")
    else:
        print(f"✅ Inserted summary for {record.get('pdf_name')} successfully into BigQuery.")


# --- Session Logging ---
def insert_session_log(log: dict):
    """
    Inserts a conversation turn into the sessions table.
    """
    row = {
        "session_id": log.get("session_id"),
        "email_id": log.get("email_id"),
        "query": log.get("query"),
        "response": log.get("response"),
        "source": log.get("source"),
        "created_at": datetime.now().isoformat()
    }
    errors = client.insert_rows_json(SESSIONS_TABLE_ID, [row])
    if errors:
        print(f"❌ Error inserting session log: {errors}")
    else:
        print(f"✅ Logged query for {log.get('email_id')}")


def fetch_session_logs_from_db(email_id: str, session_id: str = None):
    """
    Fetch conversation logs for a given email_id (optionally filter by session_id).
    Returns list of dicts.
    """
    if session_id:
        query = f"""
            SELECT session_id, email_id, query, response, source, created_at
            FROM `{SESSIONS_TABLE_ID}`
            WHERE email_id = @eid AND session_id = @sid
            ORDER BY created_at ASC
        """
        params = [
            bigquery.ScalarQueryParameter("eid", "STRING", email_id),
            bigquery.ScalarQueryParameter("sid", "STRING", session_id),
        ]
    else:
        query = f"""
            SELECT session_id, email_id, query, response, source, created_at
            FROM `{SESSIONS_TABLE_ID}`
            WHERE email_id = @eid
            ORDER BY created_at ASC
        """
        params = [bigquery.ScalarQueryParameter("eid", "STRING", email_id)]

    job_config = bigquery.QueryJobConfig(query_parameters=params)
    rows = client.query(query, job_config=job_config).result()

    return [
        {
            "session_id": r.session_id,
            "email_id": r.email_id,
            "query": r.query,
            "response": r.response,
            "source": r.source,
            "created_at": r.created_at.isoformat()
            if hasattr(r.created_at, "isoformat")
            else str(r.created_at),
        }
        for r in rows
    ]
    
def get_existing_summary(file_hash: str):
    """Retrieve the summary of an existing document by its hash"""
    query = f"""
    SELECT summary
    FROM `{DATASET_ID}.journal_vectors`
    WHERE file_hash = @file_hash
    LIMIT 1
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("file_hash", "STRING", file_hash)
        ]
    )
    
    try:
        results = client.query(query, job_config=job_config).result()
        for row in results:
            return row.summary
    except Exception as e:
        print(f"⚠️ Error retrieving existing summary: {e}")
        return None

