from app.services.document_service import ingest_document
from app.tools.rag_tool import rag_search


def test_ingest_and_search_finds_relevant_document():
    ingest_document("policy.txt", "Masa retensi dokumen perusahaan adalah 5 tahun sejak tanggal pembuatan.")
    ingest_document("unrelated.txt", "Resep membuat kopi susu dengan gula aren.")

    results = rag_search("berapa lama masa retensi dokumen?", top_k=2)

    assert len(results) == 2
    assert results[0]["filename"] == "policy.txt"
