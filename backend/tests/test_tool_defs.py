# backend/tests/test_tool_defs.py
from app.agent.tool_defs import AGENT_TOOLS


def test_agent_tools_have_names_and_descriptions():
    names = {t.name for t in AGENT_TOOLS}
    assert names == {"rag_search_tool", "image_ocr_tool", "sql_query_tool"}
    for t in AGENT_TOOLS:
        assert t.description


def test_sql_query_tool_rejects_disallowed_table():
    sql_tool = next(t for t in AGENT_TOOLS if t.name == "sql_query_tool")
    result = sql_tool.invoke({"query": "SELECT * FROM users"})
    assert "ditolak" in result.lower()
