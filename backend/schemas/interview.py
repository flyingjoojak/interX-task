from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class QAPairResponse(BaseModel):
    id: str
    session_id: str
    question_source: str
    question_text: str
    answer_text: Optional[str] = None
    followup_questions: Optional[list] = None
    parent_qa_id: Optional[str] = None
    order_index: int
    created_at: datetime
    answered_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    id: str
    candidate_id: str
    last_accessed_at: Optional[datetime] = None
    created_at: datetime
    qa_pairs: list[QAPairResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CreateQARequest(BaseModel):
    session_id: str
    question_source: str
    question_text: str
    parent_qa_id: Optional[str] = None


class AnswerQARequest(BaseModel):
    answer_text: str
