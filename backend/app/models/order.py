from sqlalchemy import Column, BigInteger, String, Numeric, Date

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True)
    customer_name = Column(String(255), nullable=False)
    product = Column(String(255), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    order_date = Column(Date, nullable=False)
