import io
import json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.analysis import Analysis
from models.candidate import Candidate
from models.interview import InterviewSession, QAPair
from models.user import User
from schemas.analysis import AnalysisProgressResponse, AnalysisResponse
from services.analysis_runner import run_analysis
from services.pdf_export import generate_pdf
from utils.jwt_utils import get_current_user

router = APIRouter()


async def _run_analysis_background(candidate_id: str) -> None:
    try:
        await run_analysis(candidate_id)
    except Exception as exc:
        print(f"[analysis] background task failed for {candidate_id}: {exc}")

STEP_DURATIONS = {
    "OCR": 15,
    "추출": 20,
    "가치매핑": 25,
    "모순탐지": 15,
    "질문생성": 15,
}
STEP_ORDER = ["OCR", "추출", "가치매핑", "모순탐지", "질문생성", "완료"]
PROCESSING_STEPS = STEP_ORDER[:-1]


def _get_candidate_or_404(db: Session, candidate_id: str) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="후보자를 찾을 수 없습니다")
    return candidate


def _safe_json_loads(raw):
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _compute_progress(analysis: Analysis, candidate_id: str) -> AnalysisProgressResponse:
    if analysis is None:
        return AnalysisProgressResponse(
            candidate_id=candidate_id,
            current_step=None,
            step_started_at=None,
            estimated_remaining_seconds=None,
            progress_percent=0,
        )

    current_step = analysis.current_step
    step_started_at = analysis.step_started_at

    if current_step == "완료":
        return AnalysisProgressResponse(
            candidate_id=candidate_id,
            current_step=current_step,
            step_started_at=step_started_at,
            estimated_remaining_seconds=0,
            progress_percent=100,
        )

    if current_step == "오류":
        return AnalysisProgressResponse(
            candidate_id=candidate_id,
            current_step=current_step,
            step_started_at=step_started_at,
            estimated_remaining_seconds=None,
            progress_percent=0,
        )

    if current_step not in PROCESSING_STEPS:
        total = sum(STEP_DURATIONS.values())
        return AnalysisProgressResponse(
            candidate_id=candidate_id,
            current_step=current_step,
            step_started_at=step_started_at,
            estimated_remaining_seconds=total,
            progress_percent=0,
        )

    idx = PROCESSING_STEPS.index(current_step)
    completed = idx
    progress_percent = int(completed / len(PROCESSING_STEPS) * 100)

    current_duration = STEP_DURATIONS[current_step]
    if step_started_at is None:
        current_remaining = current_duration
    else:
        elapsed = (datetime.utcnow() - step_started_at).total_seconds()
        current_remaining = max(0, int(current_duration - elapsed))

    later_steps_total = sum(STEP_DURATIONS[s] for s in PROCESSING_STEPS[idx + 1 :])
    estimated = current_remaining + later_steps_total

    return AnalysisProgressResponse(
        candidate_id=candidate_id,
        current_step=current_step,
        step_started_at=step_started_at,
        estimated_remaining_seconds=estimated,
        progress_percent=progress_percent,
    )


@router.post("/candidates/{candidate_id}/analysis")
def start_analysis(
    candidate_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(db, candidate_id)

    existing = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).first()
    if existing is not None:
        db.delete(existing)
        db.flush()

    fresh = Analysis(
        candidate_id=candidate_id,
        current_step="OCR",
        step_started_at=datetime.utcnow(),
    )
    db.add(fresh)

    cand = db.query(Candidate).filter(Candidate.id == candidate_id).one()
    cand.status = "분석중"

    db.commit()

    background_tasks.add_task(_run_analysis_background, candidate_id)
    return {"message": "분석이 시작되었습니다"}


@router.get("/candidates/{candidate_id}/analysis/progress", response_model=AnalysisProgressResponse)
def get_progress(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(db, candidate_id)
    analysis = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).first()
    return _compute_progress(analysis, candidate_id)


@router.get("/candidates/{candidate_id}/analysis", response_model=AnalysisResponse)
def get_analysis(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(db, candidate_id)
    analysis = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).first()
    if analysis is None:
        return AnalysisResponse(candidate_id=candidate_id)

    return AnalysisResponse(
        candidate_id=candidate_id,
        structured_data=_safe_json_loads(analysis.structured_data),
        values_scores=_safe_json_loads(analysis.values_scores),
        doc_reliability_score=analysis.doc_reliability_score,
        contradictions=_safe_json_loads(analysis.contradictions),
        preemptive_questions=_safe_json_loads(analysis.preemptive_questions),
        summary=analysis.summary,
        current_step=analysis.current_step,
    )


@router.delete("/candidates/{candidate_id}/analysis")
def delete_analysis(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(db, candidate_id)

    analysis = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).first()
    if analysis is not None:
        db.delete(analysis)

    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.candidate_id == candidate_id)
        .all()
    )
    for sess in sessions:
        db.query(QAPair).filter(QAPair.session_id == sess.id).delete()

    db.commit()
    return {"message": "분석이 초기화되었습니다"}


@router.get("/candidates/{candidate_id}/report/pdf")
async def get_report_pdf(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(db, candidate_id)
    pdf_bytes = await generate_pdf(candidate_id)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{candidate_id}.pdf"'},
    )
