# routers/sentiment_jobs.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.cloud import pubsub_v1, bigquery
from datetime import datetime
import uuid, json, os

import config  # must provide PROJECT_ID, BQ_DATASET, PUBSUB_TOPIC

router = APIRouter(prefix="/agents/sentiment", tags=["sentiment-jobs"])

PROJECT = config.PROJECT_ID
DATASET = config.BQ_DATASET
PUBSUB_TOPIC = getattr(config, "PUBSUB_TOPIC", f"projects/{PROJECT}/topics/sentiment-jobs")

bq = bigquery.Client(project=PROJECT)
publisher = pubsub_v1.PublisherClient()

class SubmitJobRequest(BaseModel):
    file_gcs_path: str  # or ingestion_id
    user_email: str
    organization_id: str = "guest_org"
    notify_email: bool = True
    run_options: dict = {}

@router.post("/submit-job")
def submit_job(req: SubmitJobRequest):
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    row = {
        "job_id": job_id,
        "ingestion_id": req.file_gcs_path,
        "created_at": now,
        "record_date": datetime.utcnow().date().isoformat(),
        "organization_id": req.organization_id,
        "user_email": req.user_email,
        "status": "PENDING",
        "progress": 0.0,
        "total_items": None,
        "processed_items": 0,
        "result_row_id": None,
        "report_url": None,
        "error_message": None,
        "meta": json.dumps({"notify_email": req.notify_email, "run_options": req.run_options})
    }

    # write job metadata to BigQuery
    table = f"{PROJECT}.{DATASET}.sentiment_jobs"
    try:
        bq.insert_rows_json(table, [row])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write job metadata: {e}")

    # publish to Pub/Sub (worker will pick up)
    payload = json.dumps({
        "job_id": job_id,
        "file_gcs_path": req.file_gcs_path,
        "organization_id": req.organization_id,
        "user_email": req.user_email,
        "run_options": req.run_options
    }).encode("utf-8")
    try:
        publisher.publish(PUBSUB_TOPIC, payload)
    except Exception as e:
        # best-effort: job metadata exists, but publishing failed
        return {"job_id": job_id, "status": "PENDING", "warning": f"publish failed: {e}"}

    return {"job_id": job_id, "status": "PENDING"}

@router.get("/job/{job_id}")
def get_job_status(job_id: str):
    table = f"{PROJECT}.{DATASET}.sentiment_jobs"
    sql = f"SELECT job_id, status, progress, total_items, processed_items, result_row_id, error_message FROM `{table}` WHERE job_id = @job_id LIMIT 1"
    job = bq.query(sql, job_config=bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("job_id", "STRING", job_id)]
    )).result()
    rows = list(job)
    if not rows:
        raise HTTPException(status_code=404, detail="Job not found")
    r = dict(rows[0])
    return r
