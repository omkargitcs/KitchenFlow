from concurrent.futures import ThreadPoolExecutor


def order(client, item_id, qty, key=None, name="Asha"):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post("/orders", json={"customer_name": name,
                       "items": [{"menu_item_id": item_id, "quantity": qty}]}, headers=headers)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_duplicate_menu_item_rejected(client, paneer):
    r = client.post("/menu", json={"name": "Paneer Tikka", "category": "starter", "price_cents": 1})
    assert r.status_code == 409


def test_order_reduces_stock_and_totals(client, paneer):
    r = order(client, paneer["id"], 3)
    assert r.status_code == 201
    assert r.json()["total_cents"] == 75000
    stock = client.get("/menu").json()[0]["stock"]
    assert stock == 7


def test_cannot_oversell(client, paneer):
    r = order(client, paneer["id"], 11)
    assert r.status_code == 409
    assert client.get("/menu").json()[0]["stock"] == 10  # nothing was taken


def test_unknown_item_404(client):
    assert order(client, 999, 1).status_code == 404


def test_idempotency_key_prevents_double_order(client, paneer):
    first = order(client, paneer["id"], 2, key="abc")
    second = order(client, paneer["id"], 2, key="abc")
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert client.get("/menu").json()[0]["stock"] == 8  # charged once, not twice


def test_cancel_restores_stock(client, paneer):
    oid = order(client, paneer["id"], 4).json()["id"]
    r = client.patch(f"/orders/{oid}/status", json={"status": "cancelled"})
    assert r.status_code == 200
    assert client.get("/menu").json()[0]["stock"] == 10


def test_invalid_status_transition(client, paneer):
    oid = order(client, paneer["id"], 1).json()["id"]
    r = client.patch(f"/orders/{oid}/status", json={"status": "completed"})  # skips steps
    assert r.status_code == 409


def test_low_stock_report(client, paneer):
    order(client, paneer["id"], 8)  # leaves 2, threshold 3
    names = [i["name"] for i in client.get("/inventory/low-stock").json()]
    assert names == ["Paneer Tikka"]


def test_daily_sales_ignores_cancelled(client, paneer):
    order(client, paneer["id"], 2)
    oid = order(client, paneer["id"], 1).json()["id"]
    client.patch(f"/orders/{oid}/status", json={"status": "cancelled"})
    rep = client.get("/reports/daily-sales").json()
    assert rep["orders"] == 1 and rep["revenue_cents"] == 50000
    assert rep["top_items"] == [{"name": "Paneer Tikka", "sold": 2}]


def test_validation_rejects_bad_quantity(client, paneer):
    assert order(client, paneer["id"], 0).status_code == 422


def test_api_key_protects_menu_writes(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    body = {"name": "Dal", "category": "main", "price_cents": 18000}
    assert client.post("/menu", json=body).status_code == 401
    assert client.post("/menu", json=body, headers={"X-API-Key": "secret"}).status_code == 201


def test_concurrent_orders_for_last_portions(tmp_path):
    """10 simultaneous orders for 5 portions: exactly 5 win, stock ends at 0, never negative.

    Uses a real file database so every thread gets its own connection (an in-memory
    database shared by one connection would hide the race this test is checking).
    """
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base, get_db
    from app.main import app

    engine = create_engine(f"sqlite:///{tmp_path/'race.db'}",
                           connect_args={"check_same_thread": False, "timeout": 30})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        c = TestClient(app)
        item = c.post("/menu", json={"name": "Biryani", "category": "main",
                                     "price_cents": 30000, "stock": 5}).json()
        with ThreadPoolExecutor(max_workers=10) as ex:
            results = list(ex.map(lambda _: order(c, item["id"], 1).status_code, range(10)))
        assert results.count(201) == 5 and results.count(409) == 5
        assert c.get("/menu").json()[0]["stock"] == 0
    finally:
        app.dependency_overrides.clear()
