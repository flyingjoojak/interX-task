from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from agents.prompts import (
    build_contradiction_prompt,
    build_extraction_prompt,
    build_preemptive_questions_prompt,
    build_reliability_prompt,
    build_value_regeneration_prompt,
    build_value_scoring_prompt,
)
from services.evidence_verifier import merge_regenerated, verify_values_scores
from services.anonymizer import anonymize, restore
from services.analysis_runner import (
    _mark_error,
    _persist_ocr_text,
    _save_analysis_result,
    _summarize_error,
    _update_step,
    call_claude_json,
    call_claude_text,
    usage_scope,
)
from services.ocr_service import extract_resume_text
from services.portfolio_service import extract_portfolio_text


class AnalysisState(TypedDict):
    candidate_id: str
    documents: List[Dict]
    resume_text: str
    portfolio_text: str
    anonymized_resume: str
    anonymized_portfolio: str
    pii_map: Dict[str, str]
    structured_data: Dict
    values_scores: Dict
    doc_reliability_score: float
    contradictions: List[Dict]
    preemptive_questions: List[Dict]
    summary: str
    error: Optional[str]


def _node_guard(candidate_id: str, step: str, fn):
    try:
        _update_step(candidate_id, step)
        with usage_scope(candidate_id, "analysis", step):
            return fn()
    except Exception as exc:
        _mark_error(candidate_id, f"[{step}] {_summarize_error(exc)}")
        raise


def parse_documents(state: AnalysisState) -> dict:
    def _do():
        resume_text = ""
        portfolio_text = ""
        for doc in state.get("documents", []):
            doc_id = doc.get("id")
            doc_type = doc.get("doc_type")
            file_path = doc.get("file_path", "")
            file_type = doc.get("file_type", "")
            cached = (doc.get("ocr_text") or "").strip()
            if doc_type == "resume":
                if cached:
                    resume_text = cached
                elif file_path:
                    text, method, quality = extract_resume_text(file_path, file_type)
                    resume_text = text or ""
                    if doc_id:
                        _persist_ocr_text(doc_id, resume_text, method, quality)
            elif doc_type == "portfolio":
                if cached:
                    portfolio_text = cached
                elif file_path:
                    portfolio_text = extract_portfolio_text(file_path, file_type) or ""
                    if doc_id:
                        _persist_ocr_text(doc_id, portfolio_text, "claude_vision", None)
        return {"resume_text": resume_text, "portfolio_text": portfolio_text}

    return _node_guard(state["candidate_id"], "OCR", _do)


def anonymize_pii(state: AnalysisState) -> dict:
    def _do():
        resume_text = state.get("resume_text", "") or ""
        portfolio_text = state.get("portfolio_text", "") or ""
        anon_resume, pii_map_r = anonymize(resume_text)
        anon_portfolio, pii_map_p = anonymize(portfolio_text)
        merged_map = {**pii_map_r, **pii_map_p}
        return {
            "anonymized_resume": anon_resume,
            "anonymized_portfolio": anon_portfolio,
            "pii_map": merged_map,
        }

    return _node_guard(state["candidate_id"], "추출", _do)


def extract_structured_data(state: AnalysisState) -> dict:
    def _do():
        prompt = build_extraction_prompt(
            state.get("anonymized_resume", ""),
            state.get("anonymized_portfolio", ""),
        )
        data = call_claude_json(prompt)
        if not isinstance(data, dict):
            data = {}
        return {"structured_data": data}

    return _node_guard(state["candidate_id"], "추출", _do)


def score_12_values(state: AnalysisState) -> dict:
    def _do():
        prompt = build_value_scoring_prompt(
            state.get("anonymized_resume", ""),
            state.get("structured_data", {}) or {},
        )
        data = call_claude_json(prompt)
        if not isinstance(data, dict):
            data = {}
        return {"values_scores": data}

    return _node_guard(state["candidate_id"], "가치매핑", _do)


def self_verify_evidence(state: AnalysisState) -> dict:
    """values_scores 의 examples 가 이력서 원문에 실제 존재하는지 검증.

    - substring + token-overlap 으로 sanity check
    - 점수가 높은데 증거가 부실한 가치는 1회 재생성
    - 재생성 결과도 다시 검증해 verification 메타데이터에 기록
    """
    def _do():
        values_scores = state.get("values_scores", {}) or {}
        resume_text = state.get("anonymized_resume", "") or ""
        portfolio_text = state.get("anonymized_portfolio", "") or ""
        source = (resume_text + "\n\n" + portfolio_text).strip()

        annotated, failed = verify_values_scores(values_scores, source)

        if not failed:
            return {"values_scores": annotated}

        try:
            prompt = build_value_regeneration_prompt(resume_text, failed)
            regenerated = call_claude_json(prompt, max_tokens=4096)
            if isinstance(regenerated, dict):
                annotated = merge_regenerated(annotated, regenerated, source)
        except Exception as exc:
            print(f"[self_verify] regeneration failed: {exc}")

        return {"values_scores": annotated}

    return _node_guard(state["candidate_id"], "가치매핑", _do)


def calculate_doc_reliability(state: AnalysisState) -> dict:
    def _do():
        prompt = build_reliability_prompt(
            state.get("anonymized_resume", ""),
            state.get("anonymized_portfolio", ""),
        )
        data = call_claude_json(prompt)
        if isinstance(data, dict):
            score = float(data.get("score", 0) or 0)
        else:
            score = 0.0
        return {"doc_reliability_score": score}

    return _node_guard(state["candidate_id"], "가치매핑", _do)


def detect_contradictions(state: AnalysisState) -> dict:
    def _do():
        prompt = build_contradiction_prompt(
            state.get("anonymized_resume", ""),
            state.get("anonymized_portfolio", ""),
            state.get("structured_data", {}) or {},
        )
        data = call_claude_json(prompt)
        if not isinstance(data, list):
            data = []
        return {"contradictions": data}

    return _node_guard(state["candidate_id"], "모순탐지", _do)


def generate_preemptive_questions(state: AnalysisState) -> dict:
    def _do():
        prompt = build_preemptive_questions_prompt(
            state.get("structured_data", {}) or {},
            state.get("values_scores", {}) or {},
            state.get("contradictions", []) or [],
        )
        data = call_claude_json(prompt)
        if not isinstance(data, list):
            data = []
        return {"preemptive_questions": data}

    return _node_guard(state["candidate_id"], "질문생성", _do)


def _build_summary(
    structured_data: dict, values_scores: dict, contradictions: list, reliability: float
) -> str:
    top_values = []
    if isinstance(values_scores, dict):
        scored = []
        for name, payload in values_scores.items():
            if isinstance(payload, dict):
                scored.append((name, int(payload.get("score", 0) or 0)))
        scored.sort(key=lambda x: x[1], reverse=True)
        top_values = scored[:3]

    career_count = len((structured_data or {}).get("career", []) or [])
    skills = (structured_data or {}).get("skills", []) or []
    top_skills = ", ".join(skills[:5])

    top_values_str = ", ".join(f"{n}({s})" for n, s in top_values) or "(정보 부족)"
    contradiction_summary = (
        f"{len(contradictions)}건의 불일치 탐지" if contradictions else "모순 없음"
    )

    return (
        f"경력 {career_count}건, 주요 기술: {top_skills or '(미기재)'}.\n"
        f"상위 가치: {top_values_str}. 문서 신뢰도 {reliability:.0f}/100. {contradiction_summary}."
    )


def compile_and_restore(state: AnalysisState) -> dict:
    candidate_id = state["candidate_id"]
    try:
        _update_step(candidate_id, "완료")

        pii_map = state.get("pii_map", {}) or {}
        structured_data = state.get("structured_data", {}) or {}
        values_scores = state.get("values_scores", {}) or {}
        contradictions = state.get("contradictions", []) or []
        preemptive_questions = state.get("preemptive_questions", []) or []

        import json as _json

        def _restore_obj(obj):
            serialized = _json.dumps(obj, ensure_ascii=False)
            restored = restore(serialized, pii_map)
            try:
                return _json.loads(restored)
            except Exception:
                return obj

        structured_data = _restore_obj(structured_data)
        values_scores = _restore_obj(values_scores)
        contradictions = _restore_obj(contradictions)
        preemptive_questions = _restore_obj(preemptive_questions)

        reliability = float(state.get("doc_reliability_score", 0.0) or 0.0)
        summary = _build_summary(
            structured_data, values_scores, contradictions, reliability
        )

        _save_analysis_result(
            candidate_id=candidate_id,
            structured_data=structured_data,
            values_scores=values_scores,
            doc_reliability_score=reliability,
            contradictions=contradictions,
            preemptive_questions=preemptive_questions,
            summary=summary,
        )

        return {
            "structured_data": structured_data,
            "values_scores": values_scores,
            "contradictions": contradictions,
            "preemptive_questions": preemptive_questions,
            "summary": summary,
        }
    except Exception as exc:
        _mark_error(candidate_id, f"[완료] {_summarize_error(exc)}")
        raise


def build_analysis_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node("parse_documents", parse_documents)
    graph.add_node("anonymize_pii", anonymize_pii)
    graph.add_node("extract_structured_data", extract_structured_data)
    graph.add_node("score_12_values", score_12_values)
    graph.add_node("self_verify_evidence", self_verify_evidence)
    graph.add_node("calculate_doc_reliability", calculate_doc_reliability)
    graph.add_node("detect_contradictions", detect_contradictions)
    graph.add_node("generate_preemptive_questions", generate_preemptive_questions)
    graph.add_node("compile_and_restore", compile_and_restore)

    graph.set_entry_point("parse_documents")
    graph.add_edge("parse_documents", "anonymize_pii")
    graph.add_edge("anonymize_pii", "extract_structured_data")
    graph.add_edge("extract_structured_data", "score_12_values")
    graph.add_edge("score_12_values", "self_verify_evidence")
    graph.add_edge("self_verify_evidence", "calculate_doc_reliability")
    graph.add_edge("calculate_doc_reliability", "detect_contradictions")
    graph.add_edge("detect_contradictions", "generate_preemptive_questions")
    graph.add_edge("generate_preemptive_questions", "compile_and_restore")
    graph.add_edge("compile_and_restore", END)

    return graph.compile()


analysis_graph = build_analysis_graph()
