from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import os
from datetime import datetime

# --- Local Utility Imports ---
try:
    from utils.file_utils import compute_pdf_hash, get_text_from_file
    from utils.query_utils import is_hr_text
    from utils.vertex_ai_utils import summarize_text, structured_extract
    from utils.vector_utils import generate_embeddings, insert_vector_record
    from utils.bigquery_utils import check_hash_exists, insert_summary
    from schemas.models import IngestResponse
except ImportError as e:
    print(f"ERROR: A utility file could not be imported. Error: {e}")
    raise

router = APIRouter()

# Constants from our Streamlit app
MAX_FILE_SIZE_MB = 20
MIN_TEXT_LENGTH = 250

@router.post("/ingest", response_model=IngestResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Handles file uploads, performs GIGO/deduplication checks, processes valid files,
    and saves them to the database.
    """
    valid_records_to_process = []
    skipped_files_info = {}
    processed_files_names = []

    # --- PASS 1: VALIDATION ---
    print(f"INGEST: Starting validation for {len(files)} files...")
    for up_file in files:
        file_name = up_file.filename
        
        # We need to read the file content to compute hash and text
        content = await up_file.read()
        await up_file.seek(0) # Reset file pointer after reading

        file_hash = hashlib.sha256(content).hexdigest()

        # GIGO and Deduplication Checks
        if up_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            skipped_files_info[file_name] = f"File size exceeds {MAX_FILE_SIZE_MB}MB limit."
            continue
        if check_hash_exists(file_hash):
            skipped_files_info[file_name] = "Duplicate file content already in the database."
            continue

        _, file_extension = os.path.splitext(file_name)
        text = get_text_from_file(up_file, file_extension)

        if not text or len(text) < MIN_TEXT_LENGTH:
            skipped_files_info[file_name] = "Insufficient text content."
            continue
        if not is_hr_text(text):
            skipped_files_info[file_name] = "Content does not appear to be HR-related."
            continue

        valid_records_to_process.append({"file_name": file_name, "text": text, "hash": file_hash, "ext": file_extension})

    # --- PASS 2: BATCH PROCESSING ---
    if valid_records_to_process:
        print(f"INGEST: Found {len(valid_records_to_process)} valid files. Starting batch processing...")
        all_texts = [rec["text"] for rec in valid_records_to_process]
        
        try:
            all_embeddings = generate_embeddings(all_texts)
            
            for i, record_data in enumerate(valid_records_to_process):
                text = record_data["text"]
                file_hash = record_data["hash"]
                embedding = all_embeddings[i] if i < len(all_embeddings) else None

                if not embedding:
                    skipped_files_info[record_data["file_name"]] = "Failed to generate embedding."
                    continue

                meta = structured_extract(text) or {}
                summary = summarize_text(text)
                record_timestamp = datetime.utcnow().isoformat()

                summary_record = {
                    "pdf_name": record_data["file_name"], "file_hash": file_hash, 
                    "title": meta.get("title", record_data["file_name"]),
                    "summary": summary, "source_type": record_data["ext"].lower().replace('.', ''),
                    "created_at": record_timestamp
                }
                
                vector_record = {**summary_record, "embedding": embedding}

                insert_summary(summary_record)
                insert_vector_record(vector_record)
                processed_files_names.append(record_data["file_name"])
                print(f"INGEST: Successfully processed and saved {record_data['file_name']}")

        except Exception as e:
            print(f"ERROR: An error occurred during batch processing: {e}")
            raise HTTPException(status_code=500, detail=f"An error occurred during batch processing: {e}")

    return IngestResponse(
        message="File ingestion process completed.",
        processed_files=processed_files_names,
        skipped_files=skipped_files_info
    )

