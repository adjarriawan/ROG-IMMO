from app.database import SessionLocal
from app.models import Document
from app.services.embedding_service import embed_text


def rag_search(query: str, top_k: int = 3) -> list[dict]:
    db = SessionLocal()
    try:
        query_embedding = embed_text(query)
        results = (
            db.query(Document, Document.embedding.cosine_distance(query_embedding).label("distance"))
            .order_by("distance")
            .limit(top_k)
            .all()
        )
        return [
            {"filename": doc.filename, "content": doc.content, "score": float(distance)}
            for doc, distance in results
        ]
    finally:
        db.close()
