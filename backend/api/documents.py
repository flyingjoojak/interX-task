import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.candidate import Candidate
from models.document import Document
from models.user import User
from schemas.document import DocumentResponse
from utils.file_validator import validate_file
from utils.jwt_utils import get_current_user

router = APIRouter()


@router.post("/candidates/{candidate_id}/documents", response_model=DocumentResponse)
async def upload_document(
    candidate_id: str,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="후보자를 찾을 수 없습니다")

    file_bytes = await file.read()
    validate_file(file, doc_type, file_bytes)

    existing = (
        db.query(Document)
        .filter(Document.candidate_id == candidate_id, Document.doc_type == doc_type)
        .first()
    )
    if existing is not None:
        try:
            if os.path.exists(existing.file_path):
                os.remove(existing.file_path)
        except OSError:
            pass
        db.delete(existing)
        db.flush()

    candidate_dir = os.path.join(settings.UPLOAD_DIR, candidate_id)
    os.makedirs(candidate_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = os.path.join(candidate_dir, stored_name)

    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    document = Document(
        candidate_id=candidate_id,
        original_name=file.filename or stored_name,
        file_path=stored_path,
        file_type=ext.lstrip("."),
        doc_type=doc_type,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == doc_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문서를 찾을 수 없습니다")

    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except OSError:
        pass

    db.delete(document)
    db.commit()
    return {"message": "삭제 완료"}
