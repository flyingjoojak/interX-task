import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(Text, ForeignKey("candidates.id", ondelete="CASCADE"), unique=True, nullable=False)
    structured_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    values_scores: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    contradictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    preemptive_questions: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
