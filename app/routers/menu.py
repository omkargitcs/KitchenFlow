from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MenuItem
from ..schemas import MenuItemCreate, MenuItemOut, MenuItemUpdate
from ..security import require_api_key

router = APIRouter(tags=["menu"])


@router.get("/menu", response_model=list[MenuItemOut])
def list_menu(
    category: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = select(MenuItem).order_by(MenuItem.id).limit(limit).offset(offset)
    if category:
        q = q.where(MenuItem.category == category)
    return db.scalars(q).all()


@router.post("/menu", response_model=MenuItemOut, status_code=201, dependencies=[Depends(require_api_key)])
def add_menu_item(body: MenuItemCreate, db: Session = Depends(get_db)):
    item = MenuItem(**body.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"'{body.name}' is already on the menu")
    return item


@router.patch("/menu/{item_id}", response_model=MenuItemOut, dependencies=[Depends(require_api_key)])
def update_menu_item(item_id: int, body: MenuItemUpdate, db: Session = Depends(get_db)):
    item = db.get(MenuItem, item_id)
    if not item:
        raise HTTPException(404, "Menu item not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    return item


@router.get("/inventory/low-stock", response_model=list[MenuItemOut])
def low_stock(db: Session = Depends(get_db)):
    """Items at or below their reorder threshold, so the kitchen knows what to restock."""
    q = select(MenuItem).where(MenuItem.stock <= MenuItem.low_stock_threshold).order_by(MenuItem.stock)
    return db.scalars(q).all()
