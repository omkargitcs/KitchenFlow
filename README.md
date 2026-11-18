# KitchenFlow

A REST API for a restaurant's menu, orders and inventory, built with **FastAPI**, **SQLAlchemy** and **pytest**, with **Terraform** to deploy it to AWS.

The interesting part is the same problem as my SeatDrop project, applied to food: two customers must never be sold the last portion, and a retried request must never charge twice.

## What it does

| Endpoint | Purpose |
|---|---|
| `GET /menu`, `POST /menu`, `PATCH /menu/{id}` | Menu and stock (writes need `X-API-Key` when `API_KEY` is set) |
| `POST /orders` | Place an order. Takes stock in the same transaction. Send an `Idempotency-Key` header to make retries safe |
| `PATCH /orders/{id}/status` | `placed → preparing → ready → completed`, or `cancelled` (returns stock). Illegal jumps return 409 |
| `GET /inventory/low-stock` | Items at or below their reorder threshold |
| `GET /reports/daily-sales?day=YYYY-MM-DD` | Orders, revenue, average order value and top sellers (cancelled orders excluded) |
| `GET /health`, `GET /docs` | Health check and auto-generated OpenAPI docs |

## Design decisions

- **No overselling.** Stock is taken with `UPDATE ... SET stock = stock - n WHERE stock >= n`. If two orders race for the last portion, only one UPDATE matches a row. A test fires 10 simultaneous orders at 5 portions and asserts exactly 5 succeed and stock ends at 0.
- **Idempotent orders.** A unique `Idempotency-Key` means a client retry returns the original order (HTTP 200) instead of creating a second one.
- **Money as integers** (`price_cents`), never floats. Order lines store the price at the time of purchase, so later menu price changes do not rewrite history.
- **Business rules in `services.py`**, not in the route handlers, so they can be tested without HTTP.
- **Validation by Pydantic**: bad quantities, empty orders and unknown statuses are rejected with 422 before reaching the database.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.seed                                 # sample menu
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs and try the endpoints.

```bash
pytest -q
```

Set `DATABASE_URL` (for example a PostgreSQL URL) to use a different database. It defaults to a local SQLite file.

## Deploy with Terraform (AWS)

`terraform/` creates a security group and one EC2 instance. On first boot it clones this repo, installs the dependencies and runs the API under systemd on port 80.

```bash
cd terraform
terraform init
terraform plan  -var "repo_url=https://github.com/<you>/kitchenflow.git"
terraform apply -var "repo_url=https://github.com/<you>/kitchenflow.git"
terraform destroy   # when finished, so it stops costing money
```
Needs AWS credentials configured locally. The default is a demo setup: SQLite on the instance disk, HTTP only.

## Not done yet (honest list)

- PostgreSQL, Alembic migrations and HTTPS behind a load balancer for a real production setup
- Authentication for customers (only a staff API key exists)
- Multi-ingredient recipes (stock is tracked per menu item, not per ingredient)
