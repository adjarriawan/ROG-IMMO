from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.database import SessionLocal
from app.models import Document
from app.services.embedding_service import embed_text

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)


def ingest_document(filename: str, content: str) -> list[int]:
    chunks = _splitter.split_text(content) or [content]
    db = SessionLocal()
    try:
        ids = []
        for chunk in chunks:
            embedding = embed_text(chunk)
            doc = Document(filename=filename, content=chunk, embedding=embedding)
            db.add(doc)
            db.flush()
            ids.append(doc.id)
        db.commit()
        return ids
    finally:
        db.close()
