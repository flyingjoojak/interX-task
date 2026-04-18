import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.candidate import Candidate
from models.interview import InterviewSession, QAPair
from models.user import User
from schemas.interview import (
    AnswerQARequest,
    CreateQARequest,
    QAPairResponse,
    SessionResponse,
)
from utils.jwt_utils import get_current_user

router = APIRouter()


def _get_candidate_or_404(db: Session, candidate_id: str) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="후보자를 찾을 수 없습니다")
    return candidate


def _safe_json_loads(raw: Optional[str]):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _qa_to_response(qa: QAPair) -> QAPairResponse:
    return QAPairResponse(
        id=qa.id,
        session_id=qa.session_id,
        question_source=qa.question_source,
        question_text=qa.question_text,
        answer_text=qa.answer_text,
        followup_questions=_safe_json_loads(qa.followup_questions),
        parent_qa_id=qa.parent_qa_id,
        order_index=qa.order_index,
        created_at=qa.created_at,
        answered_at=qa.answered_at,
    )


def _session_to_response(session: InterviewSession, qa_pairs: list[QAPair]) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        candidate_id=session.candidate_id,
        last_accessed_at=session.last_accessed_at,
        created_at=session.created_at,
        qa_pairs=[_qa_to_response(q) for q in qa_pairs],
    )


def _load_session_with_pairs(db: Session, session: InterviewSession) -> SessionResponse:
    pairs = (
        db.query(QAPair)
        .filter(QAPair.session_id == session.id)
        .order_by(QAPair.order_index.asc())
        .all()
    )
    return _session_to_response(session, pairs)


@router.post("/candidates/{candidate_id}/interview/session", response_model=SessionResponse)
def create_or_get_session(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(db, candidate_id)

    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.candidate_id == candidate_id)
        .one_or_none()
    )
    if session is None:
        session = InterviewSession(candidate_id=candidate_id, last_accessed_at=datetime.utcnow())
        db.add(session)
        db.commit()
        db.refresh(session)
    else:
        session.last_accessed_at = datetime.utcnow()
        db.commit()
        db.refresh(session)

    return _load_session_with_pairs(db, session)


@router.get("/candidates/{candidate_id}/interview/session", response_model=SessionResponse)
def get_session(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(db, candidate_id)
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.candidate_id == candidate_id)
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션이 없습니다")
    return _load_session_with_pairs(db, session)


@router.delete("/candidates/{candidate_id}/interview/session")
def reset_session(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(db, candidate_id)
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.candidate_id == candidate_id)
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션이 없습니다")

    db.query(QAPair).filter(QAPair.session_id == session.id).delete()
    session.last_accessed_at = None
    db.commit()
    return {"message": "세션이 초기화되었습니다"}


@router.post("/interview/qa", response_model=QAPairResponse)
def create_qa(
    body: CreateQARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == body.session_id)
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다")

    max_order = (
        db.query(func.max(QAPair.order_index))
        .filter(QAPair.session_id == body.session_id)
        .scalar()
    )
    next_order = (max_order or 0) + 1

    qa = QAPair(
        session_id=body.session_id,
        question_source=body.question_source,
        question_text=body.question_text,
        parent_qa_id=body.parent_qa_id,
        order_index=next_order,
    )
    db.add(qa)
    session.last_accessed_at = datetime.utcnow()
    db.commit()
    db.refresh(qa)
    return _qa_to_response(qa)


@router.patch("/interview/qa/{qa_id}", response_model=QAPairResponse)
async def answer_qa(
    qa_id: str,
    body: AnswerQARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    qa = db.query(QAPair).filter(QAPair.id == qa_id).one_or_none()
    if qa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Q&A를 찾을 수 없습니다")

    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == qa.session_id)
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다")

    qa.answer_text = body.answer_text
    qa.answered_at = datetime.utcnow()
    session.last_accessed_at = datetime.utcnow()
    db.commit()

    followups: list = []
    try:
        from agents.interview_graph import generate_followup_questions

        followups = await generate_followup_questions(
            candidate_id=session.candidate_id,
            question=qa.question_text or "",
            answer=body.answer_text or "",
            session_id=session.id,
        )
    except Exception:
        followups = []

    qa.followup_questions = json.dumps(followups or [], ensure_ascii=False)
    db.commit()
    db.refresh(qa)
    return _qa_to_response(qa)
