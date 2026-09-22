import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.config import settings
from app.core.deps import require_role
from app.schemas.document import DocumentCreateRequest, DocumentResponse
from app.services.document_service import ingest_document

router = APIRouter(tags=["documents"])

allow_write = require_role(["ADMIN", "USER"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_file(file: UploadFile, _user=Depends(allow_write)):
    safe_filename = os.path.basename(file.filename or "")
    if not safe_filename or safe_filename in (".", ".."):
        raise HTTPException(status_code=400, detail="invalid filename")

    os.makedirs(settings.upload_dir, exist_ok=True)
    dest_path = os.path.join(settings.upload_dir, safe_filename)
    content_bytes = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content_bytes)

    text_content = content_bytes.decode("utf-8", errors="ignore")
    ingest_document(file.filename, text_content)

    return DocumentResponse(filename=file.filename, status="processed")


@router.post("/documents", response_model=DocumentResponse)
def create_document(payload: DocumentCreateRequest, _user=Depends(allow_write)):
    ingest_document(payload.filename, payload.content)
    return DocumentResponse(filename=payload.filename, status="processed")
