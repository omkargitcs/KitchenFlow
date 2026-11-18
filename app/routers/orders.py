from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order
from ..schemas import OrderCreate, OrderOut, StatusUpdate
from ..services import OrderError, change_status, create_order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=201)
def place_order(
    body: OrderCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    try:
        order, created = create_order(db, body.customer_name, body.items, idempotency_key)
    except OrderError as e:
        raise HTTPException(e.status_code, e.message)
    if not created:
        response.status_code = 200  # same key as an earlier request: no second order made
    return order


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_status(order_id: int, body: StatusUpdate, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    try:
        return change_status(db, order, body.status)
    except OrderError as e:
        raise HTTPException(e.status_code, e.message)
