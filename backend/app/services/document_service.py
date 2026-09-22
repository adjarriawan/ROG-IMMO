from app.database import SessionLocal
from app.models import Document
from app.services.embedding_service import embed_text


def ingest_document(filename: str, content: str) -> int:
    db = SessionLocal()
    try:
        embedding = embed_text(content)
        doc = Document(filename=filename, content=content, embedding=embedding)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc.id
    finally:
        db.close()
