from datetime import date

from app.database import SessionLocal
from app.models import Order

SEED_ROWS = [
    ("Andi Wijaya", "Laptop", 12500000, date(2026, 1, 5)),
    ("Budi Santoso", "Monitor", 2100000, date(2026, 2, 12)),
    ("Citra Dewi", "Keyboard", 450000, date(2026, 2, 20)),
    ("Dian Permata", "Mouse", 150000, date(2026, 3, 1)),
    ("Eka Putra", "Laptop", 13200000, date(2026, 3, 15)),
    ("Fajar Nugroho", "Webcam", 650000, date(2026, 4, 2)),
    ("Gita Lestari", "Monitor", 2300000, date(2026, 4, 18)),
    ("Hendra Saputra", "Headset", 800000, date(2026, 5, 3)),
    ("Indah Sari", "Laptop", 11900000, date(2026, 5, 22)),
    ("Joko Susilo", "Keyboard", 480000, date(2026, 6, 10)),
]


def seed():
    db = SessionLocal()
    try:
        if db.query(Order).count() > 0:
            print("orders already seeded, skipping")
            return
        for customer_name, product, amount, order_date in SEED_ROWS:
            db.add(Order(customer_name=customer_name, product=product, amount=amount, order_date=order_date))
        db.commit()
        print(f"seeded {len(SEED_ROWS)} orders")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
