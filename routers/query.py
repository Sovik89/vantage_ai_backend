# from fastapi import APIRouter, HTTPException
# from fastapi.responses import StreamingResponse, JSONResponse
# from schemas.models import QueryRequest
# import uuid
# from datetime import datetime
# import hashlib
# import traceback

# # --- Local Utility Imports ---
# try:
#     from utils.query_utils import classify_topic
#     from utils.vertex_ai_utils import generate_freeform_streaming, generate_freeform
#     from utils.vector_utils import search_similar_papers, insert_vector_record, generate_embeddings
#     from utils.bigquery_utils import insert_summary, check_hash_exists, insert_session_log
# except ImportError as e:
#     print(f"ERROR: A utility file could not be imported. Error: {e}")
#     raise

# router = APIRouter()

# # --- Helper for Logging ---
# def log_turn_api(session_id, email_id, query, response, source):
#     """Logs a single turn of the conversation to BigQuery from the API."""
#     log_entry = { "session_id": session_id, "email_id": email_id, "query": query, "response": response, "source": source }
#     try:
#         insert_session_log(log_entry)
#         print(f"Successfully logged turn for session {session_id}")
#     except Exception as e:
#         print(f"ERROR: Failed to log conversation turn: {e}")

# @router.post("/ask")
# async def ask_question_streaming(request: QueryRequest):
#     """
#     Handles user queries with a STREAMING response. Ideal for frontends.
#     """
#     user_prompt = request.query
#     session_id = request.session_id or str(uuid.uuid4())
#     email_id = "guest@vantage.ai" 

#     if not classify_topic(user_prompt):
#         raise HTTPException(status_code=400, detail="Query is not related to HR or People Analytics.")

#     async def stream_generator():
#         full_response = ""
#         source = "unknown"
#         try:
#             print(f"STREAM: Starting process for query: {user_prompt[:50]}...")
#             candidates = search_similar_papers(user_prompt, top_k=5)
            
#             if candidates:
#                 print(f"STREAM: Found {len(candidates)} candidates from vector search.")
#                 combined_summaries = "\n\n".join([c.get("summary", "") for c in candidates])
#                 prompt = f"Based on the following papers, answer the user's query.\nQuery: {user_prompt}\nPapers:\n{combined_summaries}"
#                 source = "vector_search"
                
#                 stream = generate_freeform_streaming(prompt)
#                 for chunk in stream:
#                     full_response += chunk
#                     yield chunk
                
#             else: # Gemini Fallback
#                 print("STREAM: No candidates found. Proceeding to Gemini fallback.")
#                 prompt = f"You are an expert HR & People Analytics assistant. Answer clearly: {user_prompt}"
#                 source = "gemini_fallback"

#                 stream = generate_freeform_streaming(prompt)
#                 for chunk in stream:
#                     full_response += chunk
#                     yield chunk

#                 # --- Knowledge Reinforcement ---
#                 if full_response and "failed" not in full_response.lower():
#                     # ... (rest of the knowledge reinforcement logic remains the same)
#                     fallback_hash = hashlib.sha256(full_response.encode()).hexdigest()
#                     if not check_hash_exists(fallback_hash):
#                         record_timestamp = datetime.utcnow().isoformat()
#                         summary_record = {
#                             "pdf_name": f"fallback_{fallback_hash[:10]}", "file_hash": fallback_hash,
#                             "title": user_prompt, "summary": full_response, "source_type": "gemini_fallback",
#                             "created_at": record_timestamp
#                         }
#                         embeddings = generate_embeddings([full_response])
#                         if embeddings:
#                             vector_record = { **summary_record, "embedding": embeddings[0] }
#                             insert_summary(summary_record)
#                             insert_vector_record(vector_record)
#                             print(f"STREAM: Fallback insight saved with hash: {fallback_hash}")

#             print(f"STREAM: Full response generated. Logging turn.")
#             log_turn_api(session_id, email_id, user_prompt, full_response, source)
#             print(f"STREAM: Process finished.")

#         except Exception as e:
#             tb_str = traceback.format_exc()
#             error_message = f"An error occurred in stream_generator: {e}\n{tb_str}"
#             print(f"ERROR in /ask endpoint: {error_message}")
#             yield error_message

#     return StreamingResponse(stream_generator(), media_type="text/event-stream")


# @router.post("/ask/nostream", response_model=dict)
# async def ask_question_nostream(request: QueryRequest):
#     """
#     Handles user queries with a simple JSON response. Ideal for testing with Postman.
#     """
#     user_prompt = request.query
#     session_id = request.session_id or str(uuid.uuid4())
#     email_id = "guest@vantage.ai"

#     if not classify_topic(user_prompt):
#         raise HTTPException(status_code=400, detail="Query is not related to HR or People Analytics.")

#     try:
#         full_response = ""
#         source = "unknown"
#         source_documents = []

#         candidates = search_similar_papers(user_prompt, top_k=5)

#         if candidates:
#             source = "vector_search"
#             source_documents = [{"file_name": c.get("pdf_name"), "title": c.get("title"), "distance": c.get("distance")} for c in candidates]
#             combined_summaries = "\n\n".join([c.get("summary", "") for c in candidates])
#             prompt = f"Based on the following papers, answer the user's query.\nQuery: {user_prompt}\nPapers:\n{combined_summaries}"
#             full_response = generate_freeform(prompt) # Use the non-streaming version
#         else:
#             source = "gemini_fallback"
#             prompt = f"You are an expert HR & People Analytics assistant. Answer clearly: {user_prompt}"
#             full_response = generate_freeform(prompt) # Use the non-streaming version
            
#             # --- Knowledge Reinforcement ---
#             if full_response and "failed" not in full_response.lower():
#                 # ... (rest of the knowledge reinforcement logic remains the same)
#                 fallback_hash = hashlib.sha256(full_response.encode()).hexdigest()
#                 if not check_hash_exists(fallback_hash):
#                     record_timestamp = datetime.utcnow().isoformat()
#                     summary_record = {
#                         "pdf_name": f"fallback_{fallback_hash[:10]}", "file_hash": fallback_hash,
#                         "title": user_prompt, "summary": full_response, "source_type": "gemini_fallback",
#                         "created_at": record_timestamp
#                     }
#                     embeddings = generate_embeddings([full_response])
#                     if embeddings:
#                         vector_record = { **summary_record, "embedding": embeddings[0] }
#                         insert_summary(summary_record)
#                         insert_vector_record(vector_record)
#                         print(f"NOSTREAM: Fallback insight saved with hash: {fallback_hash}")

#         log_turn_api(session_id, email_id, user_prompt, full_response, source)
        
#         return JSONResponse(content={
#             "response_text": full_response,
#             "source": source,
#             "source_documents": source_documents,
#             "session_id": session_id
#         })

#     except Exception as e:
#         tb_str = traceback.format_exc()
#         print(f"ERROR in /ask/nostream endpoint: {e}\n{tb_str}")
#         raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

#---------------------------------New Approach----------------------------------#

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from schemas.models import QueryRequest, InsightResponse  # Import the new response model
import uuid
from datetime import datetime
import hashlib
import traceback

# --- Local Utility Imports ---
try:
    from utils.query_utils import classify_topic, detect_metric_and_filter
    from utils.vertex_ai_utils import generate_freeform_streaming, generate_freeform
    from utils.vector_utils import search_similar_papers, insert_vector_record, generate_embeddings, search_similar_titles
    from utils.bigquery_utils import insert_summary, check_hash_exists, insert_session_log
except ImportError as e:
    print(f"ERROR: A utility file could not be imported. Error: {e}")
    raise

router = APIRouter()

# --- Helper for Logging ---
def log_turn_api(session_id, email_id, query, response, source):
    """Logs a single turn of the conversation to BigQuery from the API."""
    log_entry = { "session_id": session_id, "email_id": email_id, "query": query, "response": response, "source": source }
    try:
        insert_session_log(log_entry)
        print(f"Successfully logged turn for session {session_id}")
    except Exception as e:
        print(f"ERROR: Failed to log conversation turn: {e}")

@router.post("/ask")
async def ask_question_streaming(request: QueryRequest):
    # This streaming endpoint remains the same for the React app's real-time UI
    
    """
    Handles user queries with a STREAMING response. Ideal for frontends.
    """
    user_prompt = request.query
    session_id = request.session_id or str(uuid.uuid4())
    email_id = "guest@vantage.ai" 

    if not classify_topic(user_prompt):
        raise HTTPException(status_code=400, detail="Query is not related to HR or People Analytics.")

    async def stream_generator():
        full_response = ""
        source = "unknown"
        try:
            print(f"STREAM: Starting process for query: {user_prompt[:50]}...")
            candidates = search_similar_papers(user_prompt, top_k=5)
            
            if candidates:
                print(f"STREAM: Found {len(candidates)} candidates from vector search.")
                combined_summaries = "\n\n".join([c.get("summary", "") for c in candidates])
                prompt = f"Based on the following papers, answer the user's query.\nQuery: {user_prompt}\nPapers:\n{combined_summaries}"
                source = "vector_search"
                
                stream = generate_freeform_streaming(prompt)
                for chunk in stream:
                    full_response += chunk
                    yield chunk
                
            else: # Gemini Fallback
                print("STREAM: No candidates found. Proceeding to Gemini fallback.")
                prompt = f"You are an expert HR & People Analytics assistant. Answer clearly: {user_prompt}"
                source = "gemini_fallback"

                stream = generate_freeform_streaming(prompt)
                for chunk in stream:
                    full_response += chunk
                    yield chunk

                # --- Knowledge Reinforcement ---
                if full_response and "failed" not in full_response.lower():
                    # ... (rest of the knowledge reinforcement logic remains the same)
                    fallback_hash = hashlib.sha256(full_response.encode()).hexdigest()
                    if not check_hash_exists(fallback_hash):
                        record_timestamp = datetime.utcnow().isoformat()
                        summary_record = {
                            "pdf_name": f"fallback_{fallback_hash[:10]}", "file_hash": fallback_hash,
                            "title": user_prompt, "summary": full_response, "source_type": "gemini_fallback",
                            "created_at": record_timestamp
                        }
                        embeddings = generate_embeddings([full_response])
                        if embeddings:
                            vector_record = { **summary_record, "embedding": embeddings[0] }
                            insert_summary(summary_record)
                            insert_vector_record(vector_record)
                            print(f"STREAM: Fallback insight saved with hash: {fallback_hash}")

            print(f"STREAM: Full response generated. Logging turn.")
            log_turn_api(session_id, email_id, user_prompt, full_response, source)
            print(f"STREAM: Process finished.")

        except Exception as e:
            tb_str = traceback.format_exc()
            error_message = f"An error occurred in stream_generator: {e}\n{tb_str}"
            print(f"ERROR in /ask endpoint: {error_message}")
            yield error_message

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

# @router.post("/ask/nostream", response_model=InsightResponse) # Use the new response model
# async def ask_question_nostream(request: QueryRequest):
#     """
#     Handles user queries with a simple JSON response. Ideal for testing with Postman.
#     NOW INCLUDES SOURCE DOCUMENTS FOR DOWNLOAD FUNCTIONALITY.
#     """
#     user_prompt = request.query
#     session_id = request.session_id or str(uuid.uuid4())
#     email_id = "guest@vantage.ai"

#     if not classify_topic(user_prompt):
#         raise HTTPException(status_code=400, detail="Query is not related to HR or People Analytics.")

#     try:
#         full_response = ""
#         source = "unknown"
#         source_documents = []

#         candidates = search_similar_papers(user_prompt, top_k=5)

#         if candidates:
#             source = "vector_search"
#             # ✅ PREPARE FULL SOURCE DOCUMENT DATA
#             source_documents = [
#                 {
#                     "file_name": c.get("pdf_name", "Unknown"), 
#                     "title": c.get("title", "Untitled"), 
#                     "summary": c.get("summary", ""),
#                     "distance": c.get("distance", 1.0)
#                 } for c in candidates
#             ]
#             combined_summaries = "\n\n".join([c["summary"] for c in source_documents])
#             prompt = f"Based on the following papers, answer the user's query.\nQuery: {user_prompt}\nPapers:\n{combined_summaries}"
#             full_response = generate_freeform(prompt)
#         else:
#             source = "gemini_fallback"
#             prompt = f"You are an expert HR & People Analytics assistant. Answer clearly: {user_prompt}"
#             full_response = generate_freeform(prompt)
#             # For a fallback, the "source document" is the Q&A pair itself
#             source_documents = [{"file_name": "N/A (Generative)", "title": user_prompt, "summary": full_response, "distance": 0.0}]
            
#             # --- Knowledge Reinforcement ---
#             if full_response and "failed" not in full_response.lower():
#                 fallback_hash = hashlib.sha256(full_response.encode()).hexdigest()
#                 if not check_hash_exists(fallback_hash):
#                     # (Code for saving fallback to DB is unchanged and omitted for brevity)
#                     pass

#         log_turn_api(session_id, email_id, user_prompt, full_response, source)
        
#         # ✅ RETURN THE COMPLETE INSIGHT RESPONSE
#         return InsightResponse(
#             response_text=full_response,
#             source=source,
#             source_documents=source_documents,
#             session_id=session_id
#         )

#     except Exception as e:
#         tb_str = traceback.format_exc()
#         print(f"ERROR in /ask/nostream endpoint: {e}\n{tb_str}")
#         raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

@router.post("/ask/nostream", response_model=InsightResponse)
async def ask_question_nostream(request: QueryRequest):
    """
    Handles user queries with a simple JSON response, featuring a robust,
    multi-layered deduplication for fallback insights.
    """
    user_prompt = request.query
    session_id = request.session_id or str(uuid.uuid4())
    email_id = "guest@vantage.ai" 

    if not classify_topic(user_prompt):
        raise HTTPException(status_code=400, detail="Query is not related to HR or People Analytics.")

    try:
        # --- VECTOR DB FIRST APPROACH ---
        # First, search for relevant documents (from PDFs, etc.)
        candidates = search_similar_papers(user_prompt, top_k=5)
        
        # More lenient threshold for initial document matching
        document_confidence_threshold = 0.8  # Lower number = more matches
        relevant_documents = [c for c in candidates if c.get("distance", 1.0) <= document_confidence_threshold]

        if relevant_documents:
            print(f"NOSTREAM: Found {len(relevant_documents)} relevant documents. Synthesizing answer.")
            source = "vector_search"
            combined_summaries = "\n\n".join([c.get("summary", "") for c in relevant_documents])
            
            # More nuanced prompt that allows for partial matches
            prompt = f"""Based on the following documents, provide an answer to the user's query.
If the documents contain directly relevant information, use it.
If they contain partially relevant information, incorporate it while acknowledging the limitations.
If the information is not sufficient, you can provide a general expert response while noting that it's not from the documents.

User Query: {user_prompt}

Document Contents:
{combined_summaries}
"""
            # Use higher temperature for synthesis to allow connecting partial matches
            full_response = generate_freeform(prompt, temperature=0.3)
            
            log_turn_api(session_id, email_id, user_prompt, full_response, source)
            return InsightResponse(
                response_text=full_response, source=source,
                source_documents=relevant_documents, session_id=session_id
            )

        # --- GEMINI FALLBACK WITH MULTI-LAYERED DEDUPLICATION ---
        else:
            print(f"NOSTREAM: No relevant documents found. Proceeding to Gemini fallback with deduplication.")
            
            # Layer 1: Check for existing insights with a very similar TITLE
            # similar_titles = search_similar_titles(user_prompt)
            # title_confidence_threshold = 0.7 # Very strict for titles
            
            #In the ask_question_nostream function, update this section:
            similar_titles = search_similar_titles(user_prompt)
            # Change the threshold check to use similarity_score:
            if similar_titles and similar_titles[0].get('similarity_score', 0) >= 70:
                print(f"✓ Found similar existing title: {similar_titles[0]['title']}")
                print(f"  Match: {similar_titles[0]['match_percentage']}")
                source = "vector_search_title_hit"
                
                # Use the existing summary instead of placeholder
                full_response = similar_titles[0]['summary']
                
                log_turn_api(session_id, email_id, user_prompt, full_response, source)
                return InsightResponse(
                    response_text=full_response,
                    source=source,
                    source_documents=similar_titles,
                    session_id=session_id
                )

            # Smooth transition to Gemini
            print(f"NOSTREAM: Using Gemini to provide expert response.")
            source = "gemini_fallback"
            prompt = f"""You are an expert HR & People Analytics assistant. 
The user's question is about: {user_prompt}

Provide a helpful response based on your expert knowledge. Focus on:
1. Direct answer to the question
2. Industry context and trends
3. Practical implications
4. Any relevant examples or case studies

Remember to maintain a balanced, professional perspective."""

            # Use higher temperature for Gemini fallback to allow more comprehensive response
            full_response = generate_freeform(prompt, temperature=0.4)
            
            if full_response and "failed" not in full_response.lower():
                # Layer 2: Check for exact content hash before saving
                fallback_hash = hashlib.sha256(full_response.encode()).hexdigest()
                if not check_hash_exists(fallback_hash):
                    print(f"NOSTREAM: New unique fallback insight found. Saving with hash: {fallback_hash}")
                    # ... (The rest of the saving logic remains the same) ...
                    record_timestamp = datetime.utcnow().isoformat()
                    summary_record = {
                        "pdf_name": f"fallback_{fallback_hash[:10]}", "file_hash": fallback_hash,
                        "title": user_prompt, "summary": full_response, "source_type": "gemini_fallback",
                        "created_at": record_timestamp
                    }
                    embeddings = generate_embeddings([full_response, user_prompt]) # Embed both answer and title
                    if embeddings and len(embeddings) == 2:
                        vector_record = { **summary_record, "embedding": embeddings[0] }
                        insert_summary(summary_record)
                        insert_vector_record(vector_record)
                else:
                    print(f"NOSTREAM: Duplicate fallback content detected by hash. Skipping insert.")

            log_turn_api(session_id, email_id, user_prompt, full_response, source)
            return InsightResponse(
                response_text=full_response, source=source,
                source_documents=[], session_id=session_id
            )

    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"ERROR in /ask/nostream endpoint: {e}\n{tb_str}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


