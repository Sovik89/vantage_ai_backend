# worker/sentiment_processing.py
import os
import json
import uuid
import hashlib
from datetime import datetime
from google.cloud import bigquery, storage
from utils.file_utils import extract_text_from_gcs, extract_text_from_bytes, sanitize_text
from utils.vertex_ai_utils import classify_texts_with_vertex
from utils.bias_utils import detect_bias_flags
import config
import io
import pandas as pd
import base64
try:
    from google.cloud import secretmanager
    _HAS_SECRET = True
except Exception:
    _HAS_SECRET = False

BQ = bigquery.Client(project=config.PROJECT_ID)
STORAGE = storage.Client(project=config.PROJECT_ID)

print("Storage and BQ clients initialized as:", STORAGE, BQ)

DEFAULT_ORG = "guest_org"
DEFAULT_USER = "guest_user@gmail.com"

def _hash_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()

def _write_aggregated_result(job_id, org_id, user_email, unit_level, total, pos, neu, neg, avg_conf, details):
    table = f"{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_results"
    now = datetime.utcnow().isoformat()
    result_id = str(uuid.uuid4())
    row = {
        "result_id": result_id,
        "job_id": job_id,
        "organization_id": org_id,
        "processed_by": "sentiment-agent-v1",
        "created_at": now,
        "unit_level": unit_level,
        "total_texts": total,
        "positive_count": pos,
        "neutral_count": neu,
        "negative_count": neg,
        "average_confidence": avg_conf,
        "details": details,
        "meta": json.dumps({"created_at": now})
    }
    BQ.insert_rows_json(table, [row])
    return result_id

#-----------------------------old upload function, commented out-------------------


# def _upload_report_to_gcs(df: pd.DataFrame, job_id: str):
#     bucket = STORAGE.bucket(config.SENTIMENT_BUCKET)
#     path = f"reports/sentiment-report-{job_id}.xlsx"
#     blob = bucket.blob(path)
#     out = io.BytesIO()
#     df.to_excel(out, index=False, engine="openpyxl")
#     blob.upload_from_string(out.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
#     # generate signed URL if environment allows; else return gs:// path
#     try:
#         url = blob.generate_signed_url(version="v4", expiration=3600)
#         return url
#     except Exception:
#         return f"gs://{config.SENTIMENT_BUCKET}/{path}"

#-----------------------------new upload function, with public read access-------------------

def _upload_report_to_gcs(df: pd.DataFrame, job_id: str):
    """
    Uploads the report to configured GCS bucket.
    Defensive: checks existence, optionally creates the bucket, and falls back to local file on error.
    Returns: URL string (signed url if available else gs:// path or file:// local fallback)
    """
    bucket_name = getattr(config, "SENTIMENT_BUCKET", None) or getattr(config, "GCS_BUCKET", None)
    if not bucket_name:
        print("ERROR: No SENTIMENT_BUCKET or GCS_BUCKET configured in config.py")
        # fallback local write
        out_dir = os.path.abspath("local_reports")
        os.makedirs(out_dir, exist_ok=True)
        fpath = os.path.join(out_dir, f"sentiment-report-{job_id}.xlsx")
        df.to_excel(fpath, index=False, engine="openpyxl")
        return f"file://{fpath}"

    try:
        # Try to get bucket; this does not necessarily validate existence on server, so test blob upload
        bucket = STORAGE.bucket(bucket_name)

        # Optional: if you want the code to create bucket when missing,
        # set config.CREATE_BUCKET_IF_MISSING = True in config.py
        if getattr(config, "CREATE_BUCKET_IF_MISSING", False):
            if not bucket.exists():
                print(f"INFO: Bucket {bucket_name} does not exist. Creating it in location {config.LOCATION} ...")
                STORAGE.create_bucket(bucket_name, location=config.LOCATION)
                bucket = STORAGE.bucket(bucket_name)

        # Prepare the path
        path = f"reports/sentiment-report-{job_id}.xlsx"
        blob = bucket.blob(path)
        out = io.BytesIO()
        df.to_excel(out, index=False, engine="openpyxl")
        # Upload
        blob.upload_from_string(out.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        # Try to generate signed URL (best-effort)
        try:
            url = blob.generate_signed_url(version="v4", expiration=3600)
            return url
        except Exception as e:
            # Signed URL failed — return gs:// path
            print(f"INFO: generate_signed_url failed: {e}. Returning gs:// path.")
            return f"gs://{bucket_name}/{path}"

    except Exception as e:
        # On any failure, persist locally as fallback (so pipeline doesn't break)
        print(f"ERROR: _upload_report_to_gcs failed for bucket {bucket_name}: {e}")
        out_dir = os.path.abspath("local_reports")
        os.makedirs(out_dir, exist_ok=True)
        fpath = os.path.join(out_dir, f"sentiment-report-{job_id}.xlsx")
        try:
            df.to_excel(fpath, index=False, engine="openpyxl")
            print("DEBUG: Wrote local fallback report to", fpath)
            return f"file://{fpath}"
        except Exception as e2:
            print("CRITICAL: also failed to write local fallback report:", e2)
            # Final fallback: return a simple path string
            return f"file://{os.path.join('local_reports','sentiment-report-{job_id}.xlsx')}"
#-----------------------------end new upload function-------------------

def _get_sendgrid_key():
    if hasattr(config, "SENDGRID_API_KEY") and config.SENDGRID_API_KEY:
        return config.SENDGRID_API_KEY
    if _HAS_SECRET and hasattr(config, "SENDGRID_SECRET_NAME"):
        client = secretmanager.SecretManagerServiceClient()
        name = config.SENDGRID_SECRET_NAME  # e.g. projects/..../secrets/SENDGRID_API_KEY/versions/latest
        res = client.access_secret_version(name=name)
        return res.payload.data.decode("utf-8")
    return None

def _send_email_with_link(to_email: str, url: str, subject: str, body_html: str):
    # Prefer SendGrid if key available, else log
    key = _get_sendgrid_key()
    if not key:
        print(f"[INFO] No SendGrid key configured. Would email {to_email} with link: {url}")
        return True
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        sg = SendGridAPIClient(key)
        message = Mail(from_email="no-reply@yourdomain.com", to_emails=to_email, subject=subject, html_content=f"{body_html}<p>Download: <a href='{url}'>Report</a></p>")
        resp = sg.send(message)
        print("Email sent:", resp.status_code)
        return resp.status_code < 300
    except Exception as e:
        print("Email error:", e)
        return False

def process_job(payload: dict, sync_mode: bool=False):
    """
    payload keys:
      - job_id
      - file_gcs_path OR (file_bytes hex + filename) when sync_mode=True
      - domain
      - consent (bool)
      - user_email
      - organization_id
    Returns: (result_id, summary_text)
    """
    print(f"DEBUG_PROCESS: start process_job job_id={payload.get('job_id')} sync_mode={sync_mode}")
    job_id = payload.get("job_id") or str(uuid.uuid4())
    domain = payload.get("domain", "general")
    consent = bool(payload.get("consent", False))
    user_email = payload.get("user_email", DEFAULT_USER)
    org_id = payload.get("organization_id", DEFAULT_ORG)

    # 1) Extract texts
    if sync_mode and payload.get("file_bytes"):
        file_bytes = bytes.fromhex(payload.get("file_bytes"))
        texts, row_idxs = extract_text_from_bytes(file_bytes, payload.get("filename", "upload.xlsx"))
    elif payload.get("file_gcs_path"):
        texts, row_idxs = extract_text_from_gcs(payload.get("file_gcs_path"))
    else:
        raise ValueError("No file source provided")

    if not texts:
        # nothing to process
        return None, "No text found"

    # 2) Sanitize depending on consent and domain rules
    processed_texts = []
    original_map = []  # (row_idx, original_text)
    for idx, t in zip(row_idxs, texts):
        sanitized, flags = sanitize_text(t, redact_names=(not consent or domain in ("interview_feedback","candidate_feedback")))
        processed_texts.append(sanitized if (consent or domain not in ("interview_feedback","candidate_feedback")) else sanitized)
        original_map.append((idx, sanitized, flags))

    # 3) Dedupe unique_texts
    hash_to_text = {}
    order_hashes = []
    for t in processed_texts:
        h = _hash_text(t)
        if h not in hash_to_text:
            hash_to_text[h] = t
        order_hashes.append(h)
    unique_hashes = list(hash_to_text.keys())
    unique_texts = [hash_to_text[h] for h in unique_hashes]

    # 4) Classify (batched)
    predictions = classify_texts_with_vertex(unique_texts, domain=domain, batch_size=32)
    # predictions align with unique_texts; build map h->pred
    h_to_pred = {}
    for h, pred in zip(unique_hashes, predictions):
        # pred: (label, conf, explanation, domain_fields)
        h_to_pred[h] = {
            "label": pred[0],
            "confidence": float(pred[1]),
            "explanation": pred[2],
            "domain_fields": pred[3] if len(pred) > 3 else {}
        }

    # 5) Map back to each original row and run bias detection
    processed_items = []
    pos = neu = neg = 0
    conf_sum = 0.0
    details_for_bq = []
    for i, h in enumerate(order_hashes):
        row_idx, text_snip, flags = original_map[i]
        pred = h_to_pred.get(h, {"label":"neutral","confidence":0.5,"explanation":"fallback","domain_fields":{}})
        label = pred["label"]
        conf = pred["confidence"]
        explanation = pred["explanation"]
        domain_fields = pred.get("domain_fields", {})
        bias_flags, bias_expl = detect_bias_flags(text_snip, domain)
        notes = []
        if conf < 0.55:
            notes.append("low_confidence")
        if label == "positive":
            pos += 1
        elif label == "negative":
            neg += 1
        else:
            neu += 1
        conf_sum += conf
        processed_items.append({
            "row_index": row_idx,
            "comment_hash": h,
            "text": text_snip if consent else (text_snip[:120] + ("..." if len(text_snip)>120 else "")),
            "include_full_text": consent,
            "label": label,
            "confidence": conf,
            "explanation": explanation,
            "domain_fields": domain_fields,
            "bias_flags": bias_flags,
            "bias_explanation": bias_expl,
            "sanitization": flags,
            "notes": notes
        })
        details_for_bq.append({
            "row_index": int(row_idx),
            "comment_hash": h,
            "text_snippet": (text_snip[:200] if text_snip else ""),
            "label": label,
            "confidence": conf,
            "explanation": explanation,
            "bias_flags": bias_flags
        })

    total = len(processed_items)
    avg_conf = conf_sum / max(1, total)
    sentiment_idx = (pos - neg) / max(1, total)

    # 6) Insert aggregated row into BQ
    result_id = _write_aggregated_result(job_id, org_id, user_email, "doc", total, pos, neu, neg, avg_conf, details_for_bq)

    # 7) Build pandas DataFrame for report
    df = pd.DataFrame(processed_items)
    # separate out_of_scope into different sheet if needed — here we keep one sheet and mark notes
    report_url = _upload_report_to_gcs(df, job_id)
    


    try:
        table_ref = f"{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_jobs"
        sql = f"""
        UPDATE `{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_jobs`
        SET status = @status, updated_at = @updated_at, report_url = @report_url
        WHERE job_id = @job_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("status", "STRING", "COMPLETED"),
                bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", datetime.utcnow().isoformat()),
                bigquery.ScalarQueryParameter("report_url", "STRING", report_url),
                bigquery.ScalarQueryParameter("job_id", "STRING", job_id),
            ]
        )
        # BQ.query(sql, job_config=job_config).result()
        try:
            # your existing BQ update
            BQ.query(sql, job_config=job_config).result()
            print("DEBUG_PROCESS: BQ update OK")
        except Exception as e:
            print("DEBUG_PROCESS: BQ update failed:", e)
    except Exception as e:
        print("Failed to update job status:", e)


    # 8) Send email (or log) with link
    subject = f"Sentiment report for job {job_id}"
    body_html = f"<p>Summary: total {total}, positive {pos}, neutral {neu}, negative {neg}, index {sentiment_idx:.3f}</p>"
    _send_email_with_link(user_email, report_url, subject, body_html)

    # 9) Insert vector summary into journal_vectors (short)
    try:
        summary = f"Sentiment run {job_id}: {total} rows, pos {pos}, neu {neu}, neg {neg}"
        emb = []  # use vector_utils.generate_embedding(summary) if available
        table = f"{config.PROJECT_ID}.{config.BQ_DATASET}.journal_vectors"
        row = {
            "vector_id": str(uuid.uuid4()),
            "job_id": job_id,
            "organization_id": org_id,
            "user_email": user_email,
            "summary": summary,
            "embedding": emb,
            "created_at": datetime.utcnow().isoformat()
        }
        BQ.insert_rows_json(table, [row])
    except Exception as e:
        print("journal_vectors insert failed:", e)

    # 10) Update sentiment_jobs row status to COMPLETED (best-effort)
    # 10) Update sentiment_jobs row status to COMPLETED (safe parameterized query)
    try:
        
        sql = f"""
        UPDATE `{config.PROJECT_ID}.{config.BQ_DATASET}.sentiment_jobs`
        SET status = @status,
            updated_at = @updated_at,
            report_url = @report_url
        WHERE job_id = @job_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("status", "STRING", "COMPLETED"),
                bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", datetime.utcnow().isoformat()),
                bigquery.ScalarQueryParameter("report_url", "STRING", report_url),
                bigquery.ScalarQueryParameter("job_id", "STRING", job_id),
            ]
        )
        BQ.query(sql, job_config=job_config).result()
    except Exception as e:
        print("Failed to update job status (safe):", e)
    summary_text = f"Processed {total} rows. +{pos}/-{neg}/~{neu}"
    print("DEBUG_PROCESS: about to return result_id=", result_id, " summary=", summary_text)
    return result_id, summary_text


