# backend/tests/test_orchestrator.py
from app.agent.orchestrator import run_agent
from app.services.document_service import ingest_document


def test_agent_answers_general_question_without_tool():
    result = run_agent("Halo, siapa kamu?")
    assert result["answer"]


def test_agent_uses_rag_tool_for_document_question():
    ingest_document("cuti.txt", "Kebijakan cuti karyawan adalah 12 hari kerja per tahun.")
    result = run_agent("Menurut dokumen, berapa hari cuti karyawan per tahun?")
    assert result["tool_used"] == "rag_search_tool"
    assert any(s["filename"] == "cuti.txt" for s in result["sources"])


def test_agent_uses_sql_tool_for_data_question():
    result = run_agent("Berapa jumlah order yang tercatat di database?")
    assert result["tool_used"] == "sql_query_tool"
