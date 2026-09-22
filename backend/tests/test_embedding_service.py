from app.services.embedding_service import embed_text


def test_embed_text_returns_768_dim_vector():
    vector = embed_text("hello world")
    assert len(vector) == 768
    assert all(isinstance(x, float) for x in vector)
