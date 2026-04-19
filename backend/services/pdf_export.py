"""서버사이드 PDF 생성 — reportlab 기반.

Playwright 경로는 프론트엔드 구동·인증 토큰·URL 정합성에 모두 의존해 불안정했다.
reportlab으로 분석 데이터(Analysis)를 직접 PDF로 렌더링하면 프론트엔드 상태와
무관하게 안정적으로 결과를 반환할 수 있다.
"""
import json
import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from database import SessionLocal
from models.analysis import Analysis
from models.candidate import Candidate

FONT_CANDIDATES = [
    ("KoreanFont", r"C:\Windows\Fonts\malgun.ttf"),
    ("KoreanFont", r"C:\Windows\Fonts\malgunbd.ttf"),
    ("KoreanFont", "/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    ("KoreanFont", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
]

_font_registered = False


def _ensure_korean_font() -> str:
    """한글 TTF 폰트를 reportlab에 등록. 성공하면 폰트명, 실패하면 Helvetica."""
    global _font_registered
    if _font_registered:
        return "KoreanFont"
    for name, path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                _font_registered = True
                return name
            except Exception:
                continue
    return "Helvetica"


def _safe_json(raw):
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _load_payload(candidate_id: str) -> dict:
    db = SessionLocal()
    try:
        cand = db.query(Candidate).filter(Candidate.id == candidate_id).one_or_none()
        analysis = (
            db.query(Analysis).filter(Analysis.candidate_id == candidate_id).one_or_none()
        )
        return {
            "candidate": cand,
            "analysis": analysis,
        }
    finally:
        db.close()


def _build_styles(font: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName=font, fontSize=20, leading=26, alignment=TA_LEFT
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName=font, fontSize=14, leading=20, spaceBefore=12, spaceAfter=6
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName=font, fontSize=10, leading=15
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontName=font, fontSize=9, leading=13, textColor=colors.grey
        ),
    }


def _escape(text) -> str:
    if text is None:
        return ""
    s = str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _severity_badge(sev: str) -> str:
    sev = (sev or "").lower()
    color = {"high": "#dc2626", "medium": "#d97706", "low": "#65a30d"}.get(sev, "#6b7280")
    label = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}.get(sev, sev.upper())
    return f'<font color="{color}"><b>[{label}]</b></font>'


def _values_table(values_scores: dict, font: str):
    if not values_scores:
        return None
    rows = [["핵심가치", "점수", "근거 요약"]]
    for name, payload in values_scores.items():
        if not isinstance(payload, dict):
            continue
        score = payload.get("score", 0)
        evidence = (payload.get("evidence") or "").strip()
        if len(evidence) > 80:
            evidence = evidence[:80] + "…"
        rows.append([str(name), str(score), evidence])

    table = Table(rows, colWidths=[35 * mm, 15 * mm, 110 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), font, 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _render_story(candidate, analysis, styles):
    story = []

    story.append(Paragraph(f"{_escape(candidate.name)} 분석 리포트", styles["title"]))
    meta = f"직군: {_escape(candidate.position) or '미지정'} · 상태: {_escape(candidate.status)}"
    story.append(Paragraph(meta, styles["small"]))
    story.append(Spacer(1, 8))

    reliability = analysis.doc_reliability_score if analysis else None
    if reliability is not None:
        story.append(Paragraph("문서 신뢰도", styles["h2"]))
        story.append(
            Paragraph(f"<b>{int(round(reliability))}</b> / 100", styles["body"])
        )

    summary = (analysis.summary or "") if analysis else ""
    if summary:
        story.append(Paragraph("요약", styles["h2"]))
        story.append(Paragraph(_escape(summary), styles["body"]))

    values_scores = _safe_json(analysis.values_scores) if analysis else None
    if values_scores:
        story.append(Paragraph("12가지 핵심가치", styles["h2"]))
        vt = _values_table(values_scores, styles["body"].fontName)
        if vt is not None:
            story.append(vt)

    contradictions = _safe_json(analysis.contradictions) if analysis else None
    if contradictions:
        story.append(Paragraph("모순 · 불일치", styles["h2"]))
        for c in contradictions:
            if not isinstance(c, dict):
                continue
            sev = _severity_badge(c.get("severity", ""))
            desc = _escape(c.get("description", ""))
            sa = _escape(c.get("source_a", ""))
            sb = _escape(c.get("source_b", ""))
            story.append(
                Paragraph(f"{sev} {desc}", styles["body"])
            )
            story.append(Paragraph(f"출처 A: {sa} · 출처 B: {sb}", styles["small"]))
            story.append(Spacer(1, 4))

    preemptive = _safe_json(analysis.preemptive_questions) if analysis else None
    if preemptive:
        story.append(PageBreak())
        story.append(Paragraph("사전 압박 질문", styles["h2"]))
        for i, q in enumerate(preemptive, start=1):
            if not isinstance(q, dict):
                continue
            text = _escape(q.get("question", ""))
            basis = _escape(q.get("basis", ""))
            target = q.get("target_value")
            tag = f" <font color='#ea580c'>[{_escape(target)}]</font>" if target else ""
            story.append(Paragraph(f"{i}. {text}{tag}", styles["body"]))
            if basis:
                story.append(Paragraph(f"근거: {basis}", styles["small"]))
            story.append(Spacer(1, 4))

    structured = _safe_json(analysis.structured_data) if analysis else None
    if structured:
        story.append(PageBreak())
        story.append(Paragraph("구조화 데이터", styles["h2"]))

        careers = structured.get("career") or []
        if careers:
            story.append(Paragraph("<b>경력</b>", styles["body"]))
            for c in careers:
                line = (
                    f"· {_escape(c.get('company'))} | {_escape(c.get('role'))} | "
                    f"{_escape(c.get('start'))} ~ {_escape(c.get('end'))}"
                )
                story.append(Paragraph(line, styles["body"]))
                desc = _escape(c.get("description"))
                if desc:
                    story.append(Paragraph(desc, styles["small"]))
            story.append(Spacer(1, 6))

        projects = structured.get("projects") or []
        if projects:
            story.append(Paragraph("<b>프로젝트</b>", styles["body"]))
            for p in projects:
                line = (
                    f"· {_escape(p.get('name'))} | {_escape(p.get('role'))} | "
                    f"{_escape(p.get('period'))}"
                )
                story.append(Paragraph(line, styles["body"]))
                tech = p.get("tech_stack") or []
                if tech:
                    story.append(Paragraph(f"기술: {_escape(', '.join(map(str, tech)))}", styles["small"]))
                desc = _escape(p.get("description"))
                if desc:
                    story.append(Paragraph(desc, styles["small"]))
            story.append(Spacer(1, 6))

        skills = structured.get("skills") or []
        if skills:
            story.append(Paragraph(f"<b>기술 스택</b>: {_escape(', '.join(map(str, skills)))}", styles["body"]))

    return story


async def generate_pdf(candidate_id: str) -> bytes:
    payload = _load_payload(candidate_id)
    candidate = payload["candidate"]
    analysis = payload["analysis"]

    if candidate is None:
        raise ValueError(f"후보자를 찾을 수 없습니다: {candidate_id}")

    font = _ensure_korean_font()
    styles = _build_styles(font)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"{candidate.name}_report",
    )
    story = _render_story(candidate, analysis, styles)
    doc.build(story)
    return buf.getvalue()
