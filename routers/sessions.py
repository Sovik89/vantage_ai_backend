# routers/sessions.py

from fastapi import APIRouter, HTTPException, Query
from google.cloud import bigquery
import config

router = APIRouter()
bq_client = bigquery.Client(project=config.PROJECT_ID)

@router.get("/user/{user_email}")
async def get_user_sessions(
    user_email: str,
    #organization_id: str = Query(...), # Uncomment if org_id filtering is needed
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get all sessions for a user across all modules
    
    Returns combined list of:
    - Journal uploads
    - Sentiment jobs
    - ATS jobs
    """
    
    try:
        # 1. Normal Query 
        normal_query = f"""
        SELECT DISTINCT
            'query' as module,
            session_id,
            created_at,
            COUNT(*) as files_count
        FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.sessions`
        WHERE email_id = @user_email
        -- AND organization_id = @org_id
        GROUP BY session_id, created_at
        ORDER BY created_at DESC
        LIMIT @limit OFFSET @offset
        """
        
        # 2. Query sentiment sessions
        sentiment_query = f"""
        SELECT
            'sentiment' as module,
            job_id as session_id,
            status,
            created_at,
            updated_at
        FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_jobs`
        WHERE user_email = @user_email
        AND status = 'COMPLETED'
        --  AND organization_id = @org_id
        ORDER BY created_at DESC
        LIMIT @limit OFFSET @offset
        """
        
        # 3. Query ATS sessions
        ats_query = f"""
        SELECT
            'ats' as module,
            job_id as session_id,
            status,
            created_at,
            updated_at
        FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.ats_jobs`
        WHERE user_email = @user_email
        AND status = 'COMPLETED'
        --  AND organization_id = @org_id
        ORDER BY created_at DESC
        LIMIT @limit OFFSET @offset
        """
        
        # Execute all queries
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                #bigquery.ScalarQueryParameter("org_id", "STRING", organization_id),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
                bigquery.ScalarQueryParameter("offset", "INT64", offset)
            ]
        )
        
        query_sessions = list(bq_client.query(normal_query, job_config=job_config).result())
        sentiment_sessions = list(bq_client.query(sentiment_query, job_config=job_config).result())
        ats_sessions = list(bq_client.query(ats_query, job_config=job_config).result())
        
        # Merge and sort by created_at
        all_sessions = []
        
        for row in query_sessions:
            all_sessions.append({
                "session_id": row.session_id,
                "module": "query",
                "created_at": row.created_at.isoformat(),
                "files_count": row.files_count
            })
        
        for row in sentiment_sessions:
            all_sessions.append({
                "session_id": row.session_id,
                "module": "sentiment",
                "status": row.status,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            })
        
        for row in ats_sessions:
            all_sessions.append({
                "session_id": row.session_id,
                "module": "ats",
                "status": row.status,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            })
        
        # Sort by created_at descending
        all_sessions.sort(key=lambda x: x['created_at'], reverse=True)
        
        return {
            "user_email": user_email,
            #"organization_id": organization_id, #will be added if needed
            "total_sessions": len(all_sessions),
            "sessions": all_sessions[:limit]
        }
        
    except Exception as e:
        print(f"Error fetching user sessions: {e}")
        raise HTTPException(500, "Failed to fetch sessions")


@router.get("/org/{organization_id}")
async def get_org_sessions(
    organization_id: str,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get all sessions for an organization
    Similar to get_user_sessions but without user_email filter
    """
    # Similar implementation, just remove user_email filter
    pass


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_email: str = Query(...)
):
    """
    Delete a session and all associated data
    We only delete user from sessions but not the vectors or results tables
    This is DESTRUCTIVE - use with caution!
    """
    
    try:
        deleted_items = {
            "journal_vectors": 0,
            "sentiment_results": 0,
            "ats_results": 0
        }
        
        # 1. Delete from journal_vectors
        delete_journal = f"""
        DELETE FROM `{config.PROJECT_ID}.{config.BQ_DATASET}.sessions`
        WHERE session_id = @session_id
          AND email_id = @user_email
        """
        
        job = bq_client.query(
            delete_journal,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
                    bigquery.ScalarQueryParameter("user_email", "STRING", user_email)
                ]
            )
        )
        job.result()
        deleted_items["journal_vectors"] = job.num_dml_affected_rows
        
        # 2. Delete from sentiment (if applicable)
        # Note: We don't delete sentiment_results as they're valuable historical data
        # But we can mark the job as deleted
        
        # 3. Delete from ATS (similar approach)
        
        return {
            "message": "User Query Session deleted successfully",
            "session_id": session_id,
            "deleted_items": deleted_items
        }
        
    except Exception as e:
        print(f"Error deleting session: {e}")
        raise HTTPException(500, "Failed to delete session")