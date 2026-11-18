"""Order business rules, kept out of the route handlers so they are easy to test."""
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import MenuItem, Order, OrderItem

# status -> statuses it may move to
TRANSITIONS = {
    "placed": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


class OrderError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        self.message = message
        self.status_code = status_code


def create_order(db: Session, customer_name: str, lines, idempotency_key: str | None):
    """Create an order and take stock, all in one transaction.

    Stock is taken with a conditional UPDATE (stock >= qty). If two orders race for the last
    portion, only one UPDATE matches a row, so stock can never go negative.
    Returns (order, created) where created is False when an idempotent retry was detected.
    """
    if idempotency_key:
        existing = db.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
        if existing:
            return existing, False

    # merge duplicate lines: [{1,x2},{1,x3}] -> {1: 5}
    wanted: dict[int, int] = {}
    for line in lines:
        wanted[line.menu_item_id] = wanted.get(line.menu_item_id, 0) + line.quantity

    order = Order(customer_name=customer_name, idempotency_key=idempotency_key)
    total = 0
    try:
        for item_id, qty in sorted(wanted.items()):  # fixed order avoids deadlocks on Postgres
            item = db.get(MenuItem, item_id)
            if item is None:
                raise OrderError(f"Menu item {item_id} does not exist", 404)
            if not item.is_available:
                raise OrderError(f"{item.name} is not available", 409)

            taken = db.execute(
                update(MenuItem)
                .where(MenuItem.id == item_id, MenuItem.stock >= qty)
                .values(stock=MenuItem.stock - qty)
            ).rowcount
            if taken == 0:
                raise OrderError(f"Not enough stock for {item.name}", 409)

            order.items.append(
                OrderItem(menu_item_id=item_id, quantity=qty, unit_price_cents=item.price_cents)
            )
            total += item.price_cents * qty

        order.total_cents = total
        db.add(order)
        db.commit()
    except OrderError:
        db.rollback()
        raise
    except IntegrityError:
        # two requests with the same idempotency key landed together; return the winner
        db.rollback()
        winner = db.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
        if winner:
            return winner, False
        raise
    return order, True


def change_status(db: Session, order: Order, new_status: str) -> Order:
    if new_status not in TRANSITIONS[order.status]:
        raise OrderError(f"Cannot move an order from '{order.status}' to '{new_status}'", 409)

    if new_status == "cancelled":  # put the food back into stock
        for line in order.items:
            db.execute(
                update(MenuItem)
                .where(MenuItem.id == line.menu_item_id)
                .values(stock=MenuItem.stock + line.quantity)
            )
    order.status = new_status
    db.commit()
    return order
