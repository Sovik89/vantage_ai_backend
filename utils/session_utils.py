import uuid
#import streamlit as st
from utils.bigquery_utils import insert_session_log, fetch_session_logs_from_db

# def init_session():
#     """
#     Initializes the session state variables.
#     The conversation is initialized as an empty list to prevent startup conflicts.
#     The sidebar logic is responsible for fetching and populating historical conversations.
#     """
#     if "session_id" not in st.session_state:
#         st.session_state.session_id = str(uuid.uuid4())
#     if "email_id" not in st.session_state:
#         st.session_state.email_id = "guest@example.com"
#     if "conversation" not in st.session_state:
#         st.session_state.conversation = [] # Initialize as empty

# def log_turn(query, response, source):
#     """
#     Logs a single turn of the conversation to BigQuery and the local session state.
#     """
#     log_entry = {
#         "session_id": st.session_state.session_id,
#         "email_id": st.session_state.email_id,
#         "query": query,
#         "response": response,
#         "source": source,
#     }
#     try:
#         insert_session_log(log_entry)
#         st.session_state.conversation.append(log_entry)
#     except Exception as e:
#         st.error(f"Failed to log conversation turn: {e}")

def log_turn_api(session_id: str, email_id: str, query: str, response: str, source: str):
    """
    Logs a single turn of the conversation to BigQuery from the API.
    """
    log_entry = {
        "session_id": session_id,
        "email_id": email_id,
        "query": query,
        "response": response,
        "source": source,
    }
    try:
        # Directly call the BigQuery insertion function
        insert_session_log(log_entry)
        print(f"Successfully logged turn for session {session_id}")
    except Exception as e:
        # In a backend, we print to the server console instead of showing a UI error
        print(f"ERROR: Failed to log conversation turn for session {session_id}: {e}")
        
def fetch_sessions_for_user(email_id: str):
    """
    Fetches all conversation logs for a user and organizes them by session.
    """
    all_logs = fetch_session_logs_from_db(email_id=email_id)
    sessions = {}
    for log in all_logs:
        sid = log["session_id"]
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "first_query": log["query"] or "File Upload",
                "last_updated": log["created_at"],
                "turns": []
            }
        sessions[sid]["turns"].append(log)
        # Update last_updated to the latest turn's timestamp
        sessions[sid]["last_updated"] = log["created_at"]
    
    # Return a list of session summaries, sorted by most recent
    session_list = sorted(sessions.values(), key=lambda s: s["last_updated"], reverse=True)
    return session_list
