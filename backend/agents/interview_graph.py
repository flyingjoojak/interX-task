import json
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from agents.prompts import (
    JSON_ONLY_SUFFIX,
    KOREAN_INSTRUCTION,
    build_followup_prompt,
)
from database import SessionLocal
from models.analysis import Analysis
from models.interview import InterviewSession, QAPair
from services.analysis_runner import call_claude_json


ANSWER_ANALYSIS_PROMPT = """당신은 실시간 면접 답변의 취약점을 빠르게 짚어내는 분석가입니다. 아래 질문과 답변을 읽고 모호성/불일치/과장 관점에서 한 문장씩 간단히 평가하세요.

[분석 지침]
- `vagueness`: 답변이 추상적이거나 구체적 수치/사례가 없는지.
- `inconsistency`: 이력서 요약 또는 이전 대화와 상충되는 지점.
- `exaggeration`: 검증 불가능한 성과 주장이나 1인칭 과장 의심 지점.
- 각 항목에서 문제가 없으면 빈 문자열("")을 반환.

[이력서 요약]
{resume_summary}

[이전 Q&A (최근 3개)]
{history}

[현재 질문]
{question}

[후보자 답변]
{answer}

[출력 JSON 스키마]
{{
  "vagueness": "",
  "inconsistency": "",
  "exaggeration": ""
}}

{korean_instruction}
{json_only_suffix}
"""


def _build_answer_analysis_prompt(
    resume_summary: dict, history: list, question: str, answer: str
) -> str:
    recent = (history or [])[-3:]
    return ANSWER_ANALYSIS_PROMPT.format(
        resume_summary=json.dumps(resume_summary or {}, ensure_ascii=False, indent=2),
        history=json.dumps(recent, ensure_ascii=False, indent=2),
        question=question or "(없음)",
        answer=answer or "(없음)",
        korean_instruction=KOREAN_INSTRUCTION,
        json_only_suffix=JSON_ONLY_SUFFIX,
    )


class InterviewState(TypedDict):
    candidate_id: str
    resume_summary: dict
    values_context: dict
    current_question: str
    current_answer: str
    conversation_history: list
    answer_analysis: dict
    followup_questions: list


def _safe_json_loads(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _load_recent_history(session_id: str, limit: int = 3) -> list:
    db = SessionLocal()
    try:
        rows = (
            db.query(QAPair)
            .filter(QAPair.session_id == session_id)
            .filter(QAPair.answer_text.isnot(None))
            .order_by(QAPair.order_index.desc())
            .limit(limit)
            .all()
        )
        pairs = [{"q": r.question_text or "", "a": r.answer_text or ""} for r in rows]
        pairs.reverse()
        return pairs
    finally:
        db.close()


def _load_session_id(candidate_id: str) -> Optional[str]:
    db = SessionLocal()
    try:
        sess = (
            db.query(InterviewSession)
            .filter(InterviewSession.candidate_id == candidate_id)
            .one_or_none()
        )
        return sess.id if sess else None
    finally:
        db.close()


def prepare_context(state: InterviewState) -> dict:
    candidate_id = state["candidate_id"]
    db = SessionLocal()
    try:
        analysis = (
            db.query(Analysis)
            .filter(Analysis.candidate_id == candidate_id)
            .one_or_none()
        )
        structured = _safe_json_loads(analysis.structured_data) if analysis else None
        values = _safe_json_loads(analysis.values_scores) if analysis else None
    finally:
        db.close()

    resume_summary = structured if isinstance(structured, dict) else {}

    values_context: Dict[str, Any] = {}
    if isinstance(values, dict):
        low = {}
        for name, payload in values.items():
            if isinstance(payload, dict):
                score = payload.get("score")
                if isinstance(score, (int, float)) and score < 40:
                    low[name] = payload
        values_context = low

    session_id = _load_session_id(candidate_id)
    history = _load_recent_history(session_id) if session_id else []

    return {
        "resume_summary": resume_summary,
        "values_context": values_context,
        "conversation_history": history,
    }


def analyze_answer(state: InterviewState) -> dict:
    prompt = _build_answer_analysis_prompt(
        state.get("resume_summary") or {},
        state.get("conversation_history") or [],
        state.get("current_question") or "",
        state.get("current_answer") or "",
    )
    try:
        data = call_claude_json(prompt, max_tokens=512)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    return {
        "answer_analysis": {
            "vagueness": str(data.get("vagueness") or ""),
            "inconsistency": str(data.get("inconsistency") or ""),
            "exaggeration": str(data.get("exaggeration") or ""),
        }
    }


def generate_followups(state: InterviewState) -> dict:
    prompt = build_followup_prompt(
        state.get("resume_summary") or {},
        state.get("current_question") or "",
        state.get("current_answer") or "",
        state.get("conversation_history") or [],
    )
    try:
        data = call_claude_json(prompt, max_tokens=1024)
        if not isinstance(data, list):
            data = []
    except Exception:
        data = []
    return {"followup_questions": data}


def rank_and_filter(state: InterviewState) -> dict:
    items = state.get("followup_questions") or []
    cleaned: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        priority_raw = item.get("priority")
        try:
            priority = int(priority_raw) if priority_raw is not None else 99
        except (TypeError, ValueError):
            priority = 99
        cleaned.append(
            {
                "question": question,
                "reasoning": str(item.get("reasoning") or ""),
                "priority": priority,
            }
        )

    cleaned.sort(key=lambda x: x["priority"])
    return {"followup_questions": cleaned[:5]}


def build_interview_graph():
    graph = StateGraph(InterviewState)
    graph.add_node("prepare_context", prepare_context)
    graph.add_node("analyze_answer", analyze_answer)
    graph.add_node("generate_followups", generate_followups)
    graph.add_node("rank_and_filter", rank_and_filter)

    graph.set_entry_point("prepare_context")
    graph.add_edge("prepare_context", "analyze_answer")
    graph.add_edge("analyze_answer", "generate_followups")
    graph.add_edge("generate_followups", "rank_and_filter")
    graph.add_edge("rank_and_filter", END)

    return graph.compile()


interview_graph = build_interview_graph()


async def generate_followup_questions(
    candidate_id: str,
    question: str,
    answer: str,
    session_id: str,
) -> list[dict]:
    """interview_graph.ainvoke 래퍼. 꼬리질문 리스트 반환."""
    initial_state: InterviewState = {
        "candidate_id": candidate_id,
        "resume_summary": {},
        "values_context": {},
        "current_question": question or "",
        "current_answer": answer or "",
        "conversation_history": [],
        "answer_analysis": {},
        "followup_questions": [],
    }
    try:
        result = await interview_graph.ainvoke(initial_state)
    except Exception:
        return []
    return result.get("followup_questions") or []
