import pytest

from app.tools.sql_tool import sql_query


def test_select_orders_succeeds():
    rows = sql_query("SELECT * FROM orders LIMIT 5")
    assert len(rows) <= 5
    assert "customer_name" in rows[0]


def test_select_disallowed_table_raises():
    with pytest.raises(ValueError):
        sql_query("SELECT * FROM users")


def test_non_select_raises():
    with pytest.raises(ValueError):
        sql_query("DELETE FROM orders")


def test_semicolon_injection_raises():
    with pytest.raises(ValueError):
        sql_query("SELECT * FROM orders; DROP TABLE orders")


def test_comma_join_other_table_raises():
    with pytest.raises(ValueError):
        sql_query("SELECT * FROM orders, pg_shadow")


def test_schema_qualified_orders_allowed():
    rows = sql_query("SELECT * FROM public.orders LIMIT 1")
    assert len(rows) <= 1
