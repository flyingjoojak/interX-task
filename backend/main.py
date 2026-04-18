from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models
from api.auth import router as auth_router
from api.candidates import router as candidates_router
from api.documents import router as documents_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="InterX API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3102"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(candidates_router, prefix="/api/candidates", tags=["candidates"])
app.include_router(documents_router, prefix="/api", tags=["documents"])


@app.get("/health")
def health():
    return {"status": "ok"}
