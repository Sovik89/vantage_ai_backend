# routers/dashboard.py
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from config import PROJECT_ID, BQ_DATASET


from google.cloud import bigquery
router = APIRouter()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_empty_stats(days: int) -> Dict[str, Any]:
    """Return empty stats for new users or when no data is available"""
    return {
        "stats": {
            "documents": {
                "total": 0,
                "change_percentage": None
            },
            "sentiment": {
                "total_jobs": 0,
                "completed": 0,
                "processing": 0,
                "failed": 0
            },
            "ats": {
                "total_jobs": 0,
                "completed": 0,
                "processing": 0,
                "total_candidates": 0
            }
        },
        "recent_activity": [],
        "insights": [
            {
                "type": "welcome",
                "message": "Welcome! Start by uploading documents or analyzing sentiment.",
                "severity": "info"
            }
        ],
        "period_days": days
    }

try:
    bq_client = bigquery.Client()
    logger.info("Successfully initialized BigQuery client")
except Exception as e:
    logger.error(f"Failed to initialize BigQuery client: {str(e)}")
    bq_client = None  # We'll handle this in the endpoint
    
# Helper functions for fetching stats
def fetch_document_stats(user_email: str, cutoff_date: datetime.date) -> Dict[str, Any]:
    """Fetch document statistics with week-over-week change"""
    try:
        query = f"""
            SELECT 
                COUNT(DISTINCT pdf_name) as doc_count,
                COUNT(DISTINCT CASE WHEN DATE(created_at) >= DATE_SUB(@cutoff_date, INTERVAL 7 DAY) 
                    THEN pdf_name END) as recent_count
            FROM `{PROJECT_ID}.{BQ_DATASET}.journal_vectors`
            WHERE user_email = @user_email
            AND DATE(created_at) >= @cutoff_date
        """
        
        result = bq_client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                    bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date)
                ]
            )
        ).result()
        
        row = list(result)[0]
        total = row.doc_count or 0
        recent = row.recent_count or 0
        change = ((total - recent) / recent * 100) if recent > 0 else None
        
        return {
            "total": total,
            "change_percentage": change
        }
    except Exception as e:
        logger.error(f"Error fetching document stats: {str(e)}")
        return {"total": 0, "change_percentage": None}

def fetch_sentiment_stats(user_email: str, cutoff_date: datetime.date) -> Dict[str, Any]:
    """Fetch sentiment analysis statistics"""
    try:
        query = f"""
            SELECT 
                COUNT(*) as total_jobs,
                COUNTIF(status = 'COMPLETED') as completed_jobs,
                COUNTIF(status = 'PROCESSING') as processing_jobs,
                COUNTIF(status = 'FAILED') as failed_jobs
            FROM `{PROJECT_ID}.{BQ_DATASET}.sentiment_jobs`
            WHERE user_email = @user_email
            AND DATE(created_at) >= @cutoff_date
        """
        
        result = bq_client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                    bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date)
                ]
            )
        ).result()
        
        row = list(result)[0]
        return {
            "total_jobs": row.total_jobs or 0,
            "completed": row.completed_jobs or 0,
            "processing": row.processing_jobs or 0,
            "failed": row.failed_jobs or 0
        }
    except Exception as e:
        logger.error(f"Error fetching sentiment stats: {str(e)}")
        return {
            "total_jobs": 0,
            "completed": 0,
            "processing": 0,
            "failed": 0
        }

def fetch_ats_stats(user_email: str, cutoff_date: datetime.date) -> Dict[str, Any]:
    """Fetch ATS check statistics"""
    try:
        query = f"""
            SELECT 
                COUNT(*) as total_jobs,
                COUNTIF(status = 'COMPLETED') as completed_jobs,
                COUNTIF(status = 'PROCESSING') as processing_jobs,
                SUM(total_candidates_analyzed) as total_candidates
            FROM `{PROJECT_ID}.{BQ_DATASET}.ats_jobs`
            WHERE user_email = @user_email
            AND DATE(created_at) >= @cutoff_date
        """
        
        result = bq_client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                    bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date)
                ]
            )
        ).result()
        
        row = list(result)[0]
        return {
            "total_jobs": row.total_jobs or 0,
            "completed": row.completed_jobs or 0,
            "processing": row.processing_jobs or 0,
            "total_candidates": row.total_candidates or 0
        }
    except Exception as e:
        logger.error(f"Error fetching ATS stats: {str(e)}")
        return {
            "total_jobs": 0,
            "completed": 0,
            "processing": 0,
            "total_candidates": 0
        }

def fetch_recent_activities(user_email: str, cutoff_date: datetime.date) -> list:
    """Fetch recent user activities"""
    try:
        # Handle activities when no session data is available yet
        if user_email == 'tester@example.com':
            return [{
                "type": "welcome",
                "description": "Welcome to the test environment",
                "timestamp": datetime.now().isoformat(),
                "job_id": "test-session"
            }]

        query = f"""
            SELECT 
                session_type as type,
                COALESCE(query_text, 'No description') as description,
                CAST(created_at as STRING) as timestamp,
                CAST(job_id as STRING) as job_id
            FROM `{PROJECT_ID}.{BQ_DATASET}.sessions`
            WHERE user_email = @user_email
            AND DATE(created_at) >= @cutoff_date
            ORDER BY created_at DESC
            LIMIT 10
        """
        
        result = bq_client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                    bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date)
                ]
            )
        ).result()
        
        activities = []
        for row in result:
            activities.append({
                "type": row.session_type,
                "description": row.query_text,
                "timestamp": row.created_at.isoformat(),
                "job_id": row.job_id
            })
        return activities
    except Exception as e:
        logger.error(f"Error fetching activities: {str(e)}")
        return []

def generate_insights(docs: Dict[str, Any], sentiment: Dict[str, Any], ats: Dict[str, Any]) -> list:
    """Generate insights based on user activity"""
    insights = []
    
    if docs["total"] == 0 and sentiment["total_jobs"] == 0 and ats["total_jobs"] == 0:
        insights.append({
            "type": "welcome",
            "message": "Welcome! Start by uploading documents or analyzing sentiment.",
            "severity": "info"
        })
    else:
        if docs["total"] > 0:
            insights.append({
                "type": "documents",
                "message": f"You have analyzed {docs['total']} documents",
                "severity": "info"
            })
        
        if sentiment["processing"] > 0:
            insights.append({
                "type": "sentiment",
                "message": f"{sentiment['processing']} sentiment analyses in progress",
                "severity": "info"
            })
            
        if ats["processing"] > 0:
            insights.append({
                "type": "ats",
                "message": f"{ats['processing']} ATS checks in progress",
                "severity": "info"
            })
    
    return insights

@router.get("/stats")
async def get_dashboard_stats(
    user_email: str = Query(...),
    days: int = Query(40, ge=1, le=90)  # Last N days
) -> Dict[str, Any]:
    """Get aggregated dashboard statistics"""
    try:
        logger.info(f"Getting dashboard stats for user {user_email}, days: {days}")
        
        if not bq_client:
            logger.warning("No BigQuery client available")
            return get_empty_stats(days)
            
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        # Test BigQuery connection
        try:
            bq_client.query("SELECT 1").result()
        except Exception as e:
            logger.error(f"BigQuery connection failed: {str(e)}")
            return get_empty_stats(days)
            
        # Document stats with change calculation
        docs = fetch_document_stats(user_email, cutoff_date)
        sentiment = fetch_sentiment_stats(user_email, cutoff_date)
        ats = fetch_ats_stats(user_email, cutoff_date)
        activities = fetch_recent_activities(user_email, cutoff_date)
        insights = generate_insights(docs, sentiment, ats)
        
        return {
            "stats": {
                "documents": docs,
                "sentiment": sentiment,
                "ats": ats
            },
            "recent_activity": activities,
            "insights": insights,
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Error in dashboard stats: {str(e)}")
        return get_empty_stats(days)
    
    journal_result = bq_client.query(
        journal_query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date)
            ]
        )
    ).result()
    
    # Mock data for development
    return {
        "stats": {
            "documents": {
                "total": 25,
                "change_percentage": 15
            },
            "sentiment": {
                "total_jobs": 50,
                "completed": 45,
                "processing": 3,
                "failed": 2
            },
            "ats": {
                "total_jobs": 30,
                "completed": 28,
                "processing": 2,
                "total_candidates": 150
            }
        },
        "recent_activity": [
            {
                "type": "journal",
                "description": "Analyzed performance review document",
                "timestamp": datetime.now().isoformat(),
                "job_id": "test-1"
            }
        ],
        "insights": [
            {
                "type": "general",
                "message": "System working in test mode",
                "severity": "info"
            }
        ],
        "period_days": days
    }
    
    # 2. Sentiment Analysis Stats
    sentiment_query = f"""
        SELECT 
            COUNT(*) as total_jobs,
            COUNTIF(status = 'COMPLETED') as completed_jobs,
            COUNTIF(status = 'PROCESSING') as processing_jobs,
            COUNTIF(status = 'FAILED') as failed_jobs
        FROM `{PROJECT_ID}.{BQ_DATASET}.sentiment_jobs`
        WHERE user_email = @user_email
        AND DATE(created_at) >= @cutoff_date
    """
    
    sentiment_result = bq_client.query(
        sentiment_query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date)
            ]
        )
    ).result()
    
    sentiment_row = list(sentiment_result)[0]
    
    # 3. ATS Stats
    ats_query = f"""
        SELECT 
            COUNT(*) as total_jobs,
            COUNTIF(status = 'COMPLETED') as completed_jobs,
            COUNTIF(status = 'PROCESSING') as processing_jobs,
            SUM(total_candidates_analyzed) as total_candidates
        FROM `{PROJECT_ID}.{BQ_DATASET}.ats_jobs`
        WHERE user_email = @user_email
        AND DATE(created_at) >= @cutoff_date
    """
    
    ats_result = bq_client.query(
        ats_query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date)
            ]
        )
    ).result()
    
    ats_row = list(ats_result)[0]
    
    # 4. Recent Activity (from sessions table)
    activity_query = f"""
        SELECT 
            session_type,
            query_text,
            created_at,
            job_id
        FROM `{PROJECT_ID}.{BQ_DATASET}.sessions`
        WHERE user_email = @user_email
        ORDER BY created_at DESC
        LIMIT 10
    """
    
    activity_result = bq_client.query(
        activity_query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_email", "STRING", user_email)
            ]
        )
    ).result()
    
    recent_activities = [
        {
            "type": row.session_type,
            "description": _format_activity_description(row.session_type, row.query_text),
            "timestamp": row.created_at.isoformat(),
            "job_id": row.job_id
        }
        for row in activity_result
    ]
    
    # 5. Quick Insights
    insights = []
    
    # Sentiment insight
    if sentiment_row.completed_jobs > 0:
        avg_sentiment_query = f"""
            SELECT AVG(sentiment_index) as avg_sentiment
            FROM `{PROJECT_ID}.{BQ_DATASET}.sentiment_results`
            WHERE user_email = @user_email
            AND unit_level = 'doc'
            AND DATE(created_at) >= @cutoff_date
        """
        avg_sentiment_result = bq_client.query(
            avg_sentiment_query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                    bigquery.ScalarQueryParameter("cutoff_date", "DATE", cutoff_date)
                ]
            )
        ).result()
        
        avg_sentiment = list(avg_sentiment_result)[0].avg_sentiment
        if avg_sentiment is not None:
            sentiment_label = "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "neutral"
            insights.append({
                "type": "sentiment",
                "message": f"Average employee sentiment is {sentiment_label} ({avg_sentiment:.2f})",
                "severity": "info" if avg_sentiment > 0 else "warning"
            })
    
    # ATS insight
    if ats_row.completed_jobs > 0:
        insights.append({
            "type": "ats",
            "message": f"Screened {ats_row.total_candidates or 0} candidates across {ats_row.completed_jobs} positions",
            "severity": "info"
        })
    
    return {
        "stats": {
            "documents": {
                "total": doc_count,
                "change_percentage": None  # Could calculate week-over-week
            },
            "sentiment": {
                "total_jobs": sentiment_row.total_jobs,
                "completed": sentiment_row.completed_jobs,
                "processing": sentiment_row.processing_jobs,
                "failed": sentiment_row.failed_jobs
            },
            "ats": {
                "total_jobs": ats_row.total_jobs,
                "completed": ats_row.completed_jobs,
                "processing": ats_row.processing_jobs,
                "total_candidates": ats_row.total_candidates or 0
            }
        },
        "recent_activity": recent_activities,
        "insights": insights,
        "period_days": days
    }

def _format_activity_description(session_type: str, query_text: str) -> str:
    """Format activity description for UI"""
    type_labels = {
        "journal_query": "Queried HR documents",
        "sentiment_analysis": "Analyzed employee sentiment",
        "ats_screening": "Screened candidates"
    }
    
    action = type_labels.get(session_type, "Performed analysis")
    
    if query_text and len(query_text) > 50:
        query_text = query_text[:47] + "..."
    
    return f"{action}: {query_text}" if query_text else action

# Don't forget to register this router in main.py!
# app.include_router(dashboard.router)