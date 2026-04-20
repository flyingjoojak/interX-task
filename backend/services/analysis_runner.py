import contextvars
import json
import re
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import anthropic

from config import settings
from database import SessionLocal
from models.analysis import Analysis
from models.candidate import Candidate
from models.document import Document

CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 16384
API_SLEEP_SECONDS = 0.5


MODEL_PRICING_USD_PER_MTOKEN: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "claude-opus-4-7":   {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "claude-haiku-4-5":  {"input": 0.8, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
}


_usage_context: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar(
    "usage_context", default=None
)


@contextmanager
def usage_scope(candidate_id: Optional[str], phase: str, step: Optional[str] = None):
    token = _usage_context.set({
        "candidate_id": candidate_id,
        "phase": phase,
        "step": step,
    })
    try:
        yield
    finally:
        _usage_context.reset(token)


def _estimate_cost_usd(
    model: str, input_tokens: int, output_tokens: int,
    cache_read_tokens: int = 0, cache_creation_tokens: int = 0,
) -> float:
    pricing = MODEL_PRICING_USD_PER_MTOKEN.get(model)
    if not pricing:
        return 0.0
    return round(
        (input_tokens * pricing["input"]
         + output_tokens * pricing["output"]
         + cache_read_tokens * pricing.get("cache_read", 0)
         + cache_creation_tokens * pricing.get("cache_write", 0)) / 1_000_000,
        6,
    )


def record_usage(model: str, response) -> None:
    ctx = _usage_context.get()
    if ctx is None:
        return
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    cache_creation = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    cost = _estimate_cost_usd(model, input_tokens, output_tokens, cache_read, cache_creation)

    from models.token_usage import TokenUsage
    db = SessionLocal()
    try:
        row = TokenUsage(
            candidate_id=ctx.get("candidate_id"),
            phase=ctx.get("phase") or "unknown",
            step=ctx.get("step"),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            cost_usd=cost,
        )
        db.add(row)
        db.commit()
    except Exception as exc:
        print(f"[record_usage] failed: {exc}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = _JSON_FENCE_RE.sub("", cleaned).strip()
    return cleaned


def _extract_json_payload(text: str) -> str:
    cleaned = _strip_json_fences(text)
    start_obj = cleaned.find("{")
    start_arr = cleaned.find("[")
    candidates = [i for i in (start_obj, start_arr) if i != -1]
    if not candidates:
        return cleaned
    start = min(candidates)
    end_obj = cleaned.rfind("}")
    end_arr = cleaned.rfind("]")
    end = max(end_obj, end_arr)
    if end <= start:
        return cleaned
    return cleaned[start : end + 1]


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _call_claude(prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    client = _get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    record_usage(CLAUDE_MODEL, response)
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    time.sleep(API_SLEEP_SECONDS)
    if getattr(response, "stop_reason", None) == "max_tokens":
        raise ValueError(
            f"Claude 응답이 max_tokens({max_tokens}) 한도에서 잘렸습니다. "
            "max_tokens를 늘리거나 입력 문서를 줄여주세요."
        )
    return "\n".join(parts)


def call_claude_json(prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS):
    """Claude 호출 후 JSON 파싱. 실패 시 1회 재시도."""
    last_err: Exception | None = None
    for _ in range(2):
        try:
            raw = _call_claude(prompt, max_tokens=max_tokens)
            payload = _extract_json_payload(raw)
            return json.loads(payload)
        except Exception as exc:
            last_err = exc
    raise ValueError(f"Claude JSON 파싱 실패: {last_err}")


def call_claude_text(prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    return _call_claude(prompt, max_tokens=max_tokens)


def _update_step(candidate_id: str, step: str) -> None:
    """독립 세션으로 analyses.current_step 업데이트."""
    db = SessionLocal()
    try:
        row = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).one_or_none()
        if row is None:
            row = Analysis(candidate_id=candidate_id)
            db.add(row)
        row.current_step = step
        row.step_started_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def _reset_analysis(candidate_id: str) -> None:
    db = SessionLocal()
    try:
        row = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).one_or_none()
        if row is None:
            row = Analysis(candidate_id=candidate_id)
            db.add(row)
        row.structured_data = None
        row.values_scores = None
        row.doc_reliability_score = None
        row.contradictions = None
        row.preemptive_questions = None
        row.summary = None
        row.current_step = "OCR"
        row.step_started_at = datetime.utcnow()
        row.error_message = None
        db.commit()
    finally:
        db.close()


def _save_analysis_result(
    candidate_id: str,
    structured_data: dict,
    values_scores: dict,
    doc_reliability_score: float,
    contradictions: list,
    preemptive_questions: list,
    summary: str,
) -> None:
    db = SessionLocal()
    try:
        row = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).one_or_none()
        if row is None:
            row = Analysis(candidate_id=candidate_id)
            db.add(row)
        row.structured_data = json.dumps(structured_data, ensure_ascii=False)
        row.values_scores = json.dumps(values_scores, ensure_ascii=False)
        row.doc_reliability_score = float(doc_reliability_score or 0.0)
        row.contradictions = json.dumps(contradictions, ensure_ascii=False)
        row.preemptive_questions = json.dumps(preemptive_questions, ensure_ascii=False)
        row.summary = summary or ""
        row.current_step = "완료"
        row.step_started_at = datetime.utcnow()
        row.error_message = None
        db.commit()

        cand = db.query(Candidate).filter(Candidate.id == candidate_id).one_or_none()
        if cand is not None:
            cand.status = "분석완료"
            db.commit()
    finally:
        db.close()


def _summarize_error(exc: BaseException) -> str:
    msg = str(exc) or exc.__class__.__name__
    low = msg.lower()
    if "credit balance is too low" in low or "credit balance" in low:
        return "Anthropic API 크레딧이 부족합니다. 결제 페이지에서 크레딧을 충전해주세요."
    if "invalid x-api-key" in low or "authentication" in low or "401" in msg:
        return "Anthropic API 키가 올바르지 않습니다. backend/.env의 ANTHROPIC_API_KEY를 확인해주세요."
    if "rate limit" in low or "429" in msg:
        return "Anthropic API 호출 한도에 도달했습니다. 잠시 후 다시 시도해주세요."
    if "connection" in low or "timeout" in low:
        return "Anthropic API 연결에 실패했습니다. 네트워크 상태를 확인해주세요."
    if "max_tokens" in low:
        return msg
    if "claude json 파싱 실패" in low or "expecting" in low or "json" in low:
        return f"Claude 응답이 올바른 JSON이 아닙니다. ({msg[:200]})"
    return msg[:500]


def _mark_error(candidate_id: str, message: str | None = None) -> None:
    db = SessionLocal()
    try:
        row = db.query(Analysis).filter(Analysis.candidate_id == candidate_id).one_or_none()
        if row is None:
            row = Analysis(candidate_id=candidate_id)
            db.add(row)
        row.current_step = "오류"
        row.step_started_at = datetime.utcnow()
        if message:
            row.error_message = message[:1000]
        db.commit()

        cand = db.query(Candidate).filter(Candidate.id == candidate_id).one_or_none()
        if cand is not None and cand.status == "분석중":
            cand.status = "미분석"
            db.commit()
    finally:
        db.close()


def _persist_ocr_text(
    doc_id: str,
    text: str,
    method: str | None = None,
    quality: float | None = None,
) -> None:
    """추출된 OCR 텍스트를 documents 테이블에 저장."""
    db = SessionLocal()
    try:
        row = db.query(Document).filter(Document.id == doc_id).one_or_none()
        if row is None:
            return
        row.ocr_text = text or ""
        if method:
            row.ocr_method = method
        if quality is not None:
            try:
                row.ocr_quality_score = float(quality)
            except (TypeError, ValueError):
                pass
        db.commit()
    finally:
        db.close()


def _load_documents_payload(candidate_id: str) -> list[dict]:
    db = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(Document.candidate_id == candidate_id)
            .order_by(Document.created_at.asc())
            .all()
        )
        return [
            {
                "id": d.id,
                "file_path": d.file_path,
                "file_type": d.file_type,
                "doc_type": d.doc_type,
                "ocr_text": d.ocr_text or "",
            }
            for d in docs
        ]
    finally:
        db.close()


async def run_analysis(candidate_id: str) -> None:
    from agents.analysis_graph import analysis_graph

    _reset_analysis(candidate_id)

    documents = _load_documents_payload(candidate_id)

    initial_state = {
        "candidate_id": candidate_id,
        "documents": documents,
        "resume_text": "",
        "portfolio_text": "",
        "anonymized_resume": "",
        "anonymized_portfolio": "",
        "pii_map": {},
        "structured_data": {},
        "values_scores": {},
        "doc_reliability_score": 0.0,
        "contradictions": [],
        "preemptive_questions": [],
        "summary": "",
        "error": None,
    }

    try:
        await analysis_graph.ainvoke(initial_state)
    except Exception as exc:
        _mark_error(candidate_id, _summarize_error(exc))
        raise
