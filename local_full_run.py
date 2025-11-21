# scripts/local_full_run.py
import os
import io
import uuid
import json
import pathlib
import tempfile
import traceback
from datetime import datetime

# Adjust repo path if needed
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Create a tiny sample Excel if not provided
SAMPLE_OUT = "test_data"
os.makedirs(SAMPLE_OUT, exist_ok=True)
SAMPLE_FILE = os.path.join(SAMPLE_OUT, "local_dry_run.xlsx")

def ensure_sample():
    import pandas as pd
    if not os.path.exists(SAMPLE_FILE):
        rows = [
            {"row_id": 1, "feedback": "I loved the training, the trainer was excellent and very helpful."},
            {"row_id": 2, "feedback": "No laptop on day one and no access to systems, onboarding failed."},
            {"row_id": 3, "feedback": "Candidate failed the test, not recommended."},
            {"row_id": 4, "feedback": "The cricket match was amazing last weekend."},
            {"row_id": 5, "feedback": "Contact: john.doe@example.com for more info."}
        ]
        df = pd.DataFrame(rows)
        df.to_excel(SAMPLE_FILE, index=False, engine="openpyxl")
        print("Wrote sample file to", SAMPLE_FILE)
    else:
        print("Sample file exists:", SAMPLE_FILE)

def run_local():
    try:
        ensure_sample()
        from worker import sentiment_processing_old
        import pandas as pd

        # Monkeypatch the _upload_report_to_gcs in sentiment_processing to write locally
        def _upload_report_to_local(df, job_id):
            out_dir = os.path.abspath("local_reports")
            os.makedirs(out_dir, exist_ok=True)
            fname = f"sentiment-report-{job_id}.xlsx"
            fpath = os.path.join(out_dir, fname)
            df.to_excel(fpath, index=False, engine="openpyxl")
            # return a local file:// path for the caller
            return f"file://{fpath}"

        # apply monkeypatch
        sentiment_processing_old._upload_report_to_gcs = _upload_report_to_local

        # also monkeypatch email send to just print to log
        def _fake_send_email_with_link(to_email, url, subject, body_html):
            print(f"[LOCAL EMAIL] to={to_email} subject={subject}\n  link={url}\n  body={body_html}")
            return True
        sentiment_processing_old._send_email_with_link = _fake_send_email_with_link

        # Read bytes from file and call process_job in sync mode
        with open(SAMPLE_FILE, "rb") as f:
            file_bytes = f.read()

        payload = {
            "job_id": str(uuid.uuid4()),
            "file_bytes": file_bytes.hex(),
            "filename": os.path.basename(SAMPLE_FILE),
            "domain": "training_feedback",
            "consent": False,
            "user_email": "tester@example.com",
            "organization_id": "guest_org"
        }

        print("Calling process_job (sync_mode=True) ...")
        result = sentiment_processing_old.process_job(payload, sync_mode=True)
        print("process_job returned:", result)

        # show generated local report path
        report_dir = os.path.abspath("local_reports")
        print("Local reports directory:", report_dir)
        for f in os.listdir(report_dir):
            print(" -", f)

        # Optionally preview first few rows of the report
        rpt_file = os.path.join(report_dir, f"sentiment-report-{payload['job_id']}.xlsx")
        if os.path.exists(rpt_file):
            print("Report exists at:", rpt_file)
        else:
            # try latest file
            files = sorted([os.path.join(report_dir, f) for f in os.listdir(report_dir)], key=os.path.getmtime)
            if files:
                print("Latest report:", files[-1])
            else:
                print("No report file found in local_reports")

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    run_local()
