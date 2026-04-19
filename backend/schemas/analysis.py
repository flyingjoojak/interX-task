from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnalysisProgressResponse(BaseModel):
    candidate_id: str
    current_step: Optional[str] = None
    step_started_at: Optional[datetime] = None
    estimated_remaining_seconds: Optional[int] = None
    progress_percent: int = 0
    error_message: Optional[str] = None


class AnalysisResponse(BaseModel):
    candidate_id: str
    structured_data: Optional[dict] = None
    values_scores: Optional[dict] = None
    doc_reliability_score: Optional[float] = None
    contradictions: Optional[list] = None
    preemptive_questions: Optional[list] = None
    summary: Optional[str] = None
    current_step: Optional[str] = None
    error_message: Optional[str] = None
