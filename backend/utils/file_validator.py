import os

import filetype
from fastapi import HTTPException, UploadFile, status

from config import settings

ALLOWED_EXTS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


def _get_ext(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def validate_file(file: UploadFile, doc_type: str, file_bytes: bytes) -> None:
    if doc_type not in {"resume", "portfolio"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_type은 resume 또는 portfolio여야 합니다",
        )

    if len(file_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"파일 크기가 {settings.MAX_FILE_SIZE_MB}MB를 초과합니다",
        )

    ext = _get_ext(file.filename or "")
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않은 파일 확장자입니다: {ext} (PDF/JPG/PNG만 지원)",
        )

    kind = filetype.guess(file_bytes)
    if kind is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일 형식을 확인할 수 없습니다",
        )

    if kind.mime not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않은 파일 형식입니다: {kind.mime}",
        )
