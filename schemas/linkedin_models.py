"""
Pydantic models for LinkedIn Scouting feature
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime


class LinkedInScoutRequest(BaseModel):
    """Request model for LinkedIn scouting"""
    jd_filename: Optional[str] = Field(None, description="Job description filename")
    job_description: str = Field(..., description="Full job description text")
    location: str = Field(..., description="Search location (e.g., 'San Francisco, CA', 'Remote')")
    min_experience: Optional[int] = Field(None, ge=0, description="Minimum years of experience")
    max_experience: Optional[int] = Field(None, ge=0, description="Maximum years of experience")
    num_candidates: int = Field(default=10, ge=1, le=50, description="Number of candidates to find")
    open_to_work_only: bool = Field(default=False, description="Filter for 'Open to Work' candidates only")
    user_email: str = Field(default="guest@vantage.ai", description="User email for tracking")
    organization_id: str = Field(default="default_org", description="Organization ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "jd_filename": "senior_data_scientist_jd.pdf",
                "job_description": "We are looking for a Senior Data Scientist with 5+ years of experience...",
                "location": "San Francisco, CA",
                "min_experience": 5,
                "max_experience": 10,
                "num_candidates": 15,
                "open_to_work_only": True,
                "user_email": "recruiter@company.com",
                "organization_id": "acme_corp"
            }
        }


class LinkedInExperience(BaseModel):
    """LinkedIn work experience entry"""
    title: str
    company: str
    duration: str = ""
    description: str = ""


class LinkedInEducation(BaseModel):
    """LinkedIn education entry"""
    school: str
    degree: str = ""
    field: str = ""
    years: str = ""


class LinkedInProfile(BaseModel):
    """Scraped LinkedIn profile data"""
    profile_url: str
    name: str
    headline: str = ""
    location: str = ""
    about: str = ""
    experience: List[LinkedInExperience] = []
    education: List[LinkedInEducation] = []
    skills: List[str] = []
    raw_text: str = ""
    scraped_at: str
    error: Optional[str] = None


class LinkedInAnalysis(BaseModel):
    """Analysis results for a candidate"""
    match_score: float = Field(..., ge=0, le=100)
    skills_score: float = Field(..., ge=0, le=100)
    experience_score: float = Field(..., ge=0, le=100)
    education_score: float = Field(..., ge=0, le=100)
    key_strengths: str
    gaps: str
    recommendation: str
    match_reasoning: str
    job_hopping_risk: Optional[str] = None
    job_hopping_detail: Optional[str] = None


class LinkedInCandidateResult(BaseModel):
    """Complete result for a single candidate"""
    result_id: str
    job_id: str
    rank: Optional[int] = None
    linkedin_profile_id: Optional[str] = None
    linkedin_profile_url: str
    full_name: str
    headline: str
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    current_tenure_years: Optional[float] = None
    location: Optional[str] = None
    total_experience_years: Optional[float] = None
    num_positions: Optional[int] = None
    skills: List[str] = []
    open_to_work: Optional[bool] = None
    match_score: float
    skills_score: float
    experience_score: float
    education_score: float
    key_strengths: str
    gaps: str
    recommendation: str
    match_reasoning: str
    job_hopping_risk: Optional[str] = None
    job_hopping_detail: Optional[str] = None
    summary_text: Optional[str] = None
    created_at: str
    raw_profile_json: Optional[str] = None


class LinkedInJobResponse(BaseModel):
    """Response model for a LinkedIn scouting job"""
    job_id: str
    jd_filename: Optional[str] = None
    job_description: str
    location: str
    min_experience: Optional[int] = None
    max_experience: Optional[int] = None
    num_candidates: int
    open_to_work_only: bool
    user_email: str
    organization_id: str
    status: str = Field(..., description="Status: pending, processing, completed, failed")
    created_at: str
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    summary_text: Optional[str] = None
    report_url: Optional[str] = None  # Excel download URL
    total_found: Optional[int] = None
    total_analyzed: Optional[int] = None
    error_message: Optional[str] = None
    results: List[LinkedInCandidateResult] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "linkedin_scout_abc123",
                "jd_filename": "data_scientist_jd.pdf",
                "job_description": "Looking for Data Scientist...",
                "location": "San Francisco, CA",
                "min_experience": 3,
                "max_experience": 8,
                "num_candidates": 10,
                "open_to_work_only": True,
                "user_email": "recruiter@company.com",
                "organization_id": "acme_corp",
                "status": "completed",
                "total_found": 15,
                "total_analyzed": 10,
                "created_at": "2025-11-14T10:00:00Z",
                "completed_at": "2025-11-14T10:05:00Z",
                "results": [],
                "report_url": "https://storage.googleapis.com/bucket/reports/linkedin_scout_abc123.pdf"
            }
        }


class LinkedInJobSummary(BaseModel):
    """Summary model for listing jobs"""
    job_id: str
    jd_filename: Optional[str] = None
    location: str
    num_candidates: int
    open_to_work_only: bool
    status: str
    total_found: Optional[int] = None
    total_analyzed: Optional[int] = None
    created_at: str
    user_email: str


class LinkedInScoutResponse(BaseModel):
    """Initial response when starting a LinkedIn scout job"""
    job_id: str
    message: str
    status: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "linkedin_scout_abc123",
                "message": "LinkedIn scouting job started successfully",
                "status": "processing"
            }
        }
