from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect, text

from database import Base, engine
import models
from api.auth import router as auth_router
from api.candidates import router as candidates_router
from api.documents import router as documents_router
from api.analysis import router as analysis_router
from api.interview import router as interview_router

Base.metadata.create_all(bind=engine)


def _ensure_column(table: str, column: str, ddl_type: str) -> None:
    """SQLite lightweight migration: add a column if missing."""
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl_type}'))


_ensure_column("analyses", "error_message", "TEXT")

app = FastAPI(title="InterX API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3102", "http://127.0.0.1:3102"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(candidates_router, prefix="/api/candidates", tags=["candidates"])
app.include_router(documents_router, prefix="/api", tags=["documents"])
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
app.include_router(interview_router, prefix="/api", tags=["interview"])


@app.on_event("startup")
async def on_startup():
    from services.followup_worker import start_worker
    start_worker()


@app.get("/health")
def health():
    return {"status": "ok"}
