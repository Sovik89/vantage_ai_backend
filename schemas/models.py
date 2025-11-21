from pydantic import BaseModel
from typing import Dict, List, Optional

# --- Request Models ---

# class QueryRequest(BaseModel):
#     """Defines the structure for a user's query sent to the /insights/ask endpoint."""
#     query: str
#     session_id: Optional[str] = None
class QueryRequest(BaseModel):
    """Defines the structure for a user's query sent to the /insights/ask endpoint."""
    query: str
    session_id: Optional[str] = None

class DownloadRequest(BaseModel):
    """Defines the payload for the /download/docx endpoint."""
    user_prompt: str
    consolidated_text: str
    records: List[Dict]


# --- Response Models ---

# class SourceDocument(BaseModel):
#     """Defines the structure for a single source document."""
#     file_name: str
#     title: str
#     summary: str
#     distance: float

class SourceDocument(BaseModel):
    """Defines the structure for a source document used to generate an insight."""
    pdf_name: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    distance: Optional[float] = None
    file_hash: Optional[str] = None

class InsightResponse(BaseModel):
    """Defines the structure for the JSON response from the /insights/ask/nostream endpoint."""
    response_text: str
    source: str
    source_documents: List[SourceDocument]
    session_id: str

class IngestResponse(BaseModel):
    """Defines the structure for the response after file ingestion."""
    message: str
    processed_files: List[str]
    skipped_files: Dict[str, str]
    
# --- NEW Consolidated File+Query(optional) Response Model ---

class ProcessResponse(BaseModel):
    """
    Defines the comprehensive response for the new combined ingestion and query endpoint.
    """
    message: str
    processed_files: List[str]
    skipped_files: Dict[str, str]
    generated_insight: Optional[str] = None
    source: str
    stats:Dict[str,int]  # New field for statistics like number of processed files, skipped files, etc.
    

# --- NEW Session Models ---

class SessionTurn(BaseModel):
    """Defines the structure for a single turn in a conversation."""
    query: str
    response: str
    source: str
    created_at: str

class SessionInfo(BaseModel):
    """Defines the summary of a single session for the sidebar list."""
    session_id: str
    first_query: str
    last_updated: str
    


