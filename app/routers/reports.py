from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MenuItem, Order, OrderItem

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily-sales")
def daily_sales(day: date | None = None, db: Session = Depends(get_db)):
    """Revenue, order count and best sellers for one day (UTC). Cancelled orders are excluded."""
    day = day or datetime.now(timezone.utc).date()
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    in_day = (Order.created_at >= start) & (Order.created_at < end) & (Order.status != "cancelled")

    orders, revenue = db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total_cents), 0)).where(in_day)
    ).one()

    top = db.execute(
        select(MenuItem.name, func.sum(OrderItem.quantity).label("sold"))
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(in_day)
        .group_by(MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    ).all()

    return {
        "date": day.isoformat(),
        "orders": orders,
        "revenue_cents": revenue,
        "average_order_cents": round(revenue / orders) if orders else 0,
        "top_items": [{"name": n, "sold": int(s)} for n, s in top],
    }
