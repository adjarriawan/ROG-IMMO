from langchain_ollama import OllamaEmbeddings

from app.config import settings

_embeddings = OllamaEmbeddings(model=settings.ollama_embedding_model, base_url=settings.ollama_base_url)


def embed_text(text: str) -> list[float]:
    return _embeddings.embed_query(text)
