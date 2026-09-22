import re

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.config import settings

_engine = create_engine(settings.sql_agent_db_url, connect_args={"options": "-c statement_timeout=5000"})

ALLOWED_TABLES = {"orders"}
FORBIDDEN_KEYWORDS = {"insert", "update", "delete", "drop", "alter", "truncate", "grant", "revoke", "--", ";"}


def _validate_query(query: str) -> None:
    normalized = query.strip().lower()
    if not normalized.startswith("select"):
        raise ValueError("only SELECT queries are allowed")
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in normalized:
            raise ValueError(f"query contains forbidden keyword: {keyword}")
    tables_referenced: set[str] = set()
    for clause in re.findall(r"from\s+(.+?)(?:where|group by|order by|limit|$)", normalized, re.DOTALL):
        for item in clause.split(","):
            match = re.match(r"\s*([a-zA-Z_][a-zA-Z0-9_.]*)", item)
            if match:
                tables_referenced.add(match.group(1).rsplit(".", 1)[-1])
    tables_referenced |= {t.rsplit(".", 1)[-1] for t in re.findall(r"join\s+([a-zA-Z_][a-zA-Z0-9_.]*)", normalized)}
    if not tables_referenced or not tables_referenced.issubset(ALLOWED_TABLES):
        raise ValueError(f"query references disallowed table(s): {tables_referenced - ALLOWED_TABLES}")


def sql_query(query: str) -> list[dict]:
    _validate_query(query)
    try:
        with _engine.connect() as conn:
            result = conn.execute(text(query))
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    except OperationalError as exc:
        raise ValueError(f"query execution failed: {exc}") from exc
