from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: str
    candidate_id: str
    original_name: str
    file_path: str
    file_type: str
    doc_type: str
    ocr_text: Optional[str] = None
    ocr_method: Optional[str] = None
    ocr_quality_score: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
