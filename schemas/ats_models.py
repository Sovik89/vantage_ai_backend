# schemas/ats_models.py

from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import date

class AtsQueryRequest(BaseModel):
    job_id: str = Field(..., description="ATS job ID to query")
    query: str = Field(..., description="Question about the analysis")
    user_email: str = Field(..., description="User email for validation")
    analysis_date: Optional[str] = Field(None, description="Filter by date (YYYY-MM-DD) for multiple analyses")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "ats-xyz789-abc123",
                "query": "What are the collective strengths?",
                "user_email": "recruiter@company.com",
                "analysis_date": "2025-10-27"  # Optional
            }
        }

class AtsQueryResponse(BaseModel):
    job_id: str
    query: str
    answer: str
    job_summary: Dict = Field(..., description="Job metadata and summary")
    supporting_data: Dict = Field(..., description="Aggregated candidate metrics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "ats-xyz789-abc123",
                "query": "What are the collective strengths?",
                "answer": "Based on the analysis...",
                "job_summary": {
                    "position_title": "Senior Data Engineer",
                    "organization": "Acme Corp",
                    "total_candidates_analyzed": 15,
                    "created_at": "2025-10-27T10:30:00",
                    "completed_at": "2025-10-27T10:45:00",
                    "report_url": "https://storage.googleapis.com/...",
                    "summary_text": "Analysis of 15 candidates..."
                },
                "supporting_data": {
                    "total_candidates": 15,
                    "average_scores": {...}
                }
            }
        }