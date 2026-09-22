import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.config import settings
from app.core.deps import require_role
from app.schemas.document import DocumentCreateRequest, DocumentResponse
from app.services.document_service import ingest_document

router = APIRouter(tags=["documents"])

allow_write = require_role(["ADMIN", "USER"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
ALLOWED_CONTENT_TYPES = {"application/pdf", "text/plain"}
FILE_SIGNATURES = {".pdf": b"%PDF-"}  # .txt has no reliable magic bytes


def _validate_upload(filename: str, content_type: str | None, content_bytes: bytes) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"file type not allowed: {ext or 'unknown'}")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"content-type not allowed: {content_type}")
    if not content_bytes:
        raise HTTPException(status_code=400, detail="empty file")
    if len(content_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="file exceeds 10MB limit")
    signature = FILE_SIGNATURES.get(ext)
    if signature and not content_bytes.startswith(signature):
        raise HTTPException(status_code=400, detail="file signature does not match extension")


@router.post("/upload", response_model=DocumentResponse)
async def upload_file(file: UploadFile, _user=Depends(allow_write)):
    safe_filename = os.path.basename(file.filename or "")
    if not safe_filename or safe_filename in (".", ".."):
        raise HTTPException(status_code=400, detail="invalid filename")

    content_bytes = await file.read()
    _validate_upload(safe_filename, file.content_type, content_bytes)

    os.makedirs(settings.upload_dir, exist_ok=True)
    dest_path = os.path.join(settings.upload_dir, safe_filename)
    with open(dest_path, "wb") as f:
        f.write(content_bytes)

    text_content = content_bytes.decode("utf-8", errors="ignore")
    ingest_document(file.filename, text_content)

    return DocumentResponse(filename=file.filename, status="processed")


@router.post("/documents", response_model=DocumentResponse)
def create_document(payload: DocumentCreateRequest, _user=Depends(allow_write)):
    ingest_document(payload.filename, payload.content)
    return DocumentResponse(filename=payload.filename, status="processed")
