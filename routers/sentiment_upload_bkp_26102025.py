# routers/sentiment_upload.py
import uuid
import io
import json
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from google.cloud import storage, pubsub_v1, bigquery
from datetime import datetime
import config

# adjust import if your project structure differs
from worker import sentiment_processing_old

router = APIRouter(prefix="/agents/sentiment", tags=["sentiment"])

# clients (reuse across requests)
_storage = storage.Client(project=config.PROJECT_ID)
_publisher = pubsub_v1.PublisherClient()
_bq = bigquery.Client(project=config.PROJECT_ID)

def _upload_to_gcs(bucket_name: str, job_id: str, file: UploadFile):
    bucket = _storage.bucket(bucket_name)
    safe_name = file.filename.replace(" ", "_")
    blob_path = f"sentiment-jobs/{job_id}/{safe_name}"
    blob = bucket.blob(blob_path)
    content = file.file.read()
    blob.upload_from_string(content, content_type=file.content_type)
    return f"gs://{bucket_name}/{blob_path}"

def _insert_job_row(job_id, gcs_path, domain, consent, user_email, organization_id="guest_org"):
    table = f"{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_jobs"
    now = datetime.utcnow().isoformat()
    row = {
        "job_id": job_id,
        "organization_id": organization_id,
        "user_email": user_email,
        "file_gcs_path": gcs_path,
        "domain": domain,
        "consent_to_email_verbatim": consent,
        "status": "PENDING",
        "created_at": now,
        "updated_at": now,
        "report_url": None,
        "meta": json.dumps({"created_by": user_email})
    }
    _bq.insert_rows_json(table, [row])
    return

@router.post("/submit-job-upload")
async def submit_job_upload(
    file: UploadFile = File(...),
    domain: str = Form(...),
    consent_to_email_verbatim: bool = Form(False),
    user_email: str = Form("guest_user@gmail.com"),
    organization_id: str = Form("guest_org")
):
    # basic validation
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xls/.xlsx supported")
    job_id = str(uuid.uuid4())
    gcs_path = _upload_to_gcs(config.SENTIMENT_BUCKET, job_id, file)
    _insert_job_row(job_id, gcs_path, domain, consent_to_email_verbatim, user_email, organization_id)

    # publish to Pub/Sub (async)
    payload = {
        "job_id": job_id,
        "file_gcs_path": gcs_path,
        "domain": domain,
        "consent": consent_to_email_verbatim,
        "user_email": user_email,
        "organization_id": organization_id
    }
    topic = _publisher.topic_path(config.PROJECT_ID, config.PUBSUB_TOPIC.split("/")[-1])
    _publisher.publish(topic, json.dumps(payload).encode("utf-8"))

    return {"job_id": job_id, "status": "PENDING", "gcs_path": gcs_path}

@router.post("/submit-job-sync")
async def submit_job_sync(
    file: UploadFile = File(...),
    domain: str = Form(...),
    consent_to_email_verbatim: bool = Form(False),
    user_email: str = Form("guest_user@gmail.com"),
    organization_id: str = Form("guest_org")
):
    # quick synchronous processing for small files (useful for tests)
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xls/.xlsx supported")
    job_id = str(uuid.uuid4())
    content = file.file.read()
    # calls process_job directly (in-process)
    payload = {
        "job_id": job_id,
        "file_bytes": content.hex(),  # pass bytes as hex to avoid binary issues
        "filename": file.filename,
        "domain": domain,
        "consent": consent_to_email_verbatim,
        "user_email": user_email,
        "organization_id": organization_id,
    }
    # Direct call - runs in the same process, beware long runtime
    result_id, summary = sentiment_processing_old.process_job(payload, sync_mode=True)
    return {"job_id": job_id, "result_id": result_id, "summary": summary}
