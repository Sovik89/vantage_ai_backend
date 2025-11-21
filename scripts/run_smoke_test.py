# scripts/run_smoke_sync.py
import sys, os, uuid
from worker import sentiment_processing_old

def run(file_path, domain="exit_feedback", consent=False, user_email="ops@example.com"):
    with open(file_path, "rb") as f:
        b = f.read()
    payload = {
        "job_id": str(uuid.uuid4()),
        "file_bytes": b.hex(),
        "filename": os.path.basename(file_path),
        "domain": domain,
        "consent": consent,
        "user_email": user_email,
        "organization_id": "guest_org"
    }
    res = sentiment_processing_old.process_job(payload, sync_mode=True)
    print("Result:", res)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_smoke_sync.py path/to/file.xlsx [domain] [consent]")
        sys.exit(1)
    fp = sys.argv[1]
    domain = sys.argv[2] if len(sys.argv) > 2 else "exit_feedback"
    consent = (sys.argv[3].lower() == "true") if len(sys.argv) > 3 else False
    run(fp, domain, consent)
