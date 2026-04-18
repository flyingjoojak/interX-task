import json
import os
import shutil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.analysis import Analysis
from models.candidate import Candidate
from models.user import User
from schemas.candidate import (
    VALID_STATUSES,
    CandidateCreate,
    CandidateResponse,
    CandidateUpdate,
    StatusUpdate,
)
from utils.jwt_utils import get_current_user

router = APIRouter()


def _avg_value_score(values_scores_json: Optional[str]) -> Optional[float]:
    if not values_scores_json:
        return None
    try:
        data = json.loads(values_scores_json)
    except (json.JSONDecodeError, TypeError):
        return None

    scores = []
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, dict) and isinstance(v.get("score"), (int, float)):
                scores.append(float(v["score"]))
            elif isinstance(v, (int, float)):
                scores.append(float(v))
    elif isinstance(data, list):
        for v in data:
            if isinstance(v, dict) and isinstance(v.get("score"), (int, float)):
                scores.append(float(v["score"]))

    if not scores:
        return None
    return sum(scores) / len(scores)


def _to_response(candidate: Candidate, analysis: Optional[Analysis]) -> CandidateResponse:
    avg = _avg_value_score(analysis.values_scores) if analysis else None
    reliability = analysis.doc_reliability_score if analysis else None
    return CandidateResponse(
        id=candidate.id,
        name=candidate.name,
        birth_year=candidate.birth_year,
        position=candidate.position,
        interviewer_memo=candidate.interviewer_memo,
        status=candidate.status,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        avg_value_score=avg,
        doc_reliability_score=reliability,
    )


def _get_candidate_or_404(db: Session, candidate_id: str) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="후보자를 찾을 수 없습니다")
    return candidate


@router.get("/", response_model=list[CandidateResponse])
def list_candidates(
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Candidate)
    if status is not None:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"유효하지 않은 상태값입니다: {status}")
        query = query.filter(Candidate.status == status)
    candidates = query.order_by(Candidate.created_at.desc()).all()

    if not candidates:
        return []

    ids = [c.id for c in candidates]
    analyses = db.query(Analysis).filter(Analysis.candidate_id.in_(ids)).all()
    analysis_map = {a.candidate_id: a for a in analyses}

    return [_to_response(c, analysis_map.get(c.id)) for c in candidates]


@router.post("/", response_model=CandidateResponse)
def create_candidate(
    body: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = Candidate(
        name=body.name,
        birth_year=body.birth_year,
        position=body.position,
        interviewer_memo=body.interviewer_memo,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return _to_response(candidate, None)


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_candidate_or_404(db, candidate_id)
    analysis = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).first()
    return _to_response(candidate, analysis)


@router.patch("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: str,
    body: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_candidate_or_404(db, candidate_id)
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    analysis = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).first()
    return _to_response(candidate, analysis)


@router.patch("/{candidate_id}/status", response_model=CandidateResponse)
def update_status(
    candidate_id: str,
    body: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 상태값입니다: {body.status}")
    candidate = _get_candidate_or_404(db, candidate_id)
    candidate.status = body.status
    db.commit()
    db.refresh(candidate)
    analysis = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).first()
    return _to_response(candidate, analysis)


@router.delete("/{candidate_id}")
def delete_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_candidate_or_404(db, candidate_id)

    upload_dir = os.path.join(settings.UPLOAD_DIR, candidate_id)
    shutil.rmtree(upload_dir, ignore_errors=True)

    db.delete(candidate)
    db.commit()
    return {"message": "삭제 완료"}
