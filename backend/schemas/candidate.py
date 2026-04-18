from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

VALID_STATUSES = {
    "미분석",
    "분석중",
    "분석완료",
    "서류합격",
    "서류탈락",
    "면접합격",
    "면접탈락",
    "최종합격",
    "최종탈락",
}


class CandidateCreate(BaseModel):
    name: str
    birth_year: Optional[int] = None
    position: Optional[str] = None
    interviewer_memo: Optional[str] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    birth_year: Optional[int] = None
    position: Optional[str] = None
    interviewer_memo: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str


class CandidateResponse(BaseModel):
    id: str
    name: str
    birth_year: Optional[int] = None
    position: Optional[str] = None
    interviewer_memo: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    avg_value_score: Optional[float] = None
    doc_reliability_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
