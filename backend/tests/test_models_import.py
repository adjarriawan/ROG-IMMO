from app.models import User, ChatHistory, Document, Order


def test_table_names():
    assert User.__tablename__ == "users"
    assert ChatHistory.__tablename__ == "chat_history"
    assert Document.__tablename__ == "documents"
    assert Order.__tablename__ == "orders"
