"""Load a sample menu: python -m scripts.seed"""
from app.database import Base, SessionLocal, engine
from app.models import MenuItem

ITEMS = [
    ("Paneer Tikka", "starter", 25000, 20, 5),
    ("Veg Manchurian", "starter", 20000, 15, 5),
    ("Butter Chicken", "main", 38000, 12, 4),
    ("Dal Makhani", "main", 28000, 14, 4),
    ("Veg Biryani", "main", 30000, 10, 4),
    ("Garlic Naan", "bread", 6000, 40, 10),
    ("Gulab Jamun", "dessert", 12000, 18, 5),
    ("Masala Chai", "drink", 5000, 30, 8),
]

Base.metadata.create_all(engine)
with SessionLocal() as db:
    if db.query(MenuItem).count() == 0:
        db.add_all(MenuItem(name=n, category=c, price_cents=p, stock=s, low_stock_threshold=t)
                   for n, c, p, s, t in ITEMS)
        db.commit()
        print(f"Seeded {len(ITEMS)} items")
    else:
        print("Menu already has items, skipping")
