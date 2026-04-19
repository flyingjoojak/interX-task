"""꼬리질문 생성 전용 비동기 큐.

answer_qa API는 답변을 즉시 저장한 뒤 이 큐에 꼬리질문 작업을 넣고 빠르게 반환한다.
단일 워커가 큐를 순차적으로 처리하므로, 여러 답변이 빠르게 제출돼도 LLM 호출이
동시에 엉키지 않고 하나씩 안정적으로 완료된다. 결과는 DB에 저장되고, 프론트는
세션 폴링으로 followup_questions 상태를 업데이트한다.
"""
import asyncio
import json
from typing import TypedDict

from database import SessionLocal
from models.interview import QAPair


class FollowupJob(TypedDict):
    qa_id: str
    candidate_id: str
    session_id: str
    question: str
    answer: str
    question_source: str


_queue: asyncio.Queue | None = None
_worker_task: asyncio.Task | None = None


def _save_followups(qa_id: str, followups: list) -> None:
    db = SessionLocal()
    try:
        qa = db.query(QAPair).filter(QAPair.id == qa_id).one_or_none()
        if qa is None:
            return
        qa.followup_questions = json.dumps(followups or [], ensure_ascii=False)
        db.commit()
    finally:
        db.close()


async def _process(job: FollowupJob) -> None:
    from agents.interview_graph import generate_followup_questions

    print(
        f"[followup-worker] start qa={job['qa_id']} source={job.get('question_source')}"
    )
    try:
        followups = await generate_followup_questions(
            candidate_id=job["candidate_id"],
            question=job["question"],
            answer=job["answer"],
            session_id=job["session_id"],
            question_source=job.get("question_source") or "pregenerated",
        )
    except Exception as exc:
        print(f"[followup-worker] generation failed qa={job['qa_id']}: {exc}")
        followups = []

    _save_followups(job["qa_id"], followups or [])
    print(
        f"[followup-worker] done qa={job['qa_id']} count={len(followups or [])}"
    )


async def _worker_loop() -> None:
    assert _queue is not None
    while True:
        job = await _queue.get()
        try:
            await _process(job)
        except Exception as exc:
            print(f"[followup-worker] unexpected error: {exc}")
        finally:
            _queue.task_done()


def start_worker() -> None:
    """FastAPI 시작 시 호출. 큐와 단일 워커를 띄운다."""
    global _queue, _worker_task
    if _queue is None:
        _queue = asyncio.Queue()
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker_loop())


async def enqueue_followup(
    qa_id: str,
    candidate_id: str,
    session_id: str,
    question: str,
    answer: str,
    question_source: str = "pregenerated",
) -> None:
    if _queue is None:
        start_worker()
    assert _queue is not None
    await _queue.put(
        FollowupJob(
            qa_id=qa_id,
            candidate_id=candidate_id,
            session_id=session_id,
            question=question,
            answer=answer,
            question_source=question_source or "pregenerated",
        )
    )
    print(f"[followup-worker] enqueued qa={qa_id} source={question_source}")
