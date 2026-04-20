"""evidence/examples 자가 검증 모듈.

values_scores 의 각 가치마다 examples(원문 인용)가 실제로 이력서 원문에
존재하는지 substring + token-overlap 두 축으로 확인한다.
hallucination 의심 가치는 caller 가 1회까지 재생성하도록 식별만 해 준다.
"""
from __future__ import annotations

import re
from typing import Iterable


_PUNCT_RE = re.compile(r"[\s\W_]+", re.UNICODE)
_TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+", re.UNICODE)


def _normalize(text: str) -> str:
    return _PUNCT_RE.sub("", (text or "").lower())


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) >= 2]


def token_overlap_ratio(quote: str, source: str) -> float:
    """quote 토큰 중 source 토큰에 등장하는 비율."""
    q_tokens = _tokenize(quote)
    if not q_tokens:
        return 0.0
    s_tokens = set(_tokenize(source))
    if not s_tokens:
        return 0.0
    hits = sum(1 for t in q_tokens if t in s_tokens)
    return hits / len(q_tokens)


def is_example_supported(example: str, source_text: str,
                         min_overlap: float = 0.6) -> bool:
    """example 이 source_text 에 의해 충분히 뒷받침되는지 판정.

    1) normalize 후 substring 일치 → True
    2) token-overlap 비율 >= min_overlap → True
    3) 둘 다 실패 → False
    """
    if not example or not example.strip():
        return False
    if not source_text or not source_text.strip():
        return False

    norm_src = _normalize(source_text)
    norm_quote = _normalize(example)
    if norm_quote and norm_quote in norm_src:
        return True

    return token_overlap_ratio(example, source_text) >= min_overlap


def verify_values_scores(
    values_scores: dict, source_text: str,
    min_supported_ratio: float = 0.5,
) -> tuple[dict, dict]:
    """values_scores 각 항목에 verification 메타데이터를 덧붙이고,
    재생성 대상 가치 dict 를 반환한다.

    Returns:
        (annotated_values, failed_values)
        annotated_values: 원본 + verification 필드 추가
        failed_values: { 가치명: { score, evidence, unverified_examples } } — 재생성 대상
    """
    if not isinstance(values_scores, dict):
        return values_scores, {}

    annotated: dict = {}
    failed: dict = {}

    for name, payload in values_scores.items():
        if not isinstance(payload, dict):
            annotated[name] = payload
            continue

        examples = payload.get("examples") or []
        if not isinstance(examples, list):
            examples = []

        verified: list[str] = []
        unverified: list[str] = []
        for ex in examples:
            if not isinstance(ex, str):
                continue
            if is_example_supported(ex, source_text):
                verified.append(ex)
            else:
                unverified.append(ex)

        total = len(verified) + len(unverified)
        ratio = (len(verified) / total) if total else 1.0

        annotated_payload = dict(payload)
        annotated_payload["verification"] = {
            "verified_examples": verified,
            "unverified_examples": unverified,
            "verified_ratio": round(ratio, 3),
        }
        annotated[name] = annotated_payload

        score = payload.get("score")
        is_high_score = isinstance(score, (int, float)) and score >= 40
        has_unverified = len(unverified) > 0
        too_unsupported = total > 0 and ratio < min_supported_ratio

        # 재생성 대상: 점수가 높은데(>=40) 증거가 부실한 경우
        if is_high_score and (too_unsupported or (has_unverified and total >= 2)):
            failed[name] = {
                "score": score,
                "evidence": payload.get("evidence", ""),
                "unverified_examples": unverified,
                "verified_ratio": round(ratio, 3),
            }

    return annotated, failed


def merge_regenerated(
    annotated: dict, regenerated: dict, source_text: str
) -> dict:
    """재생성된 결과를 기존 annotated 에 병합하면서 verification 도 다시 계산."""
    if not isinstance(regenerated, dict):
        return annotated

    merged = dict(annotated)
    for name, payload in regenerated.items():
        if not isinstance(payload, dict) or name not in merged:
            continue

        examples = payload.get("examples") or []
        verified: list[str] = []
        unverified: list[str] = []
        for ex in examples:
            if not isinstance(ex, str):
                continue
            if is_example_supported(ex, source_text):
                verified.append(ex)
            else:
                unverified.append(ex)

        total = len(verified) + len(unverified)
        ratio = (len(verified) / total) if total else 1.0

        new_payload = dict(payload)
        new_payload["verification"] = {
            "verified_examples": verified,
            "unverified_examples": unverified,
            "verified_ratio": round(ratio, 3),
            "regenerated": True,
        }
        merged[name] = new_payload

    return merged
