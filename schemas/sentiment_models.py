# models/sentiment_models.py

from pydantic import BaseModel
from typing import List, Dict, Optional

class SentimentQueryRequest(BaseModel):
    job_id: str
    query: str
    user_email: str

class SentimentQueryResponse(BaseModel):
    job_id: str
    query: str
    answer: str
    supporting_data: Dict
    sources: List[Dict]
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "sent-abc123",
                "query": "What are the main reasons for employee dissatisfaction?",
                "answer": "Based on the analysis...",
                "supporting_data": {
                    "total_analyzed": 125,
                    "negative_count": 45
                },
                "sources": []
            }
        }