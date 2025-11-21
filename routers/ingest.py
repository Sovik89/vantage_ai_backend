from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
from schemas.models import ProcessResponse
import os
import traceback
import hashlib
from io import BytesIO

# --- Local Utility Imports ---
try:
    from utils.file_utils import get_text_from_file, compute_file_hash
    from utils.query_utils import is_hr_text,is_hr_pa_content
    from utils.vertex_ai_utils import summarize_text, structured_extract, generate_freeform
    from utils.vector_utils import generate_embeddings, insert_vector_record
    from utils.bigquery_utils import check_hash_exists, insert_summary, get_existing_summary
    from datetime import datetime
except ImportError as e:
    print(f"ERROR: A utility file could not be imported. Error: {e}")
    raise

router = APIRouter()

# --- Constants for GIGO Guardrails ---
MAX_FILE_SIZE_MB = 20
MIN_TEXT_LENGTH = 250

@router.post("/process", response_model=ProcessResponse)
async def process_files_and_query(
    files: List[UploadFile] = File(...),
    query: Optional[str] = Form(None)
):
    """
    Handles the combined workflow of file ingestion and optional querying.
    """
    valid_records_to_process = []
    processed_files_names = []
    skipped_files = {}
    existing_summaries = []  # Add this line to initialize the list

    # --- PASS 1: VALIDATION ---
    for up_file in files:
        file_name = up_file.filename
        try:
            # ✅ FIX: Read the async file into a standard bytes object first.
            content = await up_file.read()

            if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
                skipped_files[file_name] = f"File size exceeds {MAX_FILE_SIZE_MB}MB limit."
                continue
            
            # Now, use synchronous functions with the file content
            file_hash = compute_file_hash(content)
            if check_hash_exists(file_hash):
                existing_summary = get_existing_summary(file_hash)
                if existing_summary:
                    print(f"📑 Found existing content for {file_name}")
                    existing_summaries.append({
                        "file_name": file_name,
                        "summary": existing_summary,
                        "status": "existing"
                    })
                skipped_files[file_name] = "Duplicate file content already in the database."
                continue

            _, file_extension = os.path.splitext(file_name)
            
            # ✅ FIX: Pass an in-memory buffer to the text extraction functions
            text = get_text_from_file(BytesIO(content), file_extension)

            if not text or len(text) < MIN_TEXT_LENGTH:
                skipped_files[file_name] = "Insufficient text content."
                continue
            if not is_hr_pa_content(text):
                print(f"❌ Validation failed for {file_name}")
                skipped_files[file_name] = "Content does not appear to be HR-related."
                continue
            # if not is_hr_pa_content(text) or not is_hr_text(text):
            #     skipped_files[file_name] = "Content does not appear to be HR-related."
            #     continue
            
            valid_records_to_process.append({"file_name": file_name, "text": text, "hash": file_hash, "ext": file_extension})
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Validation Error for {file_name}: {e}\n{tb}")
            skipped_files[file_name] = f"An unexpected error during validation: {e}"

    # --- PASS 2: BATCH PROCESSING & SAVING TO DB ---
    processed_summaries = []
    if valid_records_to_process:
        all_texts = [rec["text"] for rec in valid_records_to_process]
        all_embeddings = generate_embeddings(all_texts)

        for i, record_data in enumerate(valid_records_to_process):
            file_name = record_data["file_name"]
            text = record_data["text"]
            file_hash = record_data["hash"]
            embedding = all_embeddings[i] if i < len(all_embeddings) else None

            if not embedding:
                skipped_files[file_name] = "Failed to generate embedding."
                continue
            
            try:
                meta = structured_extract(text) or {}
                summary = summarize_text(text)
                record_timestamp = datetime.utcnow().isoformat()

                summary_record = {
                    "pdf_name": file_name, "file_hash": file_hash, "title": meta.get("title", file_name),
                    "summary": summary, "source_type": record_data["ext"].lower().replace('.', ''),
                    "created_at": record_timestamp
                }
                vector_record = { **summary_record, "embedding": embedding }

                insert_summary(summary_record)
                insert_vector_record(vector_record)
                processed_files_names.append(file_name)
                processed_summaries.append(summary)
                
                print(f"✅ Processed and saved: {file_name}")
                
            except Exception as e:
                tb = traceback.format_exc()
                print(f"❌ DB insertion error for {file_name}: {e}\n{tb}")
                skipped_files[file_name] = f"An error occurred during DB insertion: {e}"

    # # --- PASS 3: CONDITIONAL RESPONSE GENERATION ---
    # generated_insight = None
    # source = "file_ingestion"
    
    # if processed_summaries:
    #     combined_text = "\n\n---\n\n".join(processed_summaries)
        
    #     try:
    #         if query:
    #             # User asked a question about the uploaded docs
    #             source = "file_query"
    #             prompt = f"Based ONLY on the following text summaries, provide a concise answer to the user's query.\n\nUser Query: \"{query}\"\n\nSummaries:\n{combined_text}"
    #             print(f"🤖 Generating insight for query: {query}")
    #             generated_insight = generate_freeform(prompt)
    #         else:
    #             # No query, just provide a consolidated summary
    #             source = "file_summary"
    #             prompt = f"Provide a high-level consolidated summary of the following documents.\n\nSummaries:\n{combined_text}"
    #             print(f"🤖 Generating consolidated summary for {len(processed_summaries)} documents")
    #             generated_insight = generate_freeform(prompt)
            
    #         # ✅ FIX: Check if Gemini returned empty/None
    #         if not generated_insight or generated_insight.strip() == "":
    #             print("⚠️ Gemini returned empty response, using fallback")
    #             generated_insight = (
    #                 f"Successfully processed {len(processed_files_names)} document(s). "
    #                 f"The content has been extracted, summarized, and stored in the knowledge base. "
    #                 f"You can now query this information using the insights endpoint."
    #             )
    #         else:
    #             print(f"✅ Generated insight ({len(generated_insight)} chars)")
                
    #     except Exception as e:
    #         tb = traceback.format_exc()
    #         print(f"❌ Error generating insight: {e}\n{tb}")
    #         generated_insight = (
    #             f"Successfully processed {len(processed_files_names)} document(s) and saved to database. "
    #             f"However, insight generation encountered an error: {str(e)}. "
    #             f"The documents are saved and searchable."
    #         )
    
    # elif not processed_files_names:
    #     # Nothing was processed successfully
    #     generated_insight = (
    #         "No files were successfully processed. "
    #         "Please check the skipped_files for details on why files were rejected."
    #     )
    #     source = "validation_failure"

    # return ProcessResponse(
    #     message="Processing complete.",
    #     processed_files=processed_files_names,
    #     skipped_files=skipped_files,
    #     generated_insight=generated_insight,
    #     source=source
    # )
# Modify the insight generation section:
    # --- PASS 3: CONDITIONAL RESPONSE GENERATION ---
    generated_insight = None
    source = "file_ingestion"
    
    # Combine new and existing summaries
    all_summaries = []
    if processed_summaries:
        all_summaries.extend([{"summary": s, "status": "new"} for s in processed_summaries])
    if existing_summaries:
        all_summaries.extend(existing_summaries)
    
    if all_summaries:
        try:
            if query:
                source = "file_query"
                prompt = f"""Based on the following document summaries (including both new and existing documents), 
                provide a concise answer to the user's query.

                Context: {len(processed_summaries)} new documents and {len(existing_summaries)} existing documents.
                
                User Query: "{query}"
                
                Summaries:
                {chr(10).join(f"[{'New' if s['status']=='new' else 'Existing'}] {s['summary']}" for s in all_summaries)}"""
                
                generated_insight = generate_freeform(prompt)
            else:
                source = "mixed_summary" if existing_summaries else "file_summary"
                prompt = f"""Provide a consolidated summary of these documents.
                Context: Processing results include {len(processed_summaries)} new documents and {len(existing_summaries)} existing documents.
                
                Summaries:
                {chr(10).join(f"[{'New' if s['status']=='new' else 'Existing'}] {s['summary']}" for s in all_summaries)}
                
                Please provide:
                1. An overview of the key topics across all documents
                2. Note any significant insights from new vs existing content
                3. A brief synthesis of how the documents relate to each other"""
                
                generated_insight = generate_freeform(prompt)
            
            if not generated_insight or generated_insight.strip() == "":
                print("⚠️ Gemini returned empty response, using fallback")
                generated_insight = (
                    f"Processed {len(processed_files_names)} new document(s) and found {len(existing_summaries)} "
                    f"existing related document(s) in the database. All content is now searchable "
                    f"in the knowledge base."
                )
            
        except Exception as e:
            tb = traceback.format_exc()
            print(f"❌ Error generating insight: {e}\n{tb}")
            generated_insight = (
                f"Processed {len(processed_files_names)} new document(s) and found {len(existing_summaries)} "
                f"existing document(s). Error during insight generation: {str(e)}"
            )
    
    elif not processed_files_names and not existing_summaries:
        generated_insight = (
            "No files were successfully processed. "
            "Please check the skipped_files for details on why files were rejected."
        )
        source = "validation_failure"

    # Modified return to include counts of new and existing
    return ProcessResponse(
        message="Processing complete.",
        processed_files=processed_files_names,
        skipped_files=skipped_files,
        generated_insight=generated_insight,
        source=source,
        stats={
            "new_files": len(processed_files_names),
            "existing_files": len(existing_summaries),
            "total_files": len(files),
            "failed_files": len(skipped_files)
        }
    )