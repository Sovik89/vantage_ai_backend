# worker/worker_app.py
import os
import sys
import base64
import json
import traceback
from fastapi import FastAPI, Request
from google.cloud import bigquery

# make repo root importable so we can reuse utils in repo
# worker/ is at: <repo root>/worker -> append repo root
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)

# now imports from your repo should work
import worker.sentiment_processing_old as sentiment_processing_old  # local worker module in worker/ that imports utils

import config

app = FastAPI()
PROJECT = config.PROJECT_ID
DATASET = config.BQ_DATASET
bq = bigquery.Client(project=PROJECT)

def update_job(job_id, **kwargs):
    sets = []
    for k, v in kwargs.items():
        if v is None:
            continue
        if isinstance(v, str):
            val = v.replace("'", "\\'")
            sets.append(f"{k} = '{val}'")
        else:
            sets.append(f"{k} = {json.dumps(v)}")
    if not sets:
        return
    sql = f"UPDATE `{PROJECT}.{DATASET}.sentiment_jobs` SET {', '.join(sets)} WHERE job_id = '{job_id}'"
    bq.query(sql).result()

@app.post("/pubsub/push")
async def pubsub_push(req: Request):
    body = await req.json()
    try:
        message = body.get("message", {})
        if "data" not in message:
            return {"status":"ignored","reason":"no data"}
        payload = json.loads(base64.b64decode(message["data"]).decode("utf-8"))
        job_id = payload.get("job_id")
        gcs_path = payload.get("file_gcs_path")
        if not job_id or not gcs_path:
            return {"status":"invalid","reason":"missing job_id or file_gcs_path"}

        # idempotency check: skip if already completed
        q = f"SELECT status FROM `{PROJECT}.{DATASET}.sentiment_jobs` WHERE job_id = @job_id LIMIT 1"
        job_res = bq.query(q, job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("job_id","STRING",job_id)]
        )).result()
        rows = list(job_res)
        if rows and dict(rows[0])["status"] == "COMPLETED":
            return {"status":"skipped","reason":"already completed"}

        update_job(job_id, status="RUNNING", progress=0.01)

        # process the job (the heavy lifting is in sentiment_processing.process_job)
        result_row_id, summary = sentiment_processing_old.process_job(payload)

        update_job(job_id, status="COMPLETED", progress=1.0, result_row_id=result_row_id)
        return {"status":"ok", "result": result_row_id}
    except Exception as e:
        traceback.print_exc()
        job_id = locals().get("job_id", None)
        if job_id:
            update_job(job_id, status="FAILED", error_message=str(e))
        return {"status":"error", "error": str(e)}
